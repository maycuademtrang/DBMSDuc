# 🏦 Ngân Hàng Bankdash - Đồ Án Cơ Sở Dữ Liệu

Dự án này là một hệ thống ngân hàng mô phỏng toàn diện, được thiết kế để áp dụng các kiến thức chuyên sâu về Hệ Quản Trị Cơ Sở Dữ Liệu (DBMS) như: **Trigger, Stored Procedure, Transaction, View**.
Đặc biệt, hệ thống được tích hợp **AI Tài Chính (Gemini 1.5)** để tư vấn chi tiêu và trả lời câu hỏi trực tiếp dựa trên dữ liệu giao dịch của khách hàng.

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy App
1. **Cài đặt thư viện Python:** Mở Terminal và chạy lệnh sau:
   ```bash
   pip install customtkinter psycopg2-binary google-generativeai requests
   ```
2. **Setup Database:**
   - Mở pgAdmin (hoặc bất kỳ tool quản lý PostgreSQL nào).
   - Chạy toàn bộ file `lưu-code-databsae.sql` để tạo Cấu trúc bảng, Trigger, Stored Procedure, View và **tự động chèn sẵn dữ liệu mẫu**.
3. **Khởi chạy ứng dụng:**
   ```bash
   python main.py
   ```

---

## 🔑 Danh Sách Tài Khoản Đăng Nhập Mẫu
Do dữ liệu đã được tự động chèn khi bạn chạy file SQL, bạn có thể dùng ngay các tài khoản dưới đây để đăng nhập:

| Quyền Hạn | Tên Đăng Nhập (Username) | Mật khẩu (Password) | Người sở hữu | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| **Quản trị (Admin)** | `admin` | `123456` | Tổng Giám Đốc | Toàn quyền, quản lý nhân viên |
| **Quản lý** | `nva_quanly` | `123456` | Nguyễn Văn A | Quản lý sổ sách |
| **Giao dịch viên** | `ttb_nhanvien` | `123456` | Trần Thị B | Nạp tiền khách, mở thẻ |
| **Khách hàng 1** | `khachhang1` | `123456` | Phạm Văn Khách | Tài khoản (Số: 1111222233): 5 triệu, Thẻ (Số: 9704001234567890): 1tr5 |
| **Khách hàng 2** | `khachhang2` | `123456` | Lê Thị Thu | Tài khoản (Số: 4444555566): 3 triệu, Thẻ (Số: 4220000987654321): 500k |

---

## 🤖 Hướng dẫn Demo tính năng Trợ Lý AI
Để lấy điểm cộng từ giáo viên với tính năng AI:
1. Đăng nhập bằng tài khoản **Khách hàng 1** (`khachhang1` / `123456`).
2. Mở tab **🤖 Trợ Lý AI**.
3. Lấy API Key từ Google AI Studio (miễn phí) và dán vào ô nhập khóa.
4. Gõ câu hỏi: *"Chào bạn, tôi hiện đang có bao nhiêu tài sản tổng cộng? Cho tôi lời khuyên tiết kiệm."*
5. AI sẽ tự động đọc dữ liệu số dư từ Database của người dùng đó (Gồm số dư tài khoản và số dư thẻ ATM) và đưa ra tư vấn. 
