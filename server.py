from flask import Flask, request, jsonify
from flask_cors import CORS
from textblob import TextBlob
from googletrans import Translator
from pyvi import ViTokenizer, ViPosTagger

app = Flask(__name__)
CORS(app)
translator = Translator()

# --- TỪ ĐIỂN CẢM XÚC TIẾNG VIỆT ---

POSITIVE_WORDS = {
    'hay', 'tốt', 'đẹp', 'vui', 'thích', 'yêu', 'tuyệt', 'xuất_sắc',
    'đỉnh', 'xịn', 'ngon', 'hạnh_phúc', 'tự_hào', 'ổn', 'được',
    'giỏi', 'thú_vị', 'hấp_dẫn', 'nhanh', 'mạnh', 'sáng', 'cảm_ơn',
    'ủng_hộ', 'tin', 'hy_vọng', 'phấn_khởi', 'hài_lòng', 'hoàn_hảo',
    'tuyệt_vời', 'đáng', 'xứng', 'nổi_bật', 'ấn_tượng', 'khen'
}

NEGATIVE_WORDS = {
    'tệ', 'dở', 'chán', 'buồn', 'tức', 'ghét', 'xấu', 'kém',
    'thất_vọng', 'tồi', 'kinh', 'sợ', 'chê', 'phàn_nàn', 'bực',
    'khó_chịu', 'phí', 'lãng_phí', 'chậm', 'yếu', 'tối', 'lo',
    'lo_lắng', 'băn_khoăn', 'nghi_ngờ', 'không_hài_lòng', 'thất_bại',
    'vô_dụng', 'ngu', 'tệ_hại', 'tồi_tệ', 'bỏ', 'từ_chối'
}

# Từ tăng cường (rất, quá, cực...) nhân đôi trọng số
INTENSIFIERS = {'rất', 'quá', 'cực', 'siêu', 'lắm', 'vô_cùng', 'hết_sức', 'thật', 'thực_sự'}

# Từ phủ định đảo chiều điểm
NEGATIONS = {'không', 'chẳng', 'chưa', 'chả', 'đâu', 'chưa_hề', 'không_hề'}

# Từ nhượng bộ — ý sau mới là ý chính
CONCESSIONS = {'nhưng', 'tuy_nhiên', 'song', 'thế_nhưng', 'dù_vậy', 'mặc_dù'}


def analyze_vi(tokens, tags):
    """
    Phân tích cảm xúc dựa trên tokens và POS tags từ pyvi.
    Trả về điểm pyvi trong khoảng [-1, 1] và danh sách từ quan trọng.
    """
    score = 0.0
    key_words = []
    notes = []
    n = len(tokens)

    i = 0
    after_concession = False  # Đang ở phần sau "nhưng"?
    concession_index = -1

    # Tìm vị trí từ nhượng bộ đầu tiên
    for idx, tok in enumerate(tokens):
        if tok.lower() in CONCESSIONS:
            concession_index = idx
            break

    while i < n:
        tok = tokens[i].lower()
        tag = tags[i]

        # Phần trước "nhưng" chỉ tính 30% trọng số
        weight = 1.0 if (concession_index == -1 or i > concession_index) else 0.3

        if tok in CONCESSIONS:
            after_concession = True
            notes.append(f'Phát hiện "{tok}" — ý sau là ý chính')
            i += 1
            continue

        # Kiểm tra phủ định phía trước
        negated = False
        if i > 0 and tokens[i-1].lower() in NEGATIONS:
            negated = True

        # Kiểm tra intensifier phía trước
        intensified = False
        if i > 0 and tokens[i-1].lower() in INTENSIFIERS:
            intensified = True
        if i > 1 and tokens[i-2].lower() in INTENSIFIERS:
            intensified = True

        # Chỉ quan tâm tính từ (A) và trạng từ (R) — đây là từ mang cảm xúc
        if tag in ('A', 'R') or tok in POSITIVE_WORDS or tok in NEGATIVE_WORDS:
            word_score = 0.0

            if tok in POSITIVE_WORDS:
                word_score = 0.4
                key_words.append(tok)
            elif tok in NEGATIVE_WORDS:
                word_score = -0.4
                key_words.append(tok)
            elif tag == 'A':
                # Tính từ chưa có trong từ điển → nhờ TextBlob xử lý sau
                word_score = 0.1

            if intensified:
                word_score *= 1.8
                if tok in POSITIVE_WORDS or tok in NEGATIVE_WORDS:
                    notes.append(f'Tăng cường: "{tok}"')

            if negated:
                word_score *= -0.6
                if tok in POSITIVE_WORDS or tok in NEGATIVE_WORDS:
                    notes.append(f'Phủ định: "{tok}"')

            score += word_score * weight

        i += 1

    # Giới hạn điểm pyvi về [-1, 1]
    score = max(-1.0, min(1.0, score))
    return round(score, 2), key_words, notes


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        text_vi = data.get('text', '').strip()
        if not text_vi:
            return jsonify({'error': 'Chưa nhập text'}), 400

        # 1. Tách từ và gán nhãn bằng pyvi
        tokenized = ViTokenizer.tokenize(text_vi)
        tokens, tags = ViPosTagger.postagging(tokenized)
        tokens = list(tokens)
        tags = list(tags)

        # 2. Tính điểm pyvi (tiếng Việt thuần)
        vi_score, key_words, notes = analyze_vi(tokens, tags)

        # 3. Dịch và tính điểm TextBlob (tiếng Anh)
        translated = translator.translate(text_vi, src='vi', dest='en')
        text_en = translated.text
        blob = TextBlob(text_en)
        tb_score = round(blob.sentiment.polarity, 2)
        subjectivity = round(blob.sentiment.subjectivity, 2)

        # 4. Kết hợp: pyvi 60% + TextBlob 40%
        #    pyvi hiểu tiếng Việt tốt hơn nên trọng số cao hơn
        if vi_score != 0:
            final_score = round(vi_score * 0.6 + tb_score * 0.4, 2)
            notes.append(f'Kết hợp: pyvi({vi_score}) × 60% + TextBlob({tb_score}) × 40%')
        else:
            # pyvi không nhận diện được → dùng TextBlob hoàn toàn
            final_score = tb_score
            notes.append(f'pyvi không nhận diện được → dùng TextBlob({tb_score})')

        final_score = max(-1.0, min(1.0, final_score))

        if final_score > 0.1:
            sentiment = 'positive'
        elif final_score < -0.1:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        return jsonify({
            'sentiment': sentiment,
            'score': round(final_score, 2),
            'vi_score': vi_score,
            'tb_score': tb_score,
            'subjectivity': subjectivity,
            'translation': text_en,
            'keywords': key_words[:5],
            'notes': notes
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=== Server đang chạy tại http://localhost:5000 ===")
    app.run(host='0.0.0.0', port=5000, debug=True)