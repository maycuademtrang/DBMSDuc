import psycopg2
import random
from datetime import datetime, timedelta

# ========================================================== #
# PHẦN 1: LỚP XỬ LÝ DATABASE 
# ========================================================== #
class BankingSystem:
    def __init__(self):
        self.conn = self.get_db_connection()
        self.current_user = None
        self.setup_database_updates() # THÊM DÒNG NÀY VÀO ĐỂ KÍCH HOẠT


    def get_db_connection(self):
        try:
            return psycopg2.connect(dbname="nganhang", user="postgres", password="123456", host="localhost", port="5432")
        except Exception as e:
            return None

    def login(self, username, password):
        try:
            with self.conn.cursor() as cur:
                # 1. Kiểm tra tài khoản Nhân viên / Quản lý / Admin
                cur.execute("SELECT ma_nv, ho_ten, vai_tro FROM nhan_vien WHERE username = %s AND password = %s", (username, password))
                user = cur.fetchone()
                if user:
                    self.current_user = {'ma': user[0], 'ho_ten': user[1], 'vai_tro': user[2]}
                    return True
                
                # 2. Kiểm tra tài khoản Khách hàng
                cur.execute("SELECT ma_kh, ho_ten FROM khach_hang WHERE username = %s AND password = %s", (username, password))
                kh = cur.fetchone()
                if kh:
                    self.current_user = {'ma': kh[0], 'ho_ten': kh[1], 'vai_tro': 'khachhang'}
                    return True
                
                return False
        except Exception as e:
            # LỆNH QUAN TRỌNG NHẤT: Xóa bỏ trạng thái "đóng băng" của Database
            self.conn.rollback() 
            print("Lỗi hệ thống khi đăng nhập:", e)
            return False

    def dang_ky_khach_hang(self, ho_ten, cmnd, ngay_sinh, username, password):
        """Tạo khách hàng mới; DB tự sinh `ma_kh`. Trả về (True, message) hoặc (False, error)."""
        try:
            with self.conn.cursor() as cur:
                # Kiểm tra trùng CMND và username
                cur.execute("SELECT 1 FROM khach_hang WHERE cmnd = %s", (cmnd,))
                if cur.fetchone():
                    return False, "CMND/CCCD đã tồn tại trong hệ thống!"
                cur.execute("SELECT 1 FROM khach_hang WHERE username = %s UNION SELECT 1 FROM nhan_vien WHERE username = %s", (username, username))
                if cur.fetchone():
                    return False, "Tên đăng nhập đã có người sử dụng!"

                # Tạo mã khách hàng tự động tăng (VD: KH1, KH2...)
                cur.execute("SELECT ma_kh FROM khach_hang WHERE ma_kh LIKE 'KH%'")
                danh_sach_ma = cur.fetchall()
                max_id = 0
                for row in danh_sach_ma:
                    try:
                        num = int(row[0].replace('KH', ''))
                        if num > max_id: max_id = num
                    except: pass
                ma_kh_moi = f"KH{max_id + 1}"

                # Thêm khách hàng mới với mã vừa tạo
                cur.execute(
                    "INSERT INTO khach_hang (ma_kh, ho_ten, cmnd, ngay_sinh, username, password) VALUES (%s, %s, %s, %s, %s, %s)",
                    (ma_kh_moi, ho_ten, cmnd, ngay_sinh, username, password)
                )

                # Tạo số TK ngẫu nhiên (10 chữ số) và gán số dư khởi tạo
                while True:
                    so_tk = str(random.randint(1000000000, 9999999999))
                    cur.execute("SELECT 1 FROM tai_khoan WHERE so_tk = %s", (so_tk,))
                    if not cur.fetchone():
                        break

                cur.execute("INSERT INTO tai_khoan (so_tk, ma_kh, so_du) VALUES (%s, %s, 50000)", (so_tk, ma_kh_moi))
                self.conn.commit()
                return True, f"Đăng ký thành công!\n👤 Mã KH của bạn: {ma_kh_moi}\n💳 Số TK mặc định: {so_tk}\n💰 Số dư: 50,000đ"
        except Exception as e:
            self.conn.rollback()
            return False, f"Lỗi DB: {str(e)}"
        

    def setup_database_updates(self):
        """Tự động nâng cấp Database: Thêm trạng thái thẻ, Tài khoản KH, và Số dư Thẻ độc lập"""
        if self.conn:
            try:
                # Dùng SAVEPOINT để chạy tuần tự từng lệnh ALTER, tránh lỗi 1 câu làm sập cả cụm
                with self.conn.cursor() as cur:
                    queries = [
                        "ALTER TABLE the ADD COLUMN IF NOT EXISTS trang_thai VARCHAR(20) DEFAULT 'Hoat dong'",
                        "ALTER TABLE khach_hang ADD COLUMN IF NOT EXISTS username VARCHAR(50)",
                        "ALTER TABLE khach_hang ADD COLUMN IF NOT EXISTS password VARCHAR(255)",
                        "ALTER TABLE the ADD COLUMN IF NOT EXISTS so_du DECIMAL(15, 2) DEFAULT 0 CHECK (so_du >= 0)",
                        "ALTER TABLE loai_the ADD COLUMN IF NOT EXISTS dau_so VARCHAR(6) DEFAULT '970400'",
                        "DROP VIEW IF EXISTS vw_sao_ke_giao_dich CASCADE",
                        "ALTER TABLE giao_dich ALTER COLUMN tk_nguon TYPE VARCHAR(20)",
                        "ALTER TABLE giao_dich ALTER COLUMN tk_dich TYPE VARCHAR(20)",
                        "ALTER TABLE giao_dich DROP CONSTRAINT IF EXISTS giao_dich_tk_nguon_fkey",
                        "ALTER TABLE giao_dich DROP CONSTRAINT IF EXISTS giao_dich_tk_dich_fkey",
                        "CREATE OR REPLACE VIEW vw_sao_ke_giao_dich AS SELECT gd.ma_gd, gd.ngay_gd, gd.loai_gd, gd.tk_nguon, gd.tk_dich, gd.so_tien, gd.noi_dung FROM giao_dich gd ORDER BY gd.ngay_gd DESC"
                    ]
                    for q in queries:
                        try:
                            cur.execute("SAVEPOINT sp")
                            cur.execute(q)
                            cur.execute("RELEASE SAVEPOINT sp")
                        except Exception as e:
                            cur.execute("ROLLBACK TO SAVEPOINT sp")
                            
                    # Cập nhật Trigger tự động cho cả thẻ và TK
                    cur.execute("""
                        CREATE OR REPLACE FUNCTION fn_check_so_du()
                        RETURNS TRIGGER AS $$
                        BEGIN
                            IF NEW.loai_gd IN ('Rút tiền', 'Chuyển khoản') THEN
                                IF length(NEW.tk_nguon) <= 15 THEN
                                    IF NOT EXISTS (SELECT 1 FROM tai_khoan WHERE so_tk = NEW.tk_nguon AND (so_du - NEW.so_tien) >= 50000) THEN
                                        RAISE EXCEPTION 'Số dư tài khoản không đủ (cần duy trì tối thiểu 50.000đ)';
                                    END IF;
                                ELSE
                                    IF NOT EXISTS (SELECT 1 FROM the WHERE so_the = NEW.tk_nguon AND (so_du - NEW.so_tien) >= 0) THEN
                                        RAISE EXCEPTION 'Số dư thẻ không đủ để giao dịch';
                                    END IF;
                                END IF;
                            END IF;
                            RETURN NEW;
                        END;
                        $$ LANGUAGE plpgsql;
                    """)
                    cur.execute("""
                        CREATE OR REPLACE FUNCTION update_so_du_sau_giao_dich()
                        RETURNS TRIGGER AS $$
                        BEGIN
                            IF NEW.loai_gd IN ('Rút tiền', 'Chuyển khoản') AND NEW.tk_nguon IS NOT NULL THEN
                                IF length(NEW.tk_nguon) <= 15 THEN UPDATE tai_khoan SET so_du = so_du - NEW.so_tien WHERE so_tk = NEW.tk_nguon;
                                ELSE UPDATE the SET so_du = so_du - NEW.so_tien WHERE so_the = NEW.tk_nguon; END IF;
                            END IF;
                            IF NEW.loai_gd IN ('Nạp tiền', 'Chuyển khoản') AND NEW.tk_dich IS NOT NULL THEN
                                IF length(NEW.tk_dich) <= 15 THEN UPDATE tai_khoan SET so_du = so_du + NEW.so_tien WHERE so_tk = NEW.tk_dich;
                                ELSE UPDATE the SET so_du = so_du + NEW.so_tien WHERE so_the = NEW.tk_dich; END IF;
                            END IF;
                            RETURN NEW;
                        END;
                        $$ LANGUAGE plpgsql;
                    """)
                    cur.execute("""
                        CREATE OR REPLACE PROCEDURE sp_nap_tien(
                            p_so_nhan VARCHAR, 
                            p_so_tien DECIMAL, 
                            p_noi_dung TEXT
                        )
                        LANGUAGE plpgsql
                        AS $$
                        DECLARE
                            v_exists INT;
                        BEGIN
                            IF length(p_so_nhan) <= 15 THEN
                                SELECT 1 INTO v_exists FROM tai_khoan WHERE so_tk = p_so_nhan;
                            ELSE
                                SELECT 1 INTO v_exists FROM the WHERE so_the = p_so_nhan;
                            END IF;

                            IF v_exists IS NULL THEN
                                RAISE EXCEPTION 'Không tìm thấy số tài khoản hoặc số thẻ!';
                            END IF;

                            INSERT INTO giao_dich (tk_dich, loai_gd, so_tien, noi_dung)
                            VALUES (p_so_nhan, 'Nạp tiền', p_so_tien, p_noi_dung);

                            COMMIT;
                        END;
                        $$;
                    """)
                    cur.execute("""
                        CREATE OR REPLACE PROCEDURE sp_chuyen_khoan(
                            p_tk_nguon VARCHAR, 
                            p_tk_dich VARCHAR, 
                            p_so_tien DECIMAL, 
                            p_noi_dung TEXT,
                            p_ma_kh VARCHAR DEFAULT NULL
                        )
                        LANGUAGE plpgsql
                        AS $$
                        DECLARE
                            v_so_du DECIMAL;
                            v_chu_tk VARCHAR;
                            v_exists INT;
                        BEGIN
                            IF length(p_tk_nguon) <= 15 THEN
                                SELECT so_du, ma_kh INTO v_so_du, v_chu_tk FROM tai_khoan WHERE so_tk = p_tk_nguon;
                            ELSE
                                SELECT t.so_du, tk.ma_kh INTO v_so_du, v_chu_tk FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk WHERE t.so_the = p_tk_nguon;
                            END IF;

                            IF v_so_du IS NULL THEN
                                RAISE EXCEPTION 'Nguồn trích tiền (TK/Thẻ) không tồn tại!';
                            END IF;

                            IF p_ma_kh IS NOT NULL AND v_chu_tk != p_ma_kh THEN
                                RAISE EXCEPTION 'Chỉ được chuyển tiền từ tài sản của chính mình!';
                            END IF;

                            IF v_so_du < p_so_tien THEN
                                RAISE EXCEPTION 'Số dư trong Thẻ/Tài khoản không đủ!';
                            END IF;

                            IF length(p_tk_dich) <= 15 THEN
                                SELECT 1 INTO v_exists FROM tai_khoan WHERE so_tk = p_tk_dich;
                            ELSE
                                SELECT 1 INTO v_exists FROM the WHERE so_the = p_tk_dich;
                            END IF;

                            IF v_exists IS NULL THEN
                                RAISE EXCEPTION 'Đích nhận tiền không tồn tại!';
                            END IF;

                            INSERT INTO giao_dich (tk_nguon, tk_dich, loai_gd, so_tien, noi_dung)
                            VALUES (p_tk_nguon, p_tk_dich, 'Chuyển khoản', p_so_tien, p_noi_dung);

                            COMMIT;
                        END;
                        $$;
                    """)

                    cur.execute("""
                        CREATE OR REPLACE FUNCTION fn_tinh_tong_tai_san(p_ma_kh VARCHAR)
                        RETURNS DECIMAL AS $$
                        DECLARE
                            v_tong_tk DECIMAL := 0;
                            v_tong_the DECIMAL := 0;
                        BEGIN
                            SELECT COALESCE(SUM(so_du), 0) INTO v_tong_tk FROM tai_khoan WHERE ma_kh = p_ma_kh;
                            SELECT COALESCE(SUM(t.so_du), 0) INTO v_tong_the FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk WHERE tk.ma_kh = p_ma_kh;
                            RETURN v_tong_tk + v_tong_the;
                        END;
                        $$ LANGUAGE plpgsql;
                    """)
                    
                    cur.execute("""
                        CREATE OR REPLACE FUNCTION fn_tinh_phi_thuong_nien(p_ma_kh VARCHAR)
                        RETURNS DECIMAL AS $$
                        DECLARE v_tong_phi DECIMAL := 0;
                        BEGIN
                            SELECT COALESCE(SUM(l.phi_thuong_nien), 0) INTO v_tong_phi
                            FROM the t JOIN loai_the l ON t.ma_loai_the = l.ma_loai_the JOIN tai_khoan tk ON t.so_tk = tk.so_tk
                            WHERE tk.ma_kh = p_ma_kh AND t.trang_thai = 'Hoat dong';
                            RETURN v_tong_phi;
                        END;
                        $$ LANGUAGE plpgsql;
                    """)

                    cur.execute("""
                        CREATE OR REPLACE FUNCTION fn_thong_ke_gd_thang_nay(p_so_tk VARCHAR, p_loai_gd VARCHAR)
                        RETURNS DECIMAL AS $$
                        DECLARE v_tong_tien DECIMAL := 0;
                        BEGIN
                            SELECT COALESCE(SUM(so_tien), 0) INTO v_tong_tien
                            FROM giao_dich
                            WHERE loai_gd = p_loai_gd 
                              AND (tk_nguon = p_so_tk OR tk_dich = p_so_tk)
                              AND EXTRACT(MONTH FROM ngay_gd) = EXTRACT(MONTH FROM CURRENT_DATE)
                              AND EXTRACT(YEAR FROM ngay_gd) = EXTRACT(YEAR FROM CURRENT_DATE);
                            RETURN v_tong_tien;
                        END;
                        $$ LANGUAGE plpgsql;
                    """)

                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS so_tiet_kiem (
                            ma_so SERIAL PRIMARY KEY,
                            so_tk VARCHAR(15) NOT NULL REFERENCES tai_khoan(so_tk),
                            so_tien_gui DECIMAL(15, 2) NOT NULL CHECK (so_tien_gui >= 1000000), 
                            ky_han INT NOT NULL, 
                            lai_suat DECIMAL(5, 2) NOT NULL, 
                            ngay_gui DATE DEFAULT CURRENT_DATE,
                            ngay_dao_han DATE NOT NULL,
                            trang_thai VARCHAR(20) DEFAULT 'Dang gui'
                        );
                    """)
                    
                    cur.execute("""
                        CREATE OR REPLACE PROCEDURE sp_mo_so_tiet_kiem(p_so_tk VARCHAR, p_so_tien DECIMAL, p_ky_han INT)
                        LANGUAGE plpgsql
                        AS $$
                        DECLARE v_so_du DECIMAL; v_lai_suat DECIMAL; v_ngay_dao_han DATE;
                        BEGIN
                            SELECT so_du INTO v_so_du FROM tai_khoan WHERE so_tk = p_so_tk;
                            IF v_so_du < p_so_tien + 50000 THEN RAISE EXCEPTION 'Số dư không đủ để mở sổ tiết kiệm (cần dư tối thiểu 50.000đ sau khi gửi)!'; END IF;
                            CASE p_ky_han WHEN 1 THEN v_lai_suat := 4.5; WHEN 3 THEN v_lai_suat := 5.0; WHEN 6 THEN v_lai_suat := 6.0; WHEN 12 THEN v_lai_suat := 7.0; WHEN 24 THEN v_lai_suat := 7.5; ELSE RAISE EXCEPTION 'Kỳ hạn không hợp lệ!'; END CASE;
                            v_ngay_dao_han := CURRENT_DATE + (p_ky_han || ' months')::INTERVAL;
                            UPDATE tai_khoan SET so_du = so_du - p_so_tien WHERE so_tk = p_so_tk;
                            INSERT INTO so_tiet_kiem (so_tk, so_tien_gui, ky_han, lai_suat, ngay_dao_han) VALUES (p_so_tk, p_so_tien, p_ky_han, v_lai_suat, v_ngay_dao_han);
                            INSERT INTO giao_dich (tk_nguon, loai_gd, so_tien, noi_dung) VALUES (p_so_tk, 'Mở sổ tiết kiệm', p_so_tien, 'Trích tiền mở sổ tiết kiệm ' || p_ky_han || ' tháng');
                        END;
                        $$;
                    """)

                    cur.execute("""
                        CREATE OR REPLACE PROCEDURE sp_tat_toan_so_tiet_kiem(p_ma_so INT)
                        LANGUAGE plpgsql
                        AS $$
                        DECLARE
                            v_so_tk VARCHAR; v_so_tien_gui DECIMAL; v_lai_suat DECIMAL; v_ky_han INT; v_ngay_gui DATE; v_ngay_dao_han DATE; v_trang_thai VARCHAR; v_so_ngay_thuc_gui INT; v_tien_lai DECIMAL := 0; v_tong_tien_nhan DECIMAL;
                        BEGIN
                            SELECT so_tk, so_tien_gui, lai_suat, ky_han, ngay_gui, ngay_dao_han, trang_thai INTO v_so_tk, v_so_tien_gui, v_lai_suat, v_ky_han, v_ngay_gui, v_ngay_dao_han, v_trang_thai FROM so_tiet_kiem WHERE ma_so = p_ma_so;
                            IF v_trang_thai = 'Da tat toan' THEN RAISE EXCEPTION 'Sổ tiết kiệm này đã được tất toán!'; END IF;
                            v_so_ngay_thuc_gui := CURRENT_DATE - v_ngay_gui;
                            IF CURRENT_DATE >= v_ngay_dao_han THEN v_tien_lai := v_so_tien_gui * (v_lai_suat / 100) * (v_ky_han * 30.0 / 365);
                            ELSE v_tien_lai := v_so_tien_gui * (0.1 / 100) * (v_so_ngay_thuc_gui / 365.0); END IF;
                            v_tong_tien_nhan := v_so_tien_gui + v_tien_lai;
                            UPDATE so_tiet_kiem SET trang_thai = 'Da tat toan' WHERE ma_so = p_ma_so;
                            UPDATE tai_khoan SET so_du = so_du + v_tong_tien_nhan WHERE so_tk = v_so_tk;
                            INSERT INTO giao_dich (tk_dich, loai_gd, so_tien, noi_dung) VALUES (v_so_tk, 'Tất toán tiết kiệm', v_tong_tien_nhan, 'Tất toán sổ tiết kiệm (Lãi: ' || ROUND(v_tien_lai, 0) || 'đ)');
                        END;
                        $$;
                    """)

                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                print("Lỗi setup DB:", e)

    def chuyen_khoan(self, tk_nguon, tk_dich, so_tien, noi_dung):
        try:
            self.conn.rollback() # Xóa các giao dịch ngầm đang mở
            self.conn.autocommit = True
            with self.conn.cursor() as cur:
                ma_kh = self.current_user['ma'] if self.current_user['vai_tro'] == 'khachhang' else None
                cur.execute("CALL sp_chuyen_khoan(%s, %s, %s, %s, %s)", (tk_nguon, tk_dich, so_tien, noi_dung, ma_kh))
            self.conn.autocommit = False
            return True, "Chuyển khoản thành công!"
        except Exception as e:
            try: self.conn.autocommit = False
            except: pass
            err_msg = str(e)
            if "Số dư trong Thẻ/Tài khoản không đủ!" in err_msg or "tai_khoan_so_du_check" in err_msg or "Số dư tài khoản không đủ" in err_msg:
                err_msg = "Số dư không đủ để thực hiện giao dịch (cần duy trì tối thiểu 50.000đ)"
            elif "Nguồn trích tiền" in err_msg:
                err_msg = "Nguồn trích tiền (TK/Thẻ) không tồn tại!"
            elif "Chỉ được chuyển tiền" in err_msg:
                err_msg = "Chỉ được chuyển tiền từ tài sản của chính mình!"
            elif "Đích nhận tiền không tồn tại" in err_msg:
                err_msg = "Đích nhận tiền không tồn tại!"
            return False, err_msg

    def mo_so_tiet_kiem(self, so_tk, so_tien, ky_han):
        try:
            self.conn.rollback()
            self.conn.autocommit = True
            with self.conn.cursor() as cur:
                cur.execute("CALL sp_mo_so_tiet_kiem(%s, %s, %s)", (so_tk, so_tien, ky_han))
            self.conn.autocommit = False
            return True, "Mở sổ tiết kiệm thành công!"
        except Exception as e:
            try: self.conn.autocommit = False
            except: pass
            return False, str(e)

    def tat_toan_so_tiet_kiem(self, ma_so):
        try:
            self.conn.rollback()
            self.conn.autocommit = True
            with self.conn.cursor() as cur:
                cur.execute("CALL sp_tat_toan_so_tiet_kiem(%s)", (ma_so,))
            self.conn.autocommit = False
            return True, "Tất toán sổ tiết kiệm thành công!"
        except Exception as e:
            try: self.conn.autocommit = False
            except: pass
            return False, str(e)

    def lay_danh_sach_so_tiet_kiem(self, ma_kh):
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT s.ma_so, s.so_tk, s.so_tien_gui, s.ky_han, s.lai_suat, s.ngay_gui, s.ngay_dao_han, s.trang_thai
                    FROM so_tiet_kiem s
                    JOIN tai_khoan tk ON s.so_tk = tk.so_tk
                    WHERE tk.ma_kh = %s
                    ORDER BY s.ngay_gui DESC
                """, (ma_kh,))
                return cur.fetchall()
        except:
            return []

    def lay_ds_nguon_tien_cua_khach(self, ma_kh):
        """Lấy danh sách các tài sản (TK + Thẻ) có thể dùng để trích tiền"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT so_tk, so_du FROM tai_khoan WHERE ma_kh = %s", (ma_kh,))
                ds_tk = cur.fetchall()
                # Lấy số dư riêng biệt t.so_du của Thẻ
                cur.execute("""
                    SELECT t.so_the, t.so_du 
                    FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk 
                    WHERE tk.ma_kh = %s AND t.trang_thai = 'Hoat dong'
                """, (ma_kh,))
                ds_the = cur.fetchall()
                return ds_tk, ds_the
        except:
            return [], []

    def nap_tien(self, so_nhan, so_tien, noi_dung):
        try:
            self.conn.rollback() # Xóa các giao dịch ngầm đang mở
            self.conn.autocommit = True
            with self.conn.cursor() as cur:
                cur.execute("CALL sp_nap_tien(%s, %s, %s)", (so_nhan, so_tien, noi_dung))
            self.conn.autocommit = False
            return True, "Nạp tiền thành công!"
        except Exception as e:
            try: self.conn.autocommit = False
            except: pass
            err_msg = str(e)
            if "Không tìm thấy số tài khoản hoặc số thẻ!" in err_msg:
                err_msg = "Không tìm thấy số tài khoản hoặc số thẻ!"
            return False, err_msg

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
                if res: return res[0], "Tài khoản"
                
                cur.execute("SELECT kh.ho_ten FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk JOIN khach_hang kh ON tk.ma_kh = kh.ma_kh WHERE t.so_the = %s", (so_nhan,))
                res = cur.fetchone()
                return (res[0], "Thẻ") if res else (None, None)
        except: return None, None

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
        """Bổ sung lấy cột so_du của bảng the"""
        with self.conn.cursor() as cur:
            sql = "SELECT t.so_the, t.so_tk, kh.ho_ten, l.ten_loai, t.so_du, t.ngay_het_han, t.trang_thai FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk JOIN khach_hang kh ON tk.ma_kh = kh.ma_kh JOIN loai_the l ON t.ma_loai_the = l.ma_loai_the"
            if ma_kh: sql += " WHERE kh.ma_kh = %s"
            cur.execute(sql, (ma_kh,) if ma_kh else None)
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

    def tra_cuu_giao_dich_nang_cao(self, so_tk=None, so_the=None, tu_ngay=None, den_ngay=None, ma_kh=None):
        query = "SELECT ma_gd, loai_gd, so_tien, ngay_gd, tk_nguon, tk_dich, noi_dung FROM giao_dich WHERE 1=1"
        params = []

        if ma_kh:
            kh_condition = """
                (tk_nguon IN (SELECT so_tk FROM tai_khoan WHERE ma_kh = %s) 
                 OR tk_dich IN (SELECT so_tk FROM tai_khoan WHERE ma_kh = %s)
                 OR tk_nguon IN (SELECT t.so_the FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk WHERE tk.ma_kh = %s)
                 OR tk_dich IN (SELECT t.so_the FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk WHERE tk.ma_kh = %s))
            """
            query += " AND " + kh_condition
            params.extend([ma_kh, ma_kh, ma_kh, ma_kh])

        if so_tk:
            query += " AND (tk_nguon = %s OR tk_dich = %s)"
            params.extend([so_tk, so_tk])

        if so_the:
            query += " AND (tk_nguon = %s OR tk_dich = %s)"
            params.extend([so_the, so_the])

        if tu_ngay:
            query += " AND ngay_gd >= %s"
            params.append(f"{tu_ngay} 00:00:00")
        if den_ngay:
            query += " AND ngay_gd <= %s"
            params.append(f"{den_ngay} 23:59:59")

        query += " ORDER BY ngay_gd DESC"
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, tuple(params))
                return cur.fetchall()
        except: return []

    def sao_ke_giao_dich(self, ma_kh=None, so_tk=None):
        """Trả về danh sách giao dịch cho báo cáo nhanh.
        - Nếu `ma_kh` được cung cấp: lấy tất cả giao dịch liên quan tới KH đó.
        - Nếu `so_tk` được cung cấp: lấy giao dịch theo số tài khoản.
        """
        try:
            with self.conn.cursor() as cur:
                if ma_kh:
                    query = """
                        SELECT ma_gd, loai_gd, so_tien, ngay_gd, tk_nguon, tk_dich, noi_dung
                        FROM giao_dich
                        WHERE tk_nguon IN (SELECT so_tk FROM tai_khoan WHERE ma_kh = %s)
                          OR tk_dich IN (SELECT so_tk FROM tai_khoan WHERE ma_kh = %s)
                          OR tk_nguon IN (SELECT t.so_the FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk WHERE tk.ma_kh = %s)
                          OR tk_dich IN (SELECT t.so_the FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk WHERE tk.ma_kh = %s)
                        ORDER BY ngay_gd DESC
                    """
                    cur.execute(query, (ma_kh, ma_kh, ma_kh, ma_kh))
                elif so_tk:
                    cur.execute("SELECT ma_gd, loai_gd, so_tien, ngay_gd, tk_nguon, tk_dich, noi_dung FROM giao_dich WHERE tk_nguon = %s OR tk_dich = %s ORDER BY ngay_gd DESC", (so_tk, so_tk))
                else:
                    cur.execute("SELECT ma_gd, loai_gd, so_tien, ngay_gd, tk_nguon, tk_dich, noi_dung FROM giao_dich ORDER BY ngay_gd DESC")
                return cur.fetchall()
        except Exception:
            return []

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

    def lay_du_lieu_cho_ai(self, ma_kh):
        """Trích xuất dữ liệu tổng quan của khách hàng để làm bối cảnh (context) cho AI"""
        try:
            with self.conn.cursor() as cur:
                # 1. Lấy tổng tài sản (dùng Function đã tạo trong SQL)
                cur.execute("SELECT fn_tinh_tong_tai_san(%s)", (ma_kh,))
                tong_tai_san = cur.fetchone()[0] or 0
                
                # 2. Lấy tổng tiền gửi tiết kiệm
                cur.execute("SELECT SUM(so_tien_gui) FROM so_tiet_kiem s JOIN tai_khoan tk ON s.so_tk = tk.so_tk WHERE tk.ma_kh = %s AND s.trang_thai = 'Dang gui'", (ma_kh,))
                tong_tiet_kiem = cur.fetchone()[0] or 0

                # 3. Lấy 5 giao dịch gần nhất
                cur.execute("""
                    SELECT ngay_gd, loai_gd, so_tien, noi_dung 
                    FROM vw_sao_ke_giao_dich 
                    WHERE tk_nguon IN (SELECT so_tk FROM tai_khoan WHERE ma_kh = %s UNION SELECT t.so_the FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk WHERE tk.ma_kh = %s)
                       OR tk_dich IN (SELECT so_tk FROM tai_khoan WHERE ma_kh = %s UNION SELECT t.so_the FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk WHERE tk.ma_kh = %s)
                    ORDER BY ngay_gd DESC LIMIT 5
                """, (ma_kh, ma_kh, ma_kh, ma_kh))
                giao_dich = cur.fetchall()
                
                gd_text = ""
                for gd in giao_dich:
                    gd_text += f"- {gd[0].strftime('%d/%m/%Y')}: {gd[1]} {gd[2]:,.0f}đ ({gd[3]})\n"
                if not gd_text:
                    gd_text = "Chưa có giao dịch nào."
                    
                context = f"Thông tin tài chính hiện tại của khách hàng:\n- Tổng tài sản lưu động (Thẻ & TK): {tong_tai_san:,.0f} VND\n- Tổng tiền gửi tiết kiệm: {tong_tiet_kiem:,.0f} VND\n- Lịch sử 5 giao dịch gần nhất:\n{gd_text}"
                return context
        except Exception as e:
            print("Lỗi lấy dữ liệu AI:", e)
            return "Không thể lấy dữ liệu tài chính lúc này do lỗi."
