import customtkinter as ctk
import psycopg2
from tkinter import messagebox, ttk
from datetime import datetime, timedelta

# Cấu hình giao diện tổng thể
ctk.set_appearance_mode("Light")

# --- BẢNG MÀU TÙY CHỈNH ---
M_CAM_CHINH = "#FF8C00"      
M_CAM_HOVER = "#E67300"      
M_CAM_NHAT = "#FFF0E0"       
M_TRANG = "#FFFFFF"          
M_DEN_CHU = "#333333"        

# ========================================================== #
# PHẦN 1: LỚP XỬ LÝ DATABASE CHUẨN (BACKEND)
# ========================================================== #
class BankingSystem:
    def __init__(self):
        self.conn = self.get_db_connection()
        self.current_user = None
        self.setup_database_updates() 

    def get_db_connection(self):
        try:
            return psycopg2.connect(
                dbname="nganhang", user="postgres", password="123456", host="localhost", port="5432"
            )
        except Exception as e:
            return None

    def setup_database_updates(self):
        """Tự động nâng cấp Database: Thêm trạng thái thẻ & Tài khoản cho Khách hàng"""
        if self.conn:
            try:
                with self.conn.cursor() as cur:
                    cur.execute("ALTER TABLE the ADD COLUMN IF NOT EXISTS trang_thai VARCHAR(20) DEFAULT 'Hoat dong'")
                    cur.execute("ALTER TABLE khach_hang ADD COLUMN IF NOT EXISTS username VARCHAR(50)")
                    cur.execute("ALTER TABLE khach_hang ADD COLUMN IF NOT EXISTS password VARCHAR(255)")
                    self.conn.commit()
            except:
                self.conn.rollback()

    def login(self, username, password):
        with self.conn.cursor() as cur:
            # 1. Ưu tiên kiểm tra xem có phải Nhân viên / Quản lý không
            cur.execute("SELECT ma_nv, ho_ten, vai_tro FROM nhan_vien WHERE username = %s AND password = %s", (username, password))
            user = cur.fetchone()
            if user:
                self.current_user = {'ma': user[0], 'ho_ten': user[1], 'vai_tro': user[2]}
                return True
            
            # 2. Nếu không phải nhân viên, kiểm tra xem có phải Khách hàng không
            cur.execute("SELECT ma_kh, ho_ten FROM khach_hang WHERE username = %s AND password = %s", (username, password))
            kh = cur.fetchone()
            if kh:
                self.current_user = {'ma': kh[0], 'ho_ten': kh[1], 'vai_tro': 'khachhang'}
                return True
                
            return False

    def dang_ky_khach_hang(self, ma_kh, ho_ten, cmnd, ngay_sinh, username, password):
        try:
            with self.conn.cursor() as cur:
                # Kiểm tra trùng lặp
                cur.execute("SELECT ma_kh FROM khach_hang WHERE ma_kh = %s OR cmnd = %s", (ma_kh, cmnd))
                if cur.fetchone(): return False, "Mã khách hàng hoặc CMND/CCCD đã tồn tại!"
                
                cur.execute("SELECT ma_kh FROM khach_hang WHERE username = %s", (username,))
                if cur.fetchone(): return False, "Tên đăng nhập đã có người sử dụng!"

                cur.execute(
                    "INSERT INTO khach_hang (ma_kh, ho_ten, cmnd, ngay_sinh, username, password) VALUES (%s, %s, %s, %s, %s, %s)", 
                    (ma_kh, ho_ten, cmnd, ngay_sinh, username, password)
                )
                self.conn.commit()
                return True, "Đăng ký Internet Banking thành công! Bạn có thể đăng nhập ngay."
        except Exception as e:
            self.conn.rollback()
            return False, f"Lỗi DB: {str(e)}"

    def nap_tien(self, so_nhan, so_tien, noi_dung):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT so_tk FROM the WHERE so_the = %s", (so_nhan,))
                the_info = cur.fetchone()
                tk_dich = the_info[0] if the_info else so_nhan

                cur.execute("UPDATE tai_khoan SET so_du = so_du + %s WHERE so_tk = %s RETURNING so_du", (so_tien, tk_dich))
                if cur.rowcount == 0: return False, "Không tìm thấy số tài khoản hoặc số thẻ!"
                
                cur.execute("INSERT INTO giao_dich (tk_dich, loai_gd, so_tien, noi_dung) VALUES (%s, 'Nạp tiền', %s, %s)", (tk_dich, so_tien, noi_dung))
                self.conn.commit()
                return True, f"Giao dịch thành công vào tài khoản: {tk_dich}!"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)

    def chuyen_khoan(self, tk_nguon, tk_dich, so_tien, noi_dung):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT so_du FROM tai_khoan WHERE so_tk = %s", (tk_nguon,))
                row = cur.fetchone()
                if not row: return False, "Tài khoản nguồn không tồn tại!"
                if row[0] < float(so_tien): return False, "Số dư không đủ!"

                cur.execute("UPDATE tai_khoan SET so_du = so_du - %s WHERE so_tk = %s", (so_tien, tk_nguon))
                cur.execute("UPDATE tai_khoan SET so_du = so_du + %s WHERE so_tk = %s RETURNING so_du", (so_tien, tk_dich))
                if cur.rowcount == 0:
                    self.conn.rollback()
                    return False, "Tài khoản đích không tồn tại!"

                cur.execute("INSERT INTO giao_dich (tk_nguon, tk_dich, loai_gd, so_tien, noi_dung) VALUES (%s, %s, 'Chuyển khoản', %s, %s)", (tk_nguon, tk_dich, so_tien, noi_dung))
                self.conn.commit()
                return True, "Chuyển khoản thành công!"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)

    # --- HÀM QUẢN LÝ THẺ ---
    def lay_ds_loai_the(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT ma_loai_the, ten_loai FROM loai_the")
            return cur.fetchall()

    def tao_the_moi(self, so_the, so_tk, ma_loai_the, pin):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT so_tk FROM tai_khoan WHERE so_tk = %s", (so_tk,))
                if not cur.fetchone(): return False, "Số tài khoản chưa tồn tại!"
                ngay_hh = (datetime.now() + timedelta(days=365*4)).strftime('%Y-%m-%d')
                cur.execute("INSERT INTO the (so_the, so_tk, ma_loai_the, ngay_het_han, pin, trang_thai) VALUES (%s, %s, %s, %s, %s, 'Hoat dong')", (so_the, so_tk, ma_loai_the, ngay_hh, pin))
                self.conn.commit()
                return True, "Phát hành thẻ thành công!"
        except Exception as e:
            self.conn.rollback()
            return False, f"Lỗi: {str(e)}"

    def lay_ds_the(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT t.so_the, t.so_tk, kh.ho_ten, l.ten_loai, t.ngay_het_han, t.trang_thai FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk JOIN khach_hang kh ON tk.ma_kh = kh.ma_kh JOIN loai_the l ON t.ma_loai_the = l.ma_loai_the")
            return cur.fetchall()

    def doi_trang_thai_the(self, so_the, action):
        try:
            with self.conn.cursor() as cur:
                if action == 'khoa':
                    cur.execute("UPDATE the SET trang_thai = 'Da Khoa' WHERE so_the = %s", (so_the,))
                elif action == 'mo_khoa':
                    cur.execute("UPDATE the SET trang_thai = 'Hoat dong' WHERE so_the = %s", (so_the,))
                else:
                    cur.execute("DELETE FROM the WHERE so_the = %s", (so_the,))
                self.conn.commit()
                return True, "Thao tác trên thẻ thành công!"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)

    # --- HÀM TRA CỨU & QUẢN LÝ ---
    def sao_ke_giao_dich(self, so_tk):
        with self.conn.cursor() as cur:
            cur.execute("SELECT ma_gd, loai_gd, so_tien, ngay_gd, tk_nguon, tk_dich, noi_dung FROM giao_dich WHERE tk_nguon = %s OR tk_dich = %s ORDER BY ngay_gd DESC", (so_tk, so_tk))
            return cur.fetchall()

    def lay_ds_khach_hang(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT kh.ma_kh, kh.ho_ten, kh.cmnd, tk.so_tk, tk.so_du, tk.trang_thai FROM khach_hang kh LEFT JOIN tai_khoan tk ON kh.ma_kh = tk.ma_kh ORDER BY kh.ma_kh")
            return cur.fetchall()

    def lay_ds_nhan_su(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT ma_nv, ho_ten, username, vai_tro, luong FROM nhan_vien ORDER BY vai_tro")
            return cur.fetchall()

    def tao_nhan_vien(self, ma_nv, ho_ten, user, pwd, vai_tro, luong):
        try:
            with self.conn.cursor() as cur:
                cur.execute("INSERT INTO nhan_vien (ma_nv, ho_ten, username, password, vai_tro, luong) VALUES (%s, %s, %s, %s, %s, %s)", (ma_nv, ho_ten, user, pwd, vai_tro, luong))
                self.conn.commit()
                return True, "Thêm nhân sự thành công!"
        except Exception as e:
            self.conn.rollback()
            return False, f"Lỗi DB: {str(e)}"

    def dieu_chinh_chuc_vu(self, ma_nv, vai_tro_moi):
        try:
            with self.conn.cursor() as cur:
                cur.execute("UPDATE nhan_vien SET vai_tro = %s WHERE ma_nv = %s RETURNING ma_nv", (vai_tro_moi, ma_nv))
                if cur.rowcount == 0: return False, "Không tìm thấy Mã nhân viên này!"
                self.conn.commit()
                return True, f"Đã đổi chức vụ thành {vai_tro_moi.upper()}"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)

    def xoa_nhan_vien(self, ma_nv, role_nguoi_xoa):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT vai_tro FROM nhan_vien WHERE ma_nv = %s", (ma_nv,))
                target = cur.fetchone()
                if not target: return False, "Không tìm thấy nhân viên!"
                if role_nguoi_xoa == 'quanly' and target[0] in ['admin', 'quanly']:
                    return False, "Quản lý không có quyền xóa Admin hoặc Quản lý khác!"
                cur.execute("DELETE FROM nhan_vien WHERE ma_nv = %s", (ma_nv,))
                self.conn.commit()
                return True, "Xóa nhân viên thành công!"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)


# ========================================================== #
# PHẦN 2: LỚP GIAO DIỆN FRONTEND
# ========================================================== #
class BankingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Hệ Thống Ngân Hàng - Quản Lý Toàn Diện")
        self.geometry("1100x750")
        self.resizable(False, False)
        self.configure(fg_color=M_TRANG) 
        
        self.db = BankingSystem()
        if not self.db.conn:
            messagebox.showerror("Lỗi", "Mất kết nối Database! Vui lòng kiểm tra PostgreSQL.")
            self.destroy()
            return
            
        self.setup_treeview_style()
        self.show_login()

    def setup_treeview_style(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=M_TRANG, foreground=M_DEN_CHU, rowheight=30, fieldbackground=M_TRANG, bordercolor=M_CAM_CHINH, borderwidth=0, font=("Arial", 11))
        style.map('Treeview', background=[('selected', M_CAM_CHINH)])
        style.configure("Treeview.Heading", background=M_CAM_CHINH, foreground=M_TRANG, font=('Arial', 11, 'bold'), padding=(0, 5))
        style.map("Treeview.Heading", background=[('active', M_CAM_HOVER)])

    def clear_window(self):
        for widget in self.winfo_children(): widget.destroy()

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()

    def create_form_entry(self, parent, placeholder, is_password=False):
        e = ctk.CTkEntry(master=parent, placeholder_text=placeholder, width=350, height=40, font=("Arial", 14), fg_color=M_TRANG, text_color=M_DEN_CHU, border_color="lightgray", show="*" if is_password else "")
        e.pack(pady=10)
        return e

    def tao_bang(self, parent, columns, widths):
        frame_table = ctk.CTkFrame(master=parent, fg_color=M_TRANG, border_width=1, border_color="lightgray")
        frame_table.pack(fill="both", expand=True, pady=10)
        tree = ttk.Treeview(frame_table, columns=columns, show="headings", height=12)
        for col, w in zip(columns, widths):
            tree.column(col, width=w, anchor="center")
            tree.heading(col, text=col)
        tree.pack(fill="both", expand=True, padx=2, pady=2)
        return tree

    # --- ĐĂNG NHẬP ---
    def show_login(self):
        self.clear_window()
        frame = ctk.CTkFrame(master=self, width=450, height=450, fg_color=M_TRANG, border_width=2, border_color=M_CAM_CHINH, corner_radius=15)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(master=frame, text="NGÂN HÀNG SỐ", font=("Helvetica", 28, "bold"), text_color=M_CAM_CHINH).place(relx=0.5, rely=0.15, anchor="center")
        
        self.e_user = ctk.CTkEntry(master=frame, width=280, height=40, placeholder_text="Tên đăng nhập")
        self.e_user.place(relx=0.5, rely=0.4, anchor="center")
        self.e_pass = ctk.CTkEntry(master=frame, width=280, height=40, placeholder_text="Mật khẩu", show="*")
        self.e_pass.place(relx=0.5, rely=0.55, anchor="center")
        
        ctk.CTkButton(master=frame, text="ĐĂNG NHẬP", width=280, height=45, fg_color=M_CAM_CHINH, command=self.do_login).place(relx=0.5, rely=0.75, anchor="center")
        ctk.CTkButton(master=frame, text="Mở tài khoản Khách Hàng", width=280, height=45, fg_color="transparent", border_width=2, border_color=M_CAM_CHINH, text_color=M_CAM_CHINH, command=self.show_register_screen).place(relx=0.5, rely=0.88, anchor="center")

    def do_login(self):
        if self.db.login(self.e_user.get(), self.e_pass.get()): 
            self.show_dashboard()
        else: 
            messagebox.showerror("Lỗi", "Sai tên đăng nhập hoặc mật khẩu!")

    def show_register_screen(self):
        self.clear_window()
        # Mở rộng frame để chứa thêm Username/Password
        frame = ctk.CTkFrame(master=self, width=500, height=600, fg_color=M_TRANG, border_width=2, border_color=M_CAM_CHINH)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(master=frame, text="ĐĂNG KÝ INTERNET BANKING", font=("Helvetica", 20, "bold"), text_color=M_CAM_CHINH).pack(pady=(20,10))
        
        e_makh = self.create_form_entry(frame, "Mã KH (VD: KH001)")
        e_hoten = self.create_form_entry(frame, "Họ và Tên")
        e_cmnd = self.create_form_entry(frame, "CMND / CCCD")
        e_ns = self.create_form_entry(frame, "Ngày sinh (YYYY-MM-DD)")
        
        ctk.CTkLabel(master=frame, text="Tài khoản đăng nhập app:", font=("Arial", 12, "italic"), text_color="gray").pack()
        e_username = self.create_form_entry(frame, "Tên đăng nhập mong muốn")
        e_password = self.create_form_entry(frame, "Mật khẩu", is_password=True)

        def submit_reg():
            s, m = self.db.dang_ky_khach_hang(e_makh.get(), e_hoten.get(), e_cmnd.get(), e_ns.get(), e_username.get(), e_password.get())
            if s: 
                messagebox.showinfo("Thành công", m)
                self.show_login()
            else: messagebox.showerror("Lỗi", m)

        frame_btn = ctk.CTkFrame(master=frame, fg_color="transparent")
        frame_btn.pack(pady=20)
        ctk.CTkButton(master=frame_btn, text="XÁC NHẬN", width=140, fg_color=M_CAM_CHINH, command=submit_reg).pack(side="left", padx=10)
        ctk.CTkButton(master=frame_btn, text="HỦY", width=140, fg_color="gray", command=self.show_login).pack(side="left", padx=10)

    # --- DASHBOARD CHÍNH (Đã phân nhánh Khách hàng / Nhân viên) ---
    def show_dashboard(self):
        self.clear_window()
        role = self.db.current_user['vai_tro']
        ho_ten = self.db.current_user['ho_ten']
        
        sidebar = ctk.CTkFrame(master=self, width=220, fg_color=M_CAM_NHAT, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        
        ctk.CTkLabel(master=sidebar, text="BANKING PRO", font=("Helvetica", 20, "bold"), text_color=M_CAM_CHINH).pack(pady=(20, 10))
        
        frame_user = ctk.CTkFrame(master=sidebar, fg_color="transparent")
        frame_user.pack(pady=(0, 20))
        ctk.CTkLabel(master=frame_user, text=f"Xin chào: {ho_ten}", font=("Arial", 14, "bold"), text_color=M_DEN_CHU).pack()
        ctk.CTkLabel(master=frame_user, text=f"({role.upper()})", font=("Arial", 12, "italic"), text_color=M_CAM_CHINH).pack()
        
        # --- RẼ NHÁNH GIAO DIỆN HIỂN THỊ DỰA TRÊN QUYỀN ---
        if role == 'khachhang':
            # Khách hàng chỉ thấy 2 chức năng này
            self.create_menu_btn(sidebar, "1. Chuyển Khoản", self.ui_chuyen_khoan)
            self.create_menu_btn(sidebar, "2. Sao Kê Của Tôi", self.ui_sao_ke)
        else:
            # Nhân sự nội bộ thấy các chức năng nghiệp vụ
            self.create_menu_btn(sidebar, "1. Nạp Tiền Quầy", self.ui_nap_tien)
            self.create_menu_btn(sidebar, "2. Chuyển Khoản", self.ui_chuyen_khoan)
            self.create_menu_btn(sidebar, "3. Quản Lý Thẻ ATM", self.ui_quan_ly_the)
            self.create_menu_btn(sidebar, "4. Tra Cứu Sao Kê", self.ui_sao_ke)
            
            ctk.CTkLabel(master=sidebar, text="-- Quản Trị --", text_color="gray").pack(pady=(15, 5))
            self.create_menu_btn(sidebar, "5. Tài khoản KH", self.ui_quan_ly_khach_hang)
            
            if role in ['admin', 'quanly']:
                self.create_menu_btn(sidebar, "6. Quản Lý Nhân Sự", self.ui_nhan_su)

        ctk.CTkButton(master=sidebar, text="Đăng Xuất", fg_color="transparent", border_width=2, border_color=M_CAM_CHINH, text_color=M_CAM_CHINH, command=self.show_login).pack(side="bottom", pady=20)

        self.main_frame = ctk.CTkFrame(master=self, fg_color=M_TRANG, corner_radius=0)
        self.main_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(master=self.main_frame, text="CHỌN CHỨC NĂNG BÊN TRÁI ĐỂ BẮT ĐẦU", font=("Helvetica", 22, "bold"), text_color="lightgray").place(relx=0.5, rely=0.5, anchor="center")

    def create_menu_btn(self, parent, text, command):
        ctk.CTkButton(master=parent, text=text, anchor="w", fg_color="transparent", text_color=M_DEN_CHU, hover_color=M_CAM_CHINH, font=("Arial", 14), command=command).pack(pady=5, padx=10, fill="x")

    # ================= CÁC FORM CHỨC NĂNG ================= #
    def ui_nap_tien(self):
        self.clear_main_frame()
        ctk.CTkLabel(master=self.main_frame, text="NẠP TIỀN / CHUYỂN TIỀN VÀO THẺ (TẠI QUẦY)", font=("Helvetica", 22, "bold"), text_color=M_CAM_CHINH).pack(pady=(20, 30))
        e_tk = self.create_form_entry(self.main_frame, "Nhập Số Tài Khoản hoặc Số Thẻ")
        e_tien = self.create_form_entry(self.main_frame, "Số tiền nạp (VNĐ)")
        e_nd = self.create_form_entry(self.main_frame, "Nội dung giao dịch")
        
        def submit():
            success, msg = self.db.nap_tien(e_tk.get(), e_tien.get(), e_nd.get())
            messagebox.showinfo("Kết quả", msg) if success else messagebox.showerror("Lỗi", msg)
        ctk.CTkButton(master=self.main_frame, text="XÁC NHẬN NẠP TIỀN", width=350, height=45, fg_color=M_CAM_CHINH, command=submit).pack(pady=20)

    def ui_chuyen_khoan(self):
        self.clear_main_frame()
        ctk.CTkLabel(master=self.main_frame, text="CHUYỂN KHOẢN", font=("Helvetica", 22, "bold"), text_color=M_CAM_CHINH).pack(pady=20)
        e_n = self.create_form_entry(self.main_frame, "Số TK Nguồn (Trích tiền)")
        e_d = self.create_form_entry(self.main_frame, "Số TK Đích (Nhận tiền)")
        e_t = self.create_form_entry(self.main_frame, "Số tiền")
        e_nd = self.create_form_entry(self.main_frame, "Nội dung")
        def submit():
            success, msg = self.db.chuyen_khoan(e_n.get(), e_d.get(), e_t.get(), e_nd.get())
            messagebox.showinfo("Kết quả", msg) if success else messagebox.showerror("Lỗi", msg)
        ctk.CTkButton(master=self.main_frame, text="XÁC NHẬN CHUYỂN", width=350, height=45, fg_color=M_CAM_CHINH, command=submit).pack(pady=20)

    def ui_quan_ly_the(self):
        self.clear_main_frame()
        ctk.CTkLabel(master=self.main_frame, text="QUẢN LÝ THẺ KHÁCH HÀNG", font=("Helvetica", 20, "bold"), text_color=M_CAM_CHINH).pack(pady=(5, 5))

        tabview = ctk.CTkTabview(master=self.main_frame, fg_color=M_TRANG, segmented_button_selected_color=M_CAM_CHINH)
        tabview.pack(fill="both", expand=True, padx=10, pady=5)

        tab1 = tabview.add("Danh Sách Thẻ")
        tab2 = tabview.add("Mở Thẻ Mới")

        cols = ("Số Thẻ", "Số TK Nối", "Chủ Thẻ", "Loại Thẻ", "Ngày Hết Hạn", "Trạng Thái")
        widths = (120, 100, 150, 100, 100, 100)
        tree_the = self.tao_bang(tab1, cols, widths)

        def load_the():
            for i in tree_the.get_children(): tree_the.delete(i)
            for r in self.db.lay_ds_the(): tree_the.insert("", "end", values=r)
        load_the()

        frame_btn = ctk.CTkFrame(master=tab1, fg_color="transparent")
        frame_btn.pack(pady=10)
        
        def thao_tac_the(action):
            selected = tree_the.selection()
            if not selected: return messagebox.showwarning("Cảnh báo", "Vui lòng chọn 1 thẻ trong bảng!")
            so_the = tree_the.item(selected[0])['values'][0]
            if messagebox.askyesno("Xác nhận", f"Thực hiện thao tác trên thẻ {so_the}?"):
                s, m = self.db.doi_trang_thai_the(so_the, action)
                if s: 
                    messagebox.showinfo("Thành công", m)
                    load_the()
                else: messagebox.showerror("Lỗi", m)

        ctk.CTkButton(frame_btn, text="Khóa Thẻ", width=120, fg_color="orange", command=lambda: thao_tac_the('khoa')).pack(side="left", padx=10)
        ctk.CTkButton(frame_btn, text="Mở Khóa", width=120, fg_color="green", command=lambda: thao_tac_the('mo_khoa')).pack(side="left", padx=10)
        ctk.CTkButton(frame_btn, text="Xóa Thẻ", width=120, fg_color="red", command=lambda: thao_tac_the('xoa')).pack(side="left", padx=10)

        e_sothe = self.create_form_entry(tab2, "Nhập Số Thẻ (16 số)")
        e_sotk = self.create_form_entry(tab2, "Số Tài Khoản liên kết")
        
        loai_the_db = self.db.lay_ds_loai_the()
        ds_loai = [f"{r[0]} - {r[1]}" for r in loai_the_db] if loai_the_db else ["Không có dữ liệu loại thẻ"]
        
        cb_loai = ctk.CTkComboBox(tab2, values=ds_loai, width=350, height=40)
        cb_loai.pack(pady=10)
        e_pin = self.create_form_entry(tab2, "Nhập mã PIN (6 số)")

        def tao_the():
            ma_loai = cb_loai.get().split(" - ")[0]
            s, m = self.db.tao_the_moi(e_sothe.get(), e_sotk.get(), ma_loai, e_pin.get())
            if s:
                messagebox.showinfo("Thành công", m)
                load_the()
            else: messagebox.showerror("Lỗi", m)

        ctk.CTkButton(tab2, text="PHÁT HÀNH THẺ", width=350, height=45, fg_color=M_CAM_CHINH, command=tao_the).pack(pady=20)

    def ui_sao_ke(self):
        self.clear_main_frame()
        ctk.CTkLabel(master=self.main_frame, text="SAO KÊ GIAO DỊCH", font=("Helvetica", 22, "bold"), text_color=M_CAM_CHINH).pack(pady=(10, 20))
        
        frame_top = ctk.CTkFrame(master=self.main_frame, fg_color="transparent")
        frame_top.pack(fill="x", pady=10)
        e_tk = ctk.CTkEntry(master=frame_top, placeholder_text="Nhập Số tài khoản...", width=400, height=40, font=("Arial", 14), fg_color=M_TRANG, text_color=M_DEN_CHU)
        e_tk.pack(side="left", padx=(0, 10))

        cols = ("Mã GD", "Loại", "Số tiền", "Thời gian", "Nguồn", "Đích", "Nội dung")
        widths = (50, 100, 120, 160, 100, 100, 200)
        tree = self.tao_bang(self.main_frame, cols, widths)

        def tim_kiem():
            for i in tree.get_children(): tree.delete(i)
            rows = self.db.sao_ke_giao_dich(e_tk.get())
            for row in rows:
                r = list(row)
                r[2] = f"{r[2]:,.0f} đ"
                tree.insert("", "end", values=r)

        ctk.CTkButton(master=frame_top, text="TRA CỨU", width=120, height=40, fg_color=M_CAM_CHINH, command=tim_kiem).pack(side="left")

    def ui_quan_ly_khach_hang(self):
        self.clear_main_frame()
        ctk.CTkLabel(master=self.main_frame, text="TỔNG HỢP TÀI KHOẢN KHÁCH HÀNG", font=("Helvetica", 20, "bold"), text_color=M_CAM_CHINH).pack(pady=(10, 10))
        cols = ("Mã KH", "Họ Tên", "CMND", "Số TK", "Số Dư", "Trạng Thái")
        widths = (80, 150, 100, 100, 120, 100)
        tree = self.tao_bang(self.main_frame, cols, widths)

        for row in self.db.lay_ds_khach_hang():
            r = list(row)
            if r[4] is not None: r[4] = f"{r[4]:,.0f} đ"
            else: r[4] = "Chưa có TK"
            tree.insert("", "end", values=r)

    def ui_nhan_su(self):
        self.clear_main_frame()
        ctk.CTkLabel(master=self.main_frame, text="QUẢN LÝ NHÂN SỰ", font=("Helvetica", 20, "bold"), text_color=M_CAM_CHINH).pack(pady=(5, 5))

        tabview = ctk.CTkTabview(master=self.main_frame, fg_color=M_TRANG, segmented_button_selected_color=M_CAM_CHINH)
        tabview.pack(fill="both", expand=True, padx=10, pady=5)

        tab1 = tabview.add("Danh Sách & Xóa")
        tab2 = tabview.add("Thêm Nhân Viên")
        if self.db.current_user['vai_tro'] == 'admin':
            tab3 = tabview.add("Thăng/Giáng Chức")

        cols = ("Mã NV", "Họ Tên", "Tài Khoản", "Vai Trò", "Lương CB")
        widths = (80, 150, 100, 100, 120)
        tree_ns = self.tao_bang(tab1, cols, widths)
        
        def load_ds_nhansu():
            for i in tree_ns.get_children(): tree_ns.delete(i)
            for r in self.db.lay_ds_nhan_su():
                rf = list(r)
                rf[4] = f"{rf[4]:,.0f} đ"
                tree_ns.insert("", "end", values=rf)
        load_ds_nhansu()

        def xoa_nv():
            selected = tree_ns.selection()
            if not selected: return messagebox.showwarning("Cảnh báo", "Vui lòng chọn 1 nhân viên trong bảng!")
            ma_nv = tree_ns.item(selected[0])['values'][0]
            if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa nhân viên {ma_nv} khỏi hệ thống?"):
                s, m = self.db.xoa_nhan_vien(ma_nv, self.db.current_user['vai_tro'])
                if s:
                    messagebox.showinfo("Thành công", m)
                    load_ds_nhansu()
                else: messagebox.showerror("Lỗi", m)

        ctk.CTkButton(tab1, text="XÓA NHÂN VIÊN ĐANG CHỌN", fg_color="red", command=xoa_nv).pack(pady=10)

        e_ma = self.create_form_entry(tab2, "Mã NV (VD: NV03)")
        e_ten = self.create_form_entry(tab2, "Họ Tên Nhân Viên")
        e_usr = self.create_form_entry(tab2, "Username đăng nhập")
        e_pwd = self.create_form_entry(tab2, "Mật khẩu")
        e_luong = self.create_form_entry(tab2, "Lương cơ bản (> 3tr)")
        
        roles_allowed = ["nhanvien"] if self.db.current_user['vai_tro'] == 'quanly' else ["nhanvien", "quanly", "admin"]
        cb_role = ctk.CTkComboBox(tab2, values=roles_allowed, width=350, height=40, font=("Arial", 14))
        cb_role.pack(pady=10)

        def tao_tk():
            s, m = self.db.tao_nhan_vien(e_ma.get(), e_ten.get(), e_usr.get(), e_pwd.get(), cb_role.get(), e_luong.get())
            if s: 
                messagebox.showinfo("Thành công", m)
                load_ds_nhansu() 
            else: messagebox.showerror("Lỗi", m)
            
        ctk.CTkButton(tab2, text="LƯU TÀI KHOẢN", width=350, height=45, fg_color=M_CAM_CHINH, command=tao_tk).pack(pady=20)

        if self.db.current_user['vai_tro'] == 'admin':
            e_matc = self.create_form_entry(tab3, "Nhập Mã NV cần điều chỉnh")
            cb_role_moi = ctk.CTkComboBox(tab3, values=["nhanvien", "quanly", "admin"], width=350, height=40)
            cb_role_moi.pack(pady=10)
            
            def luu_chuc_vu():
                s, m = self.db.dieu_chinh_chuc_vu(e_matc.get(), cb_role_moi.get())
                if s: 
                    messagebox.showinfo("Thành công", m)
                    load_ds_nhansu()
                else: messagebox.showerror("Lỗi", m)
                
            ctk.CTkButton(tab3, text="CẬP NHẬT CHỨC VỤ", width=350, height=45, fg_color="purple", command=luu_chuc_vu).pack(pady=20)

# ================= VẬN HÀNH ================= #
if __name__ == "__main__":
    app = BankingApp()
    app.mainloop()