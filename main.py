from kivymd.app import MDApp
from kivymd.uix.screen import Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.lang import Builder
from kivy.clock import Clock
from textblob import TextBlob
from googletrans import Translator
import threading

# --- PHẦN 1: GIAO DIỆN (KV LANGUAGE) ---
KV = '''
Screen:
    MDBoxLayout:
        orientation: "vertical"
        padding: 30
        spacing: 20
        
        MDLabel:
            text: "AI PHÂN TÍCH CẢM XÚC CỦA CÂU"
            halign: "center"
            font_style: "H3"
            theme_text_color: "Custom"
            text_color: 66/255, 165/255, 245/255, 1 
            size_hint_y: None
            height: self.texture_size[1]
            pos_hint: {"top": 1}

        MDTextField:
            id: input_text
            hint_text: "Nhập câu tiếng Việt vào đây..."
            mode: "rectangle"
            multiline: True
            font_size: 24
            size_hint_y: 0.4
            icon_right: "pencil"
            icon_right_color: app.theme_cls.primary_color
        MDRaisedButton:
            id: btn_analyze
            text: "PHÂN TÍCH NGAY"
            font_size: 20
            pos_hint: {"center_x": .5}
            size_hint_x: 0.8
            padding: 10
            elevation: 8
            on_release: app.start_analysis()
        Widget:
            size_hint_y: 0.1
        MDLabel:
            id: lbl_result
            text: "..."
            halign: "center"
            font_style: "H2"
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1

        # 6. Chi tiết điểm số & Dịch
        MDLabel:
            id: lbl_detail
            text: "Sẵn sàng phân tích"
            halign: "center"
            theme_text_color: "Secondary"
            font_style: "Subtitle1"
'''

# --- PHẦN 2: LOGIC PYTHON ---
class SentimentApp(MDApp):
    def build(self):
        # Cấu hình giao diện tối
        self.theme_cls.theme_style = "Dark" 
        self.theme_cls.primary_palette = "Blue"  # Màu chủ đạo
        
        # Khởi tạo bộ dịch
        self.translator = Translator()
        
        # Load giao diện từ chuỗi KV bên trên
        return Builder.load_string(KV)

    def start_analysis(self):
        # Lấy text từ ô nhập
        text_vi = self.root.ids.input_text.text
        
        if not text_vi.strip():
            self.root.ids.lbl_detail.text = "Bạn chưa nhập gì cả!"
            return

        # Khóa nút bấm và đổi trạng thái
        self.root.ids.btn_analyze.text = "Đang suy nghĩ..."
        self.root.ids.btn_analyze.disabled = True
        
        # Chạy logic trong luồng riêng (Thread) để không đơ app
        threading.Thread(target=self.run_logic, args=(text_vi,)).start()

    def run_logic(self, text_vi):
        try:
            # 1. Dịch
            translated = self.translator.translate(text_vi, src='vi', dest='en')
            text_en = translated.text
            
            # 2. Phân tích
            blob = TextBlob(text_en)
            score = blob.sentiment.polarity
            
            # 3. Gửi kết quả về giao diện chính
            Clock.schedule_once(lambda dt: self.update_ui(score, text_en))
            
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(str(e)))

    def update_ui(self, score, text_en):
        # Mở lại nút bấm
        self.root.ids.btn_analyze.disabled = False
        self.root.ids.btn_analyze.text = "PHÂN TÍCH NGAY"
        
        # Cập nhật thông tin phụ
        self.root.ids.lbl_detail.text = f"Dịch: {text_en}\nĐiểm số: {score:.2f}"
        
        # Xử lý kết quả và đổi màu chữ
        lbl = self.root.ids.lbl_result
        if score > 0.1:
            lbl.text = "TÍCH CỰC, YÊU ĐỜI"
            lbl.text_color = (0, 1, 0, 1) # Màu xanh lá
        elif score < -0.1:
            lbl.text = "TIÊU CỰC, CHÁN NẢN"
            lbl.text_color = (1, 0.2, 0.2, 1) # Màu đỏ
        else:
            lbl.text = "BÌNH THƯỜNG"
            lbl.text_color = (1, 0.8, 0, 1) # Màu vàng

    def show_error(self, error_msg):
        self.root.ids.btn_analyze.disabled = False
        self.root.ids.btn_analyze.text = "THỬ LẠI"
        self.root.ids.lbl_detail.text = "Lỗi kết nối mạng!"
        print(error_msg)

if __name__ == "__main__":
    SentimentApp().run()