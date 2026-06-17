import customtkinter as ctk
from tkinter import messagebox, ttk
from database import BankingSystem
import random
import threading
from ai_helper import AIHelper

ctk.set_appearance_mode("Light")

M_BLUE_CHINH = "#2D60FF"       
M_BLUE_HOVER = "#1E4DB7"       
M_BG_APP = "#F5F7FA"           
M_BG_SIDEBAR = "#FFFFFF"       
M_TEXT_DARK = "#343C6A"        
M_TEXT_GREY = "#B1B1B1"        
M_TRANG = "#FFFFFF"
M_RED = "#FF4B4B"
M_RED_HOVER = "#FF3333"

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
        frame = ctk.CTkFrame(master=self, width=500, height=600, fg_color=M_TRANG, border_width=0, corner_radius=25)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(master=frame, text="💳 Bankdash.", font=("Helvetica", 24, "bold"), text_color=M_BLUE_CHINH).pack(pady=(30,5))
        ctk.CTkLabel(master=frame, text="Mở tài khoản Internet Banking", font=("Arial", 14), text_color=M_TEXT_GREY).pack(pady=(0,20))
        
        # ĐÃ XÓA Ô NHẬP MÃ KH Ở ĐÂY
        e_hoten = self.create_form_entry(frame, "Họ và Tên")
        e_cmnd = self.create_form_entry(frame, "CMND / CCCD")
        e_ns = self.create_form_entry(frame, "Ngày sinh (YYYY-MM-DD)")
        e_username = self.create_form_entry(frame, "Tên đăng nhập App")
        e_password = self.create_form_entry(frame, "Mật khẩu", is_password=True)

        def submit_reg():
            # Chỉ truyền 5 tham số thay vì 6
            s, m = self.db.dang_ky_khach_hang(e_hoten.get(), e_cmnd.get(), e_ns.get(), e_username.get(), e_password.get())
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
            self.create_menu_btn(sidebar, "💰", "Sổ Tiết Kiệm", self.ui_so_tiet_kiem)
            self.create_menu_btn(sidebar, "🤖", "Trợ Lý AI", self.ui_tro_ly_ai)
        else:
            self.create_menu_btn(sidebar, "🏠", "Tổng Quan", self.ui_sao_ke)
            self.create_menu_btn(sidebar, "📥", "Nạp Tiền (Quầy)", self.ui_nap_tien)
            self.create_menu_btn(sidebar, "💸", "Chuyển Khoản", self.ui_chuyen_khoan)
            self.create_menu_btn(sidebar, "💳", "Quản Lý Thẻ", self.ui_quan_ly_the)
            self.create_menu_btn(sidebar, "🤖", "Trợ Lý AI", self.ui_tro_ly_ai)
            
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
                ten, loai = self.db.lay_ten_tu_tk_hoac_the(so_nhan)
                if ten:
                    icon = "💳" if loai == "Thẻ" else "🏦"
                    lbl_ten.configure(text=f"{icon} {loai} nhận: {ten}", text_color="#16DBCC")
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
        
        # CHỌN NGUỒN TIỀN (BAO GỒM CẢ TÀI KHOẢN VÀ THẺ)
        if role == 'khachhang':
            ds_tk, ds_the = self.db.lay_ds_nguon_tien_cua_khach(self.db.current_user['ma'])
            ds_nguon_cb = []
            for t in ds_tk: 
                if t[1] is not None:
                    ds_nguon_cb.append(f"TK: {t[0]} (Số dư: {t[1]:,.0f}đ)")
            for t in ds_the: 
                if t[1] is not None:
                    ds_nguon_cb.append(f"Thẻ: {t[0]} (Số dư: {t[1]:,.0f}đ)")
            if not ds_nguon_cb: 
                ds_nguon_cb = ["Bạn chưa có nguồn tiền nào"]
            
            ctk.CTkLabel(master=card, text="Trích tiền từ nguồn:", font=("Arial", 12), text_color=M_TEXT_GREY).pack()
            cb_tk_nguon = ctk.CTkComboBox(card, values=ds_nguon_cb, width=350, height=45, button_color=M_BLUE_CHINH)
            cb_tk_nguon.pack(pady=5)
            cb_tk_nguon.set(ds_nguon_cb[0] if ds_nguon_cb else "")
        else:
            e_n = self.create_form_entry(card, "Số TK hoặc Số Thẻ Nguồn (Trích tiền)")

        # THÔNG TIN ĐÍCH NHẬN VÀ TỰ ĐỘNG HIỆN TÊN (NÂNG CẤP TÌM CẢ THẺ)
        e_d = self.create_form_entry(card, "Số TK hoặc Số Thẻ Đích (Nhận tiền)")
        lbl_ten_nguoi_nhan = ctk.CTkLabel(master=card, text="", font=("Arial", 14, "bold"))
        lbl_ten_nguoi_nhan.pack(pady=(0, 10))

        def kiem_tra_ten(event):
            so_nhan = e_d.get().strip() 
            if len(so_nhan) >= 8: 
                ten, loai = self.db.lay_ten_tu_tk_hoac_the(so_nhan) # Gọi hàm tìm chung cả TK và Thẻ
                if ten: 
                    icon = "💳" if loai == "Thẻ" else "🏦"
                    lbl_ten_nguoi_nhan.configure(text=f"{icon} {loai} nhận: {ten}", text_color="#16DBCC") 
                else: 
                    lbl_ten_nguoi_nhan.configure(text="⚠️ Không tìm thấy người nhận!", text_color="#FF4B4A") 
            else: 
                lbl_ten_nguoi_nhan.configure(text="") 
        e_d.bind("<KeyRelease>", kiem_tra_ten)

        e_t = self.create_form_entry(card, "Số tiền chuyển (VNĐ)")
        e_nd = self.create_form_entry(card, "Nội dung chuyển khoản")
        
        def submit():
            if role == 'khachhang':
                chuoi_nguon = cb_tk_nguon.get()
                if "chưa có" in chuoi_nguon: return messagebox.showerror("Lỗi", "Bạn không có nguồn tiền hợp lệ!")
                tk_nguon = chuoi_nguon.split(" ")[1] # Lấy chuỗi số đằng sau chữ "TK:" hoặc "Thẻ:"
            else:
                tk_nguon = e_n.get()
                
            success, msg = self.db.chuyen_khoan(tk_nguon, e_d.get(), e_t.get(), e_nd.get())
            messagebox.showinfo("Kết quả", msg) if success else messagebox.showerror("Lỗi", msg)
            if success and role == 'khachhang': self.ui_chuyen_khoan() # Reload giao diện để update số dư
            
        ctk.CTkButton(master=card, text="Thực Hiện Chuyển", width=350, height=45, font=("Arial", 14, "bold"), fg_color=M_BLUE_CHINH, hover_color=M_BLUE_HOVER, corner_radius=10, command=submit).pack(pady=30)
    def ui_quan_ly_the(self):
        role = self.db.current_user['vai_tro']
        card = self.create_card_frame("")
        tabview = ctk.CTkTabview(master=card, fg_color="transparent", segmented_button_selected_color=M_BLUE_CHINH, segmented_button_selected_hover_color=M_BLUE_HOVER)
        tabview.pack(fill="both", expand=True, padx=20, pady=10)
        tab1 = tabview.add("Danh Sách Thẻ")
        tab2 = tabview.add("Phát Hành Thẻ Mới")

        # THÊM CỘT SỐ DƯ THẺ
        cols = ("Số Thẻ", "Số TK Nối", "Chủ Thẻ", "Loại Thẻ", "Số Dư Thẻ", "Hết Hạn", "Trạng Thái")
        widths = (130, 90, 130, 90, 110, 90, 90)
        tree_the = self.tao_bang(tab1, cols, widths)

        def load_the():
            for i in tree_the.get_children(): tree_the.delete(i)
            danh_sach = self.db.lay_ds_the(self.db.current_user['ma'] if role == 'khachhang' else None)
            for r in danh_sach: 
                r_list = list(r)
                r_list[4] = f"{r_list[4]:,.0f} đ" # Định dạng tiền
                tree_the.insert("", "end", values=r_list)
        load_the()

        frame_btn = ctk.CTkFrame(master=tab1, fg_color="transparent")
        frame_btn.pack(pady=10)
        
        def thao_tac_the(action):
            selected = tree_the.selection()
            if not selected: return messagebox.showwarning("Cảnh báo", "Vui lòng chọn 1 thẻ (chỗ bôi xanh)!")
            so_the = tree_the.item(selected[0])['values'][0]
            if messagebox.askyesno("Xác nhận", f"Thực hiện thao tác trên thẻ {so_the}?"):
                s, m = self.db.doi_trang_thai_the(so_the, action)
                if s: 
                    messagebox.showinfo("Thành công", m)
                    load_the()
                else: messagebox.showerror("Lỗi", m)

        def copy_so_the():
            selected = tree_the.selection()
            if not selected: return messagebox.showwarning("Cảnh báo", "Vui lòng click chọn dòng thẻ cần Copy!")
            so_the = tree_the.item(selected[0])['values'][0]
            self.clipboard_clear() 
            self.clipboard_append(str(so_the)) 
            self.update() 
            messagebox.showinfo("Thành công", f"Đã lưu Số thẻ vào bộ nhớ tạm:\n{so_the}")

        def copy_so_tk():
            selected = tree_the.selection()
            if not selected: return messagebox.showwarning("Cảnh báo", "Vui lòng click chọn dòng thẻ cần Copy!")
            so_tk = tree_the.item(selected[0])['values'][1]
            if so_tk == "None" or not so_tk: return messagebox.showwarning("Cảnh báo", "Thẻ này không có số tài khoản liên kết!")
            self.clipboard_clear() 
            self.clipboard_append(str(so_tk)) 
            self.update() 
            messagebox.showinfo("Thành công", f"Đã lưu Số tài khoản vào bộ nhớ tạm:\n{so_tk}")

        ctk.CTkButton(frame_btn, text="📋 Copy Số Thẻ", width=110, fg_color=M_BLUE_CHINH, hover_color=M_BLUE_HOVER, corner_radius=8, command=copy_so_the).pack(side="left", padx=10)
        ctk.CTkButton(frame_btn, text="📋 Copy Số TK", width=110, fg_color="#16DBCC", hover_color="#12B3A6", corner_radius=8, command=copy_so_tk).pack(side="left", padx=10)
        ctk.CTkButton(frame_btn, text="Khóa Thẻ", width=100, fg_color="#FFA756", hover_color="#FF8C00", corner_radius=8, command=lambda: thao_tac_the('khoa')).pack(side="left", padx=10)
        ctk.CTkButton(frame_btn, text="Mở Khóa", width=100, fg_color="#16DBCC", hover_color="#12B3A6", corner_radius=8, command=lambda: thao_tac_the('mo_khoa')).pack(side="left", padx=10)
        
        if role != 'khachhang':
            ctk.CTkButton(frame_btn, text="Hủy Thẻ", width=100, fg_color="#FF4B4A", hover_color="#E03A3A", corner_radius=8, command=lambda: thao_tac_the('xoa')).pack(side="left", padx=10)

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
        card = self.create_card_frame("Tra Cứu Lịch Sử Giao Dịch")
        
        # --- 1. KHU VỰC BỘ LỌC (FILTER) ---
        filter_frame = ctk.CTkFrame(master=card, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=10)

        # Hàng 1: Lọc Số TK và Số thẻ
        row1 = ctk.CTkFrame(master=filter_frame, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        
        if role != 'khachhang':
            e_tk = ctk.CTkEntry(master=row1, placeholder_text="Nhập Số tài khoản...", width=200, height=40, font=("Arial", 13), border_color="#E6EFF5")
            e_tk.pack(side="left", padx=5)
            e_the = ctk.CTkEntry(master=row1, placeholder_text="Nhập Số thẻ ATM...", width=200, height=40, font=("Arial", 13), border_color="#E6EFF5")
            e_the.pack(side="left", padx=5)
        else:
            ctk.CTkLabel(master=row1, text="Dưới đây là toàn bộ lịch sử giao dịch cá nhân của bạn:", font=("Arial", 14, "italic"), text_color=M_TEXT_GREY).pack(side="left", padx=5)

        # Hàng 2: Lọc Thời gian
        row2 = ctk.CTkFrame(master=filter_frame, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        
        ctk.CTkLabel(master=row2, text="Từ ngày:", font=("Arial", 13, "bold"), text_color=M_TEXT_DARK).pack(side="left", padx=5)
        e_tu = ctk.CTkEntry(master=row2, placeholder_text="YYYY-MM-DD", width=120, height=40, border_color="#E6EFF5")
        e_tu.pack(side="left", padx=5)
        
        ctk.CTkLabel(master=row2, text="Đến ngày:", font=("Arial", 13, "bold"), text_color=M_TEXT_DARK).pack(side="left", padx=5)
        e_den = ctk.CTkEntry(master=row2, placeholder_text="YYYY-MM-DD", width=120, height=40, border_color="#E6EFF5")
        e_den.pack(side="left", padx=5)

        # --- 2. BẢNG DỮ LIỆU ---
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
            ctk.CTkButton(master=row2, text="Tra Cứu", width=120, height=40, font=("Arial", 14, "bold"), fg_color=M_BLUE_CHINH, corner_radius=10, command=load_sao_ke).pack(side="left")
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

        frame_btn = ctk.CTkFrame(master=card, fg_color="transparent")
        frame_btn.pack(pady=10)

        def copy_so_tk():
            selected = tree.selection()
            if not selected: return messagebox.showwarning("Cảnh báo", "Vui lòng click chọn khách hàng cần Copy!")
            so_tk = tree.item(selected[0])['values'][3]
            if so_tk == "None" or not so_tk: return messagebox.showwarning("Cảnh báo", "Khách hàng này chưa có số tài khoản!")
            self.clipboard_clear() 
            self.clipboard_append(str(so_tk)) 
            self.update() 
            messagebox.showinfo("Thành công", f"Đã lưu Số tài khoản vào bộ nhớ tạm:\n{so_tk}")

        ctk.CTkButton(frame_btn, text="📋 Copy Số TK", width=110, fg_color=M_BLUE_CHINH, hover_color=M_BLUE_HOVER, corner_radius=8, command=copy_so_tk).pack(side="left", padx=10)

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

    # --- TRỢ LÝ AI ---
    def ui_so_tiet_kiem(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        self.lbl_page_title.configure(text="Sổ Tiết Kiệm")

        tabview = ctk.CTkTabview(master=self.main_frame, fg_color="transparent", segmented_button_selected_color=M_BLUE_CHINH, segmented_button_selected_hover_color=M_BLUE_HOVER)
        tabview.pack(fill="both", expand=True, padx=20, pady=10)
        tab1 = tabview.add("Sổ Đang Gửi")
        tab2 = tabview.add("Mở Sổ Mới")

        # Tab 1: Sổ Đang Gửi
        cols = ("Mã Sổ", "Tài Khoản", "Số Tiền Gửi", "Kỳ Hạn", "Lãi Suất", "Ngày Gửi", "Đáo Hạn", "Trạng Thái")
        widths = (50, 90, 110, 50, 60, 90, 90, 90)
        tree_stk = self.tao_bang(tab1, cols, widths)

        def load_stk():
            for i in tree_stk.get_children(): tree_stk.delete(i)
            ds = self.db.lay_danh_sach_so_tiet_kiem(self.db.current_user['ma'])
            for r in ds:
                r_list = list(r)
                r_list[2] = f"{r_list[2]:,.0f} đ" # Số tiền
                r_list[3] = f"{r_list[3]} tháng"
                r_list[4] = f"{r_list[4]}%"
                tree_stk.insert("", "end", values=r_list)
        load_stk()

        frame_btn = ctk.CTkFrame(master=tab1, fg_color="transparent")
        frame_btn.pack(pady=10)

        def xu_ly_tat_toan():
            selected = tree_stk.selection()
            if not selected: return messagebox.showwarning("Cảnh báo", "Vui lòng chọn 1 sổ tiết kiệm cần tất toán!")
            values = tree_stk.item(selected[0])['values']
            ma_so = values[0]
            trang_thai = values[7]
            if trang_thai == "Da tat toan":
                return messagebox.showwarning("Cảnh báo", "Sổ này đã được tất toán từ trước!")
            if messagebox.askyesno("Xác nhận", f"Bạn có chắc chắn muốn tất toán sổ tiết kiệm mã {ma_so}?\\n(Tất toán trước hạn sẽ chỉ được hưởng lãi suất không kỳ hạn 0.1%/năm)"):
                success, msg = self.db.tat_toan_so_tiet_kiem(ma_so)
                if success:
                    messagebox.showinfo("Thành công", msg)
                    load_stk()
                else:
                    messagebox.showerror("Lỗi", msg)

        ctk.CTkButton(master=frame_btn, text="Tất toán sổ này", font=("Arial", 14, "bold"), fg_color=M_RED, hover_color=M_RED_HOVER, command=xu_ly_tat_toan).pack(side="left", padx=10)

        # Tab 2: Mở sổ mới
        form = ctk.CTkFrame(master=tab2, fg_color=M_TRANG, corner_radius=15, width=400)
        form.pack(pady=30, padx=50, expand=True, fill="both")
        
        # Lấy danh sách nguồn tiền
        ds_tk, ds_the = self.db.lay_ds_nguon_tien_cua_khach(self.db.current_user['ma'])
        tk_list = [f"{t[0]} - Dư: {t[1]:,.0f} đ" for t in ds_tk]
        
        if not tk_list:
            ctk.CTkLabel(master=form, text="Bạn không có tài khoản nào để trích tiền!", font=("Arial", 14), text_color=M_RED).pack(pady=50)
        else:
            ctk.CTkLabel(master=form, text="Tài Khoản Trích Tiền:", font=("Arial", 14, "bold"), text_color=M_TEXT_DARK).pack(pady=(30,5), anchor="w", padx=30)
            cbo_nguon = ctk.CTkOptionMenu(master=form, values=tk_list, width=300, fg_color=M_BG_APP, text_color=M_TEXT_DARK)
            cbo_nguon.pack(pady=5, padx=30, anchor="w")

            ctk.CTkLabel(master=form, text="Kỳ Hạn (Tháng):", font=("Arial", 14, "bold"), text_color=M_TEXT_DARK).pack(pady=(15,5), anchor="w", padx=30)
            ky_han_values = ["1 tháng (Lãi 4.5%/năm)", "3 tháng (Lãi 5.0%/năm)", "6 tháng (Lãi 6.0%/năm)", "12 tháng (Lãi 7.0%/năm)", "24 tháng (Lãi 7.5%/năm)"]
            cbo_ky_han = ctk.CTkOptionMenu(master=form, values=ky_han_values, width=300, fg_color=M_BG_APP, text_color=M_TEXT_DARK)
            cbo_ky_han.pack(pady=5, padx=30, anchor="w")

            ctk.CTkLabel(master=form, text="Số Tiền Gửi (VNĐ):", font=("Arial", 14, "bold"), text_color=M_TEXT_DARK).pack(pady=(15,5), anchor="w", padx=30)
            txt_so_tien = ctk.CTkEntry(master=form, width=300, placeholder_text="Tối thiểu 1,000,000 đ")
            txt_so_tien.pack(pady=5, padx=30, anchor="w")

            def xac_nhan_mo_so():
                so_tk = cbo_nguon.get().split(" - ")[0]
                ky_han_str = cbo_ky_han.get()
                ky_han = int(ky_han_str.split(" ")[0])
                tien_str = txt_so_tien.get().strip()
                if not tien_str.isdigit():
                    return messagebox.showerror("Lỗi", "Số tiền gửi phải là số nguyên hợp lệ!")
                so_tien = int(tien_str)
                if so_tien < 1000000:
                    return messagebox.showerror("Lỗi", "Số tiền gửi tối thiểu là 1,000,000 VNĐ!")
                
                if messagebox.askyesno("Xác nhận", f"Xác nhận trích {so_tien:,.0f}đ từ tài khoản {so_tk} để mở sổ tiết kiệm {ky_han} tháng?"):
                    success, msg = self.db.mo_so_tiet_kiem(so_tk, so_tien, ky_han)
                    if success:
                        messagebox.showinfo("Thành công", msg)
                        txt_so_tien.delete(0, 'end')
                        load_stk()
                        tabview.set("Sổ Đang Gửi")
                    else:
                        messagebox.showerror("Lỗi", msg)

            ctk.CTkButton(master=form, text="Mở Sổ Tiết Kiệm", font=("Arial", 14, "bold"), fg_color=M_BLUE_CHINH, hover_color=M_BLUE_HOVER, width=200, command=xac_nhan_mo_so).pack(pady=40)

    def ui_tro_ly_ai(self):
        for widget in self.main_frame.winfo_children(): widget.destroy()
        self.lbl_page_title.configure(text="Trợ Lý AI (Beta)")

        # Khung cài đặt API Key
        frame_top = ctk.CTkFrame(master=self.main_frame, fg_color=M_TRANG, corner_radius=15)
        frame_top.pack(fill="x", padx=30, pady=(0, 20))
        
        ctk.CTkLabel(master=frame_top, text="API Key Gemini:", font=("Arial", 14)).pack(side="left", padx=(20, 10), pady=15)
        self.entry_api_key = ctk.CTkEntry(master=frame_top, width=300, show="*")
        self.entry_api_key.pack(side="left", padx=10)
        
        # Giữ lại key nếu đã nhập trước đó (lưu trên class)
        if hasattr(self, 'ai_key_saved'):
            self.entry_api_key.insert(0, self.ai_key_saved)

        # Khung Chat
        frame_chat = ctk.CTkFrame(master=self.main_frame, fg_color=M_TRANG, corner_radius=15)
        frame_chat.pack(fill="both", expand=True, padx=30, pady=(0, 30))

        self.txt_chat_history = ctk.CTkTextbox(master=frame_chat, font=("Arial", 14), wrap="word", state="disabled", fg_color="transparent", text_color=M_TEXT_DARK)
        self.txt_chat_history.pack(fill="both", expand=True, padx=20, pady=20)
        
        frame_input = ctk.CTkFrame(master=frame_chat, fg_color="transparent")
        frame_input.pack(fill="x", padx=20, pady=(0, 20))
        
        self.entry_chat = ctk.CTkEntry(master=frame_input, height=40, font=("Arial", 14), placeholder_text="Hỏi AI về tình hình tài chính của bạn...")
        self.entry_chat.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_chat.bind("<Return>", lambda e: self.send_ai_message())
        
        self.btn_send_ai = ctk.CTkButton(master=frame_input, text="Gửi", width=80, height=40, font=("Arial", 14, "bold"), fg_color=M_BLUE_CHINH, hover_color=M_BLUE_HOVER, command=self.send_ai_message)
        self.btn_send_ai.pack(side="right")
        
        self.append_chat("🤖 AI", "Xin chào! Tôi là trợ lý tài chính ảo của bạn. Bạn muốn tôi giúp gì hôm nay?\n(Vui lòng lấy API Key từ Google AI Studio và dán vào ô bên trên để bắt đầu nhé)")

    def append_chat(self, sender, message):
        self.txt_chat_history.configure(state="normal")
        self.txt_chat_history.insert("end", f"{sender}: {message}\n\n")
        self.txt_chat_history.see("end")
        self.txt_chat_history.configure(state="disabled")

    def append_chunk(self, text):
        self.txt_chat_history.configure(state="normal")
        self.txt_chat_history.insert("end", text)
        self.txt_chat_history.see("end")
        self.txt_chat_history.configure(state="disabled")

    def send_ai_message(self):
        user_msg = self.entry_chat.get().strip()
        api_key = self.entry_api_key.get().strip()
        
        if not user_msg: return
        if not api_key:
            messagebox.showwarning("Thiếu API Key", "Vui lòng nhập Google Gemini API Key để sử dụng tính năng này.")
            return

        self.ai_key_saved = api_key
        self.append_chat("👤 Bạn", user_msg)
        self.entry_chat.delete(0, 'end')
        self.btn_send_ai.configure(state="disabled", text="Đang nghĩ...")
        
        threading.Thread(target=self.process_ai_response, args=(api_key, user_msg), daemon=True).start()

    def process_ai_response(self, api_key, user_msg):
        try:
            # Chỉ khởi tạo AIHelper một lần nếu dùng chung 1 key, giúp chat siêu nhanh
            if not hasattr(self, 'ai_instance') or getattr(self, 'last_api_key', None) != api_key:
                self.ai_instance = AIHelper(api_key)
                self.last_api_key = api_key
                
            context_data = self.db.lay_du_lieu_cho_ai(self.db.current_user['ma'])
            
            self.txt_chat_history.after(0, lambda: self.append_chunk("🤖 AI: "))
            
            for chunk in self.ai_instance.get_response_stream(user_msg, context_data):
                self.txt_chat_history.after(0, lambda t=chunk: self.append_chunk(t))
                
            self.txt_chat_history.after(0, lambda: self.append_chunk("\n\n"))
        except Exception as e:
            response = "Lỗi kết nối hoặc API Key không hợp lệ."
            self.txt_chat_history.after(0, lambda: self.append_chat("🤖 AI", response))
            
        self.btn_send_ai.after(0, lambda: self.btn_send_ai.configure(state="normal", text="Gửi"))

# ================= VẬN HÀNH ================= #
