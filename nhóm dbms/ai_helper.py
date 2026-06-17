import sys
import subprocess

# Tự động cài đặt thư viện nếu máy khách chưa có
try:
    import google.generativeai as genai
except ImportError:
    print("Đang tự động cài đặt thư viện AI (google-generativeai) cho bạn, vui lòng đợi vài giây...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai"])
        import google.generativeai as genai
        print("Cài đặt xong! Đang mở ứng dụng...")
    except Exception as e:
        print("Không thể tự động cài đặt. Vui lòng gõ lệnh: pip install google-generativeai")
        raise e

class AIHelper:
    def __init__(self, api_key):
        self.api_key = api_key
        try:
            genai.configure(api_key=self.api_key)
            
            # Tự động quét và chọn Model khả dụng nhất với API Key của người dùng
            chosen_model = None
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if 'flash' in m.name:
                        chosen_model = m.name
                        break
            
            # Nếu không có flash, lấy đại model đầu tiên hỗ trợ
            if not chosen_model:
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        chosen_model = m.name
                        break
                        
            if not chosen_model:
                raise Exception("API Key của bạn không được cấp quyền truy cập bất kỳ model AI nào.")
                
            self.model = genai.GenerativeModel(chosen_model)
            self.chat = self.model.start_chat(history=[])
        except Exception as e:
            self.model = None
            print("Lỗi khởi tạo AI:", e)

    def get_response_stream(self, user_message, context_data):
        if not self.model:
            yield "Lỗi: Chưa kết nối được với AI. Vui lòng kiểm tra lại API Key."
            return
        
        system_prompt = f"""Bạn là một chuyên gia tư vấn tài chính ảo của ngân hàng Bankdash.
Dưới đây là DỮ LIỆU TÀI CHÍNH HIỆN TẠI của người dùng đang chat với bạn:
{context_data}

Yêu cầu:
- Xưng hô "tôi" và "bạn".
- Hãy đọc hiểu dữ liệu trên để trả lời câu hỏi của khách hàng.
- Trả lời ngắn gọn, lịch sự, dễ hiểu và chuyên nghiệp.
- Cấm bịa đặt các giao dịch hoặc số tiền không có trong dữ liệu.
- Nếu người dùng xin lời khuyên, hãy phân tích mức chi tiêu và đưa ra lời khuyên tiết kiệm.
"""
        full_prompt = system_prompt + "\n\nCâu hỏi của khách hàng: " + user_message
        
        try:
            response = self.chat.send_message(full_prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"Xin lỗi, tôi không thể xử lý yêu cầu lúc này. Lỗi: {str(e)}"
