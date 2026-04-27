import customtkinter as ctk
import psycopg2
import random
from tkinter import messagebox, ttk
from datetime import datetime, timedelta

ctk.set_appearance_mode("Light")

M_BLUE_CHINH = "#2D60FF"       
M_BLUE_HOVER = "#1E4DB7"       
M_BG_APP = "#F5F7FA"           
M_BG_SIDEBAR = "#FFFFFF"       
M_TEXT_DARK = "#343C6A"        
M_TEXT_GREY = "#B1B1B1"        
M_TRANG = "#FFFFFF"            

# ========================================================== #
# PHẦN 1: LỚP XỬ LÝ DATABASE 
# ========================================================== #
class BankingSystem:
    def __init__(self):
        self.conn = self.get_db_connection()
        self.current_user = None

    def get_db_connection(self):
        try:
            return psycopg2.connect(dbname="nganhang", user="postgres", password="123456", host="localhost", port="5432")
        except Exception as e:
            return None

    def login(self, username, password):
        with self.conn.cursor() as cur:
            cur.execute("SELECT ma_nv, ho_ten, vai_tro FROM nhan_vien WHERE username = %s AND password = %s", (username, password))
            user = cur.fetchone()
            if user:
                self.current_user = {'ma': user[0], 'ho_ten': user[1], 'vai_tro': user[2]}
                return True
            cur.execute("SELECT ma_kh, ho_ten FROM khach_hang WHERE username = %s AND password = %s", (username, password))
            kh = cur.fetchone()
            if kh:
                self.current_user = {'ma': kh[0], 'ho_ten': kh[1], 'vai_tro': 'khachhang'}
                return True
            return False

    def dang_ky_khach_hang(self, ma_kh, ho_ten, cmnd, ngay_sinh, username, password):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT ma_kh FROM khach_hang WHERE ma_kh = %s OR cmnd = %s", (ma_kh, cmnd))
                if cur.fetchone(): return False, "Mã khách hàng hoặc CMND đã tồn tại!"
                cur.execute("SELECT username FROM khach_hang WHERE username = %s UNION SELECT username FROM nhan_vien WHERE username = %s", (username, username))
                if cur.fetchone(): return False, "Tên đăng nhập đã có người sử dụng!"
                
                cur.execute("INSERT INTO khach_hang (ma_kh, ho_ten, cmnd, ngay_sinh, username, password) VALUES (%s, %s, %s, %s, %s, %s)", (ma_kh, ho_ten, cmnd, ngay_sinh, username, password))
                
                while True:
                    so_tk = str(random.randint(1000000000, 9999999999))
                    cur.execute("SELECT so_tk FROM tai_khoan WHERE so_tk = %s", (so_tk,))
                    if not cur.fetchone(): break 
                
                cur.execute("INSERT INTO tai_khoan (so_tk, ma_kh, so_du) VALUES (%s, %s, 50000)", (so_tk, ma_kh))
                self.conn.commit()
                return True, f"Đăng ký thành công!\nHệ thống cấp Số TK mặc định: {so_tk}\nSố dư: 50,000đ"
        except Exception as e:
            self.conn.rollback()
            return False, f"Lỗi DB: {str(e)}"

    def chuyen_khoan(self, tk_nguon, tk_dich, so_tien, noi_dung):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT so_du, ma_kh FROM tai_khoan WHERE so_tk = %s", (tk_nguon,))
                row = cur.fetchone()
                if not row: return False, "Tài khoản nguồn không tồn tại!"
                if self.current_user['vai_tro'] == 'khachhang' and row[1] != self.current_user['ma']:
                    return False, "Chỉ được chuyển tiền từ số tài khoản của chính mình!"
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
                return True, f"Nạp tiền thành công!"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)

    # --- CÁC HÀM TRA CỨU TÊN MỚI ĐƯỢC CẬP NHẬT ---
    def lay_ten_chu_tai_khoan(self, so_tk):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT kh.ho_ten FROM tai_khoan tk JOIN khach_hang kh ON tk.ma_kh = kh.ma_kh WHERE tk.so_tk = %s", (so_tk,))
                res = cur.fetchone()
                return res[0] if res else None
        except: return None

    def lay_ten_tu_tk_hoac_the(self, so_nhan):
        """Hàm này dành riêng cho Nạp tiền (Quét cả TK và Thẻ)"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT kh.ho_ten FROM tai_khoan tk JOIN khach_hang kh ON tk.ma_kh = kh.ma_kh WHERE tk.so_tk = %s", (so_nhan,))
                res = cur.fetchone()
                if res: return res[0]
                
                cur.execute("SELECT kh.ho_ten FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk JOIN khach_hang kh ON tk.ma_kh = kh.ma_kh WHERE t.so_the = %s", (so_nhan,))
                res = cur.fetchone()
                return res[0] if res else None
        except: return None

    def lay_ds_tk_cua_khach(self, ma_kh):
        with self.conn.cursor() as cur:
            cur.execute("SELECT so_tk, so_du, ngay_mo, trang_thai FROM tai_khoan WHERE ma_kh = %s ORDER BY ngay_mo DESC", (ma_kh,))
            return cur.fetchall()

    def lay_ds_loai_the(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT ma_loai_the, ten_loai, dau_so FROM loai_the")
            return cur.fetchall()

    def tao_the_tu_dong(self, so_tk, ma_loai_the, pin, ma_kh=None):
        try:
            with self.conn.cursor() as cur:
                if ma_kh:
                    cur.execute("SELECT so_tk FROM tai_khoan WHERE so_tk = %s AND ma_kh = %s", (so_tk, ma_kh))
                    if not cur.fetchone(): return False, "Bạn không có quyền sở hữu số tài khoản này!"
                cur.execute("SELECT dau_so FROM loai_the WHERE ma_loai_the = %s", (ma_loai_the,))
                dau_so = cur.fetchone()[0]
                while True:
                    so_the = dau_so + "".join([str(random.randint(0,9)) for _ in range(12)])
                    cur.execute("SELECT so_the FROM the WHERE so_the = %s", (so_the,))
                    if not cur.fetchone(): break

                ngay_hh = (datetime.now() + timedelta(days=365*4)).strftime('%Y-%m-%d')
                cur.execute("INSERT INTO the (so_the, so_tk, ma_loai_the, ngay_het_han, pin, trang_thai) VALUES (%s, %s, %s, %s, %s, 'Hoat dong')", (so_the, so_tk, ma_loai_the, ngay_hh, pin))
                self.conn.commit()
                return True, f"Phát hành thẻ thành công!\nSố thẻ của bạn là: {so_the}"
        except Exception as e:
            self.conn.rollback()
            return False, f"Lỗi: {str(e)}"

    def lay_ds_the(self, ma_kh=None):
        with self.conn.cursor() as cur:
            if ma_kh:
                cur.execute("SELECT t.so_the, t.so_tk, kh.ho_ten, l.ten_loai, t.ngay_het_han, t.trang_thai FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk JOIN khach_hang kh ON tk.ma_kh = kh.ma_kh JOIN loai_the l ON t.ma_loai_the = l.ma_loai_the WHERE kh.ma_kh = %s", (ma_kh,))
            else:
                cur.execute("SELECT t.so_the, t.so_tk, kh.ho_ten, l.ten_loai, t.ngay_het_han, t.trang_thai FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk JOIN khach_hang kh ON tk.ma_kh = kh.ma_kh JOIN loai_the l ON t.ma_loai_the = l.ma_loai_the")
            return cur.fetchall()

    def doi_trang_thai_the(self, so_the, action):
        try:
            with self.conn.cursor() as cur:
                if action == 'khoa': cur.execute("UPDATE the SET trang_thai = 'Da Khoa' WHERE so_the = %s", (so_the,))
                elif action == 'mo_khoa': cur.execute("UPDATE the SET trang_thai = 'Hoat dong' WHERE so_the = %s", (so_the,))
                else: cur.execute("DELETE FROM the WHERE so_the = %s", (so_the,))
                self.conn.commit()
                return True, "Thao tác thành công!"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)

    def sao_ke_giao_dich(self, so_tk=None, ma_kh=None):
        with self.conn.cursor() as cur:
            if ma_kh:
                cur.execute("SELECT ma_gd, loai_gd, so_tien, ngay_gd, tk_nguon, tk_dich, noi_dung FROM giao_dich WHERE tk_nguon IN (SELECT so_tk FROM tai_khoan WHERE ma_kh = %s) OR tk_dich IN (SELECT so_tk FROM tai_khoan WHERE ma_kh = %s) ORDER BY ngay_gd DESC", (ma_kh, ma_kh))
            else:
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
                cur.execute("SELECT ma_nv FROM nhan_vien WHERE ma_nv = %s", (ma_nv,))
                if cur.fetchone(): return False, "Mã nhân viên đã tồn tại!"
                cur.execute("SELECT username FROM nhan_vien WHERE username = %s UNION SELECT username FROM khach_hang WHERE username = %s", (user, user))
                if cur.fetchone(): return False, "Tên đăng nhập đã có người dùng!"
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
                if cur.rowcount == 0: return False, "Không tìm thấy Mã nhân viên!"
                self.conn.commit()
                return True, f"Cập nhật thành {vai_tro_moi.upper()}"
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
                    return False, "Quản lý không thể xóa Admin/Quản lý khác!"
                cur.execute("DELETE FROM nhan_vien WHERE ma_nv = %s", (ma_nv,))
                self.conn.commit()
                return True, "Xóa nhân viên thành công!"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)

# ========================================================== #
# PHẦN 2: LỚP GIAO DIỆN CHUẨN BANKDASH
# ========================================================== #
class BankingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Bankdash - Hệ Thống Ngân Hàng Số")
        self.geometry("1150x750")
        self.resizable(False, False)
        self.configure(fg_color=M_BG_APP) 
        self.db = BankingSystem()
        if not self.db.conn:
            messagebox.showerror("Lỗi", "Mất kết nối Database!")
            self.destroy()
            return
        self.setup_treeview_style()
        self.show_login()

    def setup_treeview_style(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=M_TRANG, foreground=M_TEXT_DARK, rowheight=35, fieldbackground=M_TRANG, bordercolor=M_BG_APP, borderwidth=0, font=("Arial", 11))
        style.map('Treeview', background=[('selected', M_BLUE_CHINH)])
        style.configure("Treeview.Heading", background=M_TRANG, foreground=M_TEXT_GREY, font=('Arial', 11, 'bold'), borderwidth=0, padding=(0, 10))

    def clear_window(self):
        for widget in self.winfo_children(): widget.destroy()

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()

    def create_form_entry(self, parent, placeholder, is_password=False):
        e = ctk.CTkEntry(master=parent, placeholder_text=placeholder, width=350, height=45, font=("Arial", 14), fg_color=M_TRANG, text_color=M_TEXT_DARK, border_color="#E6EFF5", show="*" if is_password else "")
        e.pack(pady=10)
        return e

    def tao_bang(self, parent, columns, widths):
        frame_table = ctk.CTkFrame(master=parent, fg_color=M_TRANG, border_width=1, border_color="#E6EFF5", corner_radius=15)
        frame_table.pack(fill="both", expand=True, pady=15, padx=20)
        tree = ttk.Treeview(frame_table, columns=columns, show="headings", height=12)
        for col, w in zip(columns, widths):
            tree.column(col, width=w, anchor="center")
            tree.heading(col, text=col.upper()) 
        tree.pack(fill="both", expand=True, padx=5, pady=5)
        return tree

    # --- ĐĂNG NHẬP ---
    def show_login(self):
        self.clear_window()
        frame = ctk.CTkFrame(master=self, width=450, height=500, fg_color=M_TRANG, border_width=0, corner_radius=25)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(master=frame, text="💳 Bankdash.", font=("Helvetica", 32, "bold"), text_color=M_BLUE_CHINH).place(relx=0.5, rely=0.15, anchor="center")
        ctk.CTkLabel(master=frame, text="Vui lòng đăng nhập để tiếp tục", font=("Arial", 14), text_color=M_TEXT_GREY).place(relx=0.5, rely=0.25, anchor="center")
        
        self.e_user = ctk.CTkEntry(master=frame, width=300, height=45, placeholder_text="Tên đăng nhập", border_color="#E6EFF5")
        self.e_user.place(relx=0.5, rely=0.45, anchor="center")
        self.e_pass = ctk.CTkEntry(master=frame, width=300, height=45, placeholder_text="Mật khẩu", show="*", border_color="#E6EFF5")
        self.e_pass.place(relx=0.5, rely=0.6, anchor="center")
        
        ctk.CTkButton(master=frame, text="Đăng Nhập", width=300, height=45, font=("Arial", 15, "bold"), fg_color=M_BLUE_CHINH, hover_color=M_BLUE_HOVER, corner_radius=10, command=self.do_login).place(relx=0.5, rely=0.75, anchor="center")
        ctk.CTkButton(master=frame, text="Đăng ký tài khoản Khách Hàng", width=300, height=40, font=("Arial", 13), fg_color="transparent", text_color=M_BLUE_CHINH, hover_color="#F0F4FF", command=self.show_register_screen).place(relx=0.5, rely=0.88, anchor="center")

    def do_login(self):
        if self.db.login(self.e_user.get(), self.e_pass.get()): self.show_dashboard()
        else: messagebox.showerror("Lỗi", "Sai tên đăng nhập hoặc mật khẩu!")

    def show_register_screen(self):
        self.clear_window()
        frame = ctk.CTkFrame(master=self, width=500, height=650, fg_color=M_TRANG, border_width=0, corner_radius=25)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(master=frame, text="💳 Bankdash.", font=("Helvetica", 24, "bold"), text_color=M_BLUE_CHINH).pack(pady=(30,5))
        ctk.CTkLabel(master=frame, text="Mở tài khoản Internet Banking", font=("Arial", 14), text_color=M_TEXT_GREY).pack(pady=(0,20))
        
        e_makh = self.create_form_entry(frame, "Mã KH (VD: KH001)")
        e_hoten = self.create_form_entry(frame, "Họ và Tên")
        e_cmnd = self.create_form_entry(frame, "CMND / CCCD")
        e_ns = self.create_form_entry(frame, "Ngày sinh (YYYY-MM-DD)")
        e_username = self.create_form_entry(frame, "Tên đăng nhập App")
        e_password = self.create_form_entry(frame, "Mật khẩu", is_password=True)

        def submit_reg():
            s, m = self.db.dang_ky_khach_hang(e_makh.get(), e_hoten.get(), e_cmnd.get(), e_ns.get(), e_username.get(), e_password.get())
            if s: 
                messagebox.showinfo("Thành công", m)
                self.show_login()
            else: messagebox.showerror("Lỗi", m)

        frame_btn = ctk.CTkFrame(master=frame, fg_color="transparent")
        frame_btn.pack(pady=20)
        ctk.CTkButton(master=frame_btn, text="XÁC NHẬN", width=140, height=40, font=("Arial", 14, "bold"), fg_color=M_BLUE_CHINH, hover_color=M_BLUE_HOVER, corner_radius=10, command=submit_reg).pack(side="left", padx=10)
        ctk.CTkButton(master=frame_btn, text="Quay lại", width=140, height=40, font=("Arial", 14), fg_color="transparent", border_width=1, border_color="#E6EFF5", text_color=M_TEXT_DARK, hover_color="#F0F4FF", corner_radius=10, command=self.show_login).pack(side="left", padx=10)

    # --- DASHBOARD CHÍNH ---
    def show_dashboard(self):
        self.clear_window()
        role = self.db.current_user['vai_tro']
        ho_ten = self.db.current_user['ho_ten']
        
        self.main_container = ctk.CTkFrame(master=self, fg_color=M_BG_APP, corner_radius=0)
        self.main_container.pack(side="right", fill="both", expand=True)

        header = ctk.CTkFrame(master=self.main_container, height=80, fg_color=M_BG_APP, corner_radius=0)
        header.pack(fill="x", padx=30, pady=10)
        self.lbl_page_title = ctk.CTkLabel(master=header, text="Tổng Quan", font=("Helvetica", 26, "bold"), text_color=M_TEXT_DARK)
        self.lbl_page_title.pack(side="left")
        
        avatar_frame = ctk.CTkFrame(master=header, fg_color="transparent")
        avatar_frame.pack(side="right")
        ctk.CTkLabel(master=avatar_frame, text=f"Xin chào: {ho_ten}\n({role.upper()})", font=("Arial", 13, "bold"), text_color=M_TEXT_GREY, justify="right").pack(side="left", padx=10)
        ctk.CTkLabel(master=avatar_frame, text="👤", font=("Arial", 30), text_color=M_BLUE_CHINH).pack(side="left")

        self.main_frame = ctk.CTkFrame(master=self.main_container, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)

        sidebar = ctk.CTkFrame(master=self, width=250, fg_color=M_BG_SIDEBAR, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False) 
        
        ctk.CTkLabel(master=sidebar, text="💳 Bankdash.", font=("Helvetica", 26, "bold"), text_color=M_TEXT_DARK).pack(pady=(30, 40))
        
        self.active_menu_btn = None
        self.first_btn_info = None

        if role == 'khachhang':
            self.create_menu_btn(sidebar, "🏠", "Tổng Quan", self.ui_sao_ke)
            self.create_menu_btn(sidebar, "💸", "Chuyển Khoản", self.ui_chuyen_khoan)
            self.create_menu_btn(sidebar, "💳", "Thẻ Của Tôi", self.ui_quan_ly_the)
        else:
            self.create_menu_btn(sidebar, "🏠", "Tổng Quan", self.ui_sao_ke)
            self.create_menu_btn(sidebar, "📥", "Nạp Tiền (Quầy)", self.ui_nap_tien)
            self.create_menu_btn(sidebar, "💸", "Chuyển Khoản", self.ui_chuyen_khoan)
            self.create_menu_btn(sidebar, "💳", "Quản Lý Thẻ", self.ui_quan_ly_the)
            
            ctk.CTkLabel(master=sidebar, text="QUẢN TRỊ HỆ THỐNG", font=("Arial", 10, "bold"), text_color=M_TEXT_GREY, anchor="w").pack(fill="x", padx=30, pady=(15, 5))
            self.create_menu_btn(sidebar, "👤", "Tài Khoản KH", self.ui_quan_ly_khach_hang)
            
            if role in ['admin', 'quanly']:
                self.create_menu_btn(sidebar, "👥", "Nhân Sự", self.ui_nhan_su)

        self.create_menu_btn(sidebar, "🚪", "Đăng Xuất", self.show_login, is_bottom=True)

        if self.first_btn_info:
            b, cmd, txt = self.first_btn_info
            self.on_menu_click(b, cmd, txt)

    def create_menu_btn(self, parent, icon, text, command, is_bottom=False):
        btn = ctk.CTkButton(
            master=parent, text=f"   {icon}    {text}", anchor="w", 
            fg_color="transparent", text_color=M_TEXT_GREY, hover_color="#F0F4FF", 
            font=("Arial", 16, "bold"), height=45,
            command=lambda: self.on_menu_click(btn, command, text)
        )
        if is_bottom: btn.pack(side="bottom", pady=30, padx=15, fill="x")
        else: btn.pack(pady=5, padx=15, fill="x")
        
        if self.first_btn_info is None and not is_bottom:
            self.first_btn_info = (btn, command, text)

    def on_menu_click(self, btn, command, page_title):
        if self.active_menu_btn: self.active_menu_btn.configure(text_color=M_TEXT_GREY)
        btn.configure(text_color=M_BLUE_CHINH)
        self.active_menu_btn = btn
        if hasattr(self, "lbl_page_title"): self.lbl_page_title.configure(text=page_title)
        command()

    # ================= CÁC FORM CHỨC NĂNG ================= #
    def create_card_frame(self, title):
        self.clear_main_frame()
        card = ctk.CTkFrame(master=self.main_frame, fg_color=M_TRANG, corner_radius=20)
        card.pack(fill="both", expand=True, padx=30, pady=(0, 30))
        if title:
            ctk.CTkLabel(master=card, text=title, font=("Helvetica", 18, "bold"), text_color=M_TEXT_DARK).pack(pady=(20, 10), padx=20, anchor="w")
        return card

    def ui_nap_tien(self):
        card = self.create_card_frame("Giao Dịch Nạp Tiền (Nhân Viên Tại Quầy)")
        e_tk = self.create_form_entry(card, "Nhập Số Tài Khoản hoặc Số Thẻ")
        
        # --- HIỂN THỊ TÊN TỰ ĐỘNG CHO CHỨC NĂNG NẠP TIỀN ---
        lbl_ten = ctk.CTkLabel(master=card, text="", font=("Arial", 14, "bold"))
        lbl_ten.pack(pady=(0, 10))

        e_tien = self.create_form_entry(card, "Số tiền nạp (VNĐ)")
        e_nd = self.create_form_entry(card, "Nội dung giao dịch")
        
        def kiem_tra_ten(event):
            so_nhan = e_tk.get().strip()
            if len(so_nhan) >= 8:
                ten = self.db.lay_ten_tu_tk_hoac_the(so_nhan)
                if ten:
                    lbl_ten.configure(text=f"👤 Tên người nhận: {ten}", text_color="#16DBCC")
                else:
                    lbl_ten.configure(text="⚠️ Không tìm thấy Tài khoản / Thẻ này!", text_color="#FF4B4A")
            else:
                lbl_ten.configure(text="")

        e_tk.bind("<KeyRelease>", kiem_tra_ten)
        # ---------------------------------------------------

        def submit():
            success, msg = self.db.nap_tien(e_tk.get(), e_tien.get(), e_nd.get())
            messagebox.showinfo("Kết quả", msg) if success else messagebox.showerror("Lỗi", msg)
            if success:
                e_tk.delete(0, 'end')
                e_tien.delete(0, 'end')
                e_nd.delete(0, 'end')
                lbl_ten.configure(text="")
                
        ctk.CTkButton(master=card, text="Xác Nhận Nạp Tiền", width=350, height=45, font=("Arial", 14, "bold"), fg_color=M_BLUE_CHINH, hover_color=M_BLUE_HOVER, corner_radius=10, command=submit).pack(pady=30)

    def ui_chuyen_khoan(self):
        role = self.db.current_user['vai_tro']
        card = self.create_card_frame("Chuyển Khoản Nội Bộ")
        
        if role == 'khachhang':
            ds_tk = self.db.lay_ds_tk_cua_khach(self.db.current_user['ma'])
            ds_tk_cb = [f"{t[0]} (Số dư: {t[1]:,.0f}đ)" for t in ds_tk] if ds_tk else ["Bạn chưa có số tài khoản"]
            ctk.CTkLabel(master=card, text="Trích tiền từ tài khoản:", font=("Arial", 12), text_color=M_TEXT_GREY).pack()
            cb_tk_nguon = ctk.CTkComboBox(card, values=ds_tk_cb, width=350, height=45, button_color=M_BLUE_CHINH)
            cb_tk_nguon.pack(pady=5)
        else:
            e_n = self.create_form_entry(card, "Số TK Nguồn (Trích tiền)")

        e_d = self.create_form_entry(card, "Số TK Đích (Nhận tiền)")
        
        # --- HIỂN THỊ TÊN TỰ ĐỘNG KHI CHUYỂN KHOẢN ---
        lbl_ten_nguoi_nhan = ctk.CTkLabel(master=card, text="", font=("Arial", 14, "bold"))
        lbl_ten_nguoi_nhan.pack(pady=(0, 10))

        def kiem_tra_ten(event):
            so_tk_dich = e_d.get().strip() 
            if len(so_tk_dich) >= 8: 
                ten = self.db.lay_ten_chu_tai_khoan(so_tk_dich)
                if ten:
                    lbl_ten_nguoi_nhan.configure(text=f"👤 Người nhận: {ten}", text_color="#16DBCC") 
                else:
                    lbl_ten_nguoi_nhan.configure(text="⚠️ Không tìm thấy tài khoản!", text_color="#FF4B4A") 
            else:
                lbl_ten_nguoi_nhan.configure(text="") 

        e_d.bind("<KeyRelease>", kiem_tra_ten)
        # ---------------------------------------------

        e_t = self.create_form_entry(card, "Số tiền chuyển (VNĐ)")
        e_nd = self.create_form_entry(card, "Nội dung chuyển khoản")
        
        def submit():
            tk_nguon = cb_tk_nguon.get().split(" ")[0] if role == 'khachhang' else e_n.get()
            success, msg = self.db.chuyen_khoan(tk_nguon, e_d.get(), e_t.get(), e_nd.get())
            messagebox.showinfo("Kết quả", msg) if success else messagebox.showerror("Lỗi", msg)
            if success and role == 'khachhang': self.ui_chuyen_khoan() 
            
        ctk.CTkButton(master=card, text="Thực Hiện Chuyển", width=350, height=45, font=("Arial", 14, "bold"), fg_color=M_BLUE_CHINH, hover_color=M_BLUE_HOVER, corner_radius=10, command=submit).pack(pady=30)

    def ui_quan_ly_the(self):
        role = self.db.current_user['vai_tro']
        card = self.create_card_frame("")
        tabview = ctk.CTkTabview(master=card, fg_color="transparent", segmented_button_selected_color=M_BLUE_CHINH, segmented_button_selected_hover_color=M_BLUE_HOVER)
        tabview.pack(fill="both", expand=True, padx=20, pady=10)
        tab1 = tabview.add("Danh Sách Thẻ")
        tab2 = tabview.add("Phát Hành Thẻ Mới")

        cols = ("Số Thẻ", "Số TK Nối", "Chủ Thẻ", "Loại Thẻ", "Hết Hạn", "Trạng Thái")
        widths = (120, 100, 150, 100, 100, 100)
        tree_the = self.tao_bang(tab1, cols, widths)

        def load_the():
            for i in tree_the.get_children(): tree_the.delete(i)
            danh_sach = self.db.lay_ds_the(self.db.current_user['ma'] if role == 'khachhang' else None)
            for r in danh_sach: tree_the.insert("", "end", values=r)
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

        ctk.CTkButton(frame_btn, text="Khóa Thẻ", width=120, fg_color="#FFA756", hover_color="#FF8C00", corner_radius=8, command=lambda: thao_tac_the('khoa')).pack(side="left", padx=10)
        ctk.CTkButton(frame_btn, text="Mở Khóa", width=120, fg_color="#16DBCC", hover_color="#12B3A6", corner_radius=8, command=lambda: thao_tac_the('mo_khoa')).pack(side="left", padx=10)
        
        if role != 'khachhang':
            ctk.CTkButton(frame_btn, text="Hủy Thẻ", width=120, fg_color="#FF4B4A", hover_color="#E03A3A", corner_radius=8, command=lambda: thao_tac_the('xoa')).pack(side="left", padx=10)

        if role == 'khachhang':
            ds_tk = self.db.lay_ds_tk_cua_khach(self.db.current_user['ma'])
            ds_tk_cb = [t[0] for t in ds_tk] if ds_tk else ["Chưa có TK"]
            ctk.CTkLabel(master=tab2, text="Liên kết với Số tài khoản:", text_color=M_TEXT_GREY).pack()
            cb_sotk = ctk.CTkComboBox(tab2, values=ds_tk_cb, width=350, height=45, button_color=M_BLUE_CHINH)
            cb_sotk.pack(pady=5)
        else:
            cb_sotk = self.create_form_entry(tab2, "Số Tài Khoản liên kết")
            
        loai_the_db = self.db.lay_ds_loai_the()
        ds_loai = [f"{r[0]} - {r[1]} (Đầu số: {r[2]})" for r in loai_the_db] if loai_the_db else ["Trống"]
        ctk.CTkLabel(master=tab2, text="Chọn Loại thẻ:", text_color=M_TEXT_GREY).pack()
        cb_loai = ctk.CTkComboBox(tab2, values=ds_loai, width=350, height=45, font=("Arial", 14), button_color=M_BLUE_CHINH)
        cb_loai.pack(pady=5)
        
        e_pin = self.create_form_entry(tab2, "Nhập mã PIN (6 số)")

        def tao_the():
            ma_loai = cb_loai.get().split(" - ")[0]
            so_tk = cb_sotk.get() if role == 'khachhang' else cb_sotk.get()
            ma_kh = self.db.current_user['ma'] if role == 'khachhang' else None
            
            s, m = self.db.tao_the_tu_dong(so_tk, ma_loai, e_pin.get(), ma_kh)
            if s:
                messagebox.showinfo("Thành công", m)
                load_the()
            else: messagebox.showerror("Lỗi", m)

        ctk.CTkButton(tab2, text="Xác Nhận Phát Hành", width=350, height=45, font=("Arial", 14, "bold"), fg_color=M_BLUE_CHINH, hover_color=M_BLUE_HOVER, corner_radius=10, command=tao_the).pack(pady=20)

    def ui_sao_ke(self):
        role = self.db.current_user['vai_tro']
        card = self.create_card_frame("Lịch Sử Giao Dịch")
        frame_top = ctk.CTkFrame(master=card, fg_color="transparent")
        frame_top.pack(fill="x", pady=10, padx=20)
        
        if role != 'khachhang':
            e_tk = ctk.CTkEntry(master=frame_top, placeholder_text="Nhập Số tài khoản để tra cứu...", width=400, height=40, font=("Arial", 14), fg_color=M_BG_APP, text_color=M_TEXT_DARK, border_width=0, corner_radius=10)
            e_tk.pack(side="left", padx=(0, 10))
        else:
            ctk.CTkLabel(master=frame_top, text="Dưới đây là toàn bộ lịch sử giao dịch của bạn:", font=("Arial", 14, "italic"), text_color=M_TEXT_GREY).pack(side="left")

        cols = ("Mã GD", "Loại", "Số tiền", "Thời gian", "Nguồn", "Đích", "Nội dung")
        widths = (50, 100, 120, 160, 100, 100, 200)
        tree = self.tao_bang(card, cols, widths)

        def load_sao_ke():
            for i in tree.get_children(): tree.delete(i)
            if role == 'khachhang':
                rows = self.db.sao_ke_giao_dich(ma_kh=self.db.current_user['ma'])
            else:
                rows = self.db.sao_ke_giao_dich(so_tk=e_tk.get())
                
            for row in rows:
                r = list(row)
                r[2] = f"{r[2]:,.0f} đ"
                
                # BIẾN ĐỔI NONE THÀNH "NGÂN HÀNG" KHI IN RA BẢNG GIAO DIỆN
                if r[4] is None: r[4] = "Ngân hàng"
                if r[5] is None: r[5] = "Ngân hàng"
                
                tree.insert("", "end", values=r)

        if role != 'khachhang':
            ctk.CTkButton(master=frame_top, text="Tra Cứu", width=120, height=40, font=("Arial", 14, "bold"), fg_color=M_BLUE_CHINH, corner_radius=10, command=load_sao_ke).pack(side="left")
        else:
            load_sao_ke() 

    def ui_quan_ly_khach_hang(self):
        card = self.create_card_frame("Tổng Hợp Tài Khoản Khách Hàng")
        cols = ("Mã KH", "Họ Tên", "CMND", "Số TK", "Số Dư", "Trạng Thái")
        widths = (80, 150, 100, 100, 120, 100)
        tree = self.tao_bang(card, cols, widths)

        for row in self.db.lay_ds_khach_hang():
            r = list(row)
            if r[4] is not None: r[4] = f"{r[4]:,.0f} đ"
            else: r[4] = "Chưa có TK"
            tree.insert("", "end", values=r)

    def ui_nhan_su(self):
        card = self.create_card_frame("")
        tabview = ctk.CTkTabview(master=card, fg_color="transparent", segmented_button_selected_color=M_BLUE_CHINH, segmented_button_selected_hover_color=M_BLUE_HOVER)
        tabview.pack(fill="both", expand=True, padx=20, pady=5)
        tab1 = tabview.add("Danh Sách")
        tab2 = tabview.add("Thêm Mới")
        if self.db.current_user['vai_tro'] == 'admin':
            tab3 = tabview.add("Phân Quyền / Chức Vụ")

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
            if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa nhân viên {ma_nv}?"):
                s, m = self.db.xoa_nhan_vien(ma_nv, self.db.current_user['vai_tro'])
                if s:
                    messagebox.showinfo("Thành công", m)
                    load_ds_nhansu()
                else: messagebox.showerror("Lỗi", m)

        ctk.CTkButton(tab1, text="Xóa Nhân Viên Đã Chọn", fg_color="#FF4B4A", hover_color="#E03A3A", corner_radius=10, command=xoa_nv).pack(pady=10)

        e_ma = self.create_form_entry(tab2, "Mã NV (VD: NV03)")
        e_ten = self.create_form_entry(tab2, "Họ Tên Nhân Viên")
        e_usr = self.create_form_entry(tab2, "Tên đăng nhập")
        e_pwd = self.create_form_entry(tab2, "Mật khẩu")
        e_luong = self.create_form_entry(tab2, "Lương cơ bản (VND)")
        
        roles_allowed = ["nhanvien"] if self.db.current_user['vai_tro'] == 'quanly' else ["nhanvien", "quanly", "admin"]
        cb_role = ctk.CTkComboBox(tab2, values=roles_allowed, width=350, height=45, font=("Arial", 14), button_color=M_BLUE_CHINH)
        cb_role.pack(pady=10)

        def tao_tk():
            s, m = self.db.tao_nhan_vien(e_ma.get(), e_ten.get(), e_usr.get(), e_pwd.get(), cb_role.get(), e_luong.get())
            if s: 
                messagebox.showinfo("Thành công", m)
                load_ds_nhansu() 
            else: messagebox.showerror("Lỗi", m)
            
        ctk.CTkButton(tab2, text="Lưu Hồ Sơ", width=350, height=45, font=("Arial", 14, "bold"), fg_color=M_BLUE_CHINH, corner_radius=10, command=tao_tk).pack(pady=20)

        if self.db.current_user['vai_tro'] == 'admin':
            e_matc = self.create_form_entry(tab3, "Nhập Mã NV cần điều chỉnh")
            cb_role_moi = ctk.CTkComboBox(tab3, values=["nhanvien", "quanly", "admin"], width=350, height=45, button_color=M_BLUE_CHINH)
            cb_role_moi.pack(pady=10)
            def luu_chuc_vu():
                s, m = self.db.dieu_chinh_chuc_vu(e_matc.get(), cb_role_moi.get())
                if s: 
                    messagebox.showinfo("Thành công", m)
                    load_ds_nhansu()
                else: messagebox.showerror("Lỗi", m)
            ctk.CTkButton(tab3, text="Cập Nhật Chức Vụ", width=350, height=45, font=("Arial", 14, "bold"), fg_color=M_BLUE_CHINH, corner_radius=10, command=luu_chuc_vu).pack(pady=20)

# ================= VẬN HÀNH ================= #
if __name__ == "__main__":
    app = BankingApp()
    app.mainloop()
