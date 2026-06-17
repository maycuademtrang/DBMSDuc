-- 1. XÓA BẢNG CŨ
DROP TABLE IF EXISTS giao_dich CASCADE;
DROP TABLE IF EXISTS so_tiet_kiem CASCADE;
DROP TABLE IF EXISTS the CASCADE;
DROP TABLE IF EXISTS loai_the CASCADE;
DROP TABLE IF EXISTS tai_khoan CASCADE;
DROP TABLE IF EXISTS khach_hang CASCADE;
DROP TABLE IF EXISTS nhan_vien CASCADE;

-- DỌN DẸP CÁC HÀM CŨ (JUNK) TỪ CÁC PHIÊN BẢN TRƯỚC
DROP PROCEDURE IF EXISTS proc_transfer(VARCHAR, VARCHAR, DECIMAL, TEXT);
DROP PROCEDURE IF EXISTS sp_chuyen_khoan(VARCHAR, VARCHAR, DECIMAL, TEXT);
DROP FUNCTION IF EXISTS func_update_balance() CASCADE;

-- 2. TẠO LẠI BẢNG (Đã bổ sung tài khoản Khách hàng và Trạng thái thẻ)
CREATE TABLE nhan_vien (
    ma_nv VARCHAR(10) PRIMARY KEY, 
    ho_ten VARCHAR(100) NOT NULL, 
    username VARCHAR(50) UNIQUE NOT NULL, 
    password VARCHAR(255) NOT NULL, 
    vai_tro VARCHAR(20) NOT NULL, 
    luong DECIMAL(15, 2) CHECK (luong > 3000000)
);

CREATE TABLE khach_hang (
    ma_kh VARCHAR(10) PRIMARY KEY, 
    ho_ten VARCHAR(100) NOT NULL, 
    cmnd VARCHAR(12) UNIQUE NOT NULL, 
    username VARCHAR(50) UNIQUE, 
    password VARCHAR(255), 
    ma_nv_phu_trach VARCHAR(10) REFERENCES nhan_vien(ma_nv), 
    ngay_sinh DATE
);

CREATE TABLE tai_khoan (
    so_tk VARCHAR(15) PRIMARY KEY, 
    ma_kh VARCHAR(10) NOT NULL REFERENCES khach_hang(ma_kh), 
    so_du DECIMAL(15, 2) DEFAULT 50000 CHECK (so_du >= 50000), 
    ngay_mo DATE DEFAULT CURRENT_DATE, 
    trang_thai VARCHAR(20) DEFAULT 'Hoat dong'
);

CREATE TABLE loai_the (
    ma_loai_the VARCHAR(10) PRIMARY KEY, 
    ten_loai VARCHAR(50) NOT NULL, 
    mo_ta TEXT,
    dau_so VARCHAR(6) DEFAULT '970400'
);

CREATE TABLE the (
    so_the VARCHAR(20) PRIMARY KEY, 
    so_tk VARCHAR(15) NOT NULL REFERENCES tai_khoan(so_tk), 
    ma_loai_the VARCHAR(10) NOT NULL REFERENCES loai_the(ma_loai_the), 
    ngay_phat_hanh DATE DEFAULT CURRENT_DATE, 
    ngay_het_han DATE NOT NULL, 
    pin VARCHAR(255) NOT NULL, 
    so_du DECIMAL(15, 2) DEFAULT 0 CHECK (so_du >= 0),
    trang_thai VARCHAR(20) DEFAULT 'Hoat dong'
);

CREATE TABLE giao_dich (
    ma_gd SERIAL PRIMARY KEY, 
    tk_nguon VARCHAR(20), 
    tk_dich VARCHAR(20), 
    loai_gd VARCHAR(50), 
    so_tien DECIMAL(15, 2) NOT NULL, 
    ngay_gd TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
    noi_dung TEXT
);

CREATE TABLE so_tiet_kiem (
    ma_so SERIAL PRIMARY KEY,
    so_tk VARCHAR(15) NOT NULL REFERENCES tai_khoan(so_tk),
    so_tien_gui DECIMAL(15, 2) NOT NULL CHECK (so_tien_gui >= 1000000), 
    ky_han INT NOT NULL, 
    lai_suat DECIMAL(5, 2) NOT NULL, 
    ngay_gui DATE DEFAULT CURRENT_DATE,
    ngay_dao_han DATE NOT NULL,
    trang_thai VARCHAR(20) DEFAULT 'Dang gui'
);

-- 3. TỰ ĐỘNG CHÈN DỮ LIỆU MẪU NGAY SAU KHI TẠO BẢNG

-- 3.1. Dữ liệu Nhân viên
INSERT INTO nhan_vien (ma_nv, ho_ten, username, password, vai_tro, luong) VALUES 
('ADMIN01', 'Tổng Giám Đốc', 'admin', '123456', 'admin', 99000000),
('NV01', 'Nguyễn Văn A', 'nva_quanly', '123456', 'quanly', 25000000),
('NV02', 'Trần Thị B', 'ttb_nhanvien', '123456', 'nhanvien', 15000000);

-- 3.2. Dữ liệu Khách hàng
INSERT INTO khach_hang (ma_kh, ho_ten, cmnd, username, password, ma_nv_phu_trach, ngay_sinh) VALUES 
('KH1', 'Phạm Văn Khách', '012345678912', 'khachhang1', '123456', 'NV02', '1995-05-15'),
('KH2', 'Lê Thị Thu', '098765432109', 'khachhang2', '123456', 'NV02', '1998-10-20');

-- 3.3. Dữ liệu Tài khoản (Tự động cấp số dư)
INSERT INTO tai_khoan (so_tk, ma_kh, so_du, trang_thai) VALUES 
('1111222233', 'KH1', 5000000, 'Hoat dong'),
('4444555566', 'KH2', 3000000, 'Hoat dong');

-- 3.4. Danh mục Loại thẻ
INSERT INTO loai_the (ma_loai_the, ten_loai, mo_ta, dau_so) VALUES 
('NAPAS', 'Thẻ ATM Nội Địa', 'Rút tiền và thanh toán trong nước', '970400'),
('VISA_DB', 'Visa Debit', 'Thẻ ghi nợ quốc tế', '422000');

-- 3.5. Dữ liệu Thẻ (Liên kết với tài khoản trên)
INSERT INTO the (so_the, so_tk, ma_loai_the, ngay_het_han, pin, so_du, trang_thai) VALUES 
('9704001234567890', '1111222233', 'NAPAS', '2030-12-31', '123456', 1500000, 'Hoat dong'),
('4220000987654321', '4444555566', 'VISA_DB', '2028-06-30', '000000', 500000, 'Hoat dong');

-- 3.6. Dữ liệu Lịch sử Giao dịch mẫu
INSERT INTO giao_dich (tk_dich, loai_gd, so_tien, noi_dung) VALUES 
('1111222233', 'Nạp tiền', 1000000, 'Nạp tiền mặt khởi tạo tài khoản'),
('4444555566', 'Nạp tiền', 500000, 'Nhận tiền thưởng tham gia App Bankdash');

-- =========================================================
-- 4. TRIGGER FUNCTIONS & TRIGGERS (3 Triggers)
-- =========================================================

-- Trigger 1: Kiểm tra số dư trước khi thực hiện giao dịch (đảm bảo số dư tối thiểu 50k)
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

CREATE TRIGGER trg_check_so_du
BEFORE INSERT ON giao_dich
FOR EACH ROW
EXECUTE FUNCTION fn_check_so_du();

-- Trigger 2: Cập nhật số dư tự động sau khi giao dịch thành công
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

CREATE TRIGGER trg_cap_nhat_so_du
AFTER INSERT ON giao_dich
FOR EACH ROW
EXECUTE FUNCTION update_so_du_sau_giao_dich();

-- Trigger 3: Kiểm tra trạng thái tài khoản/thẻ trước khi giao dịch
CREATE OR REPLACE FUNCTION fn_check_trang_thai_gd()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.tk_nguon IS NOT NULL THEN
        IF length(NEW.tk_nguon) <= 15 THEN
            IF EXISTS (SELECT 1 FROM tai_khoan WHERE so_tk = NEW.tk_nguon AND trang_thai != 'Hoat dong') THEN
                RAISE EXCEPTION 'Tài khoản nguồn đang bị khóa hoặc không hoạt động!';
            END IF;
        ELSE
            IF EXISTS (SELECT 1 FROM the WHERE so_the = NEW.tk_nguon AND trang_thai != 'Hoat dong') THEN
                RAISE EXCEPTION 'Thẻ nguồn đang bị khóa hoặc không hoạt động!';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_trang_thai_gd
BEFORE INSERT ON giao_dich
FOR EACH ROW
EXECUTE FUNCTION fn_check_trang_thai_gd();

-- =========================================================
-- 5. NORMAL FUNCTIONS (1 Function)
-- =========================================================

-- Function 1: Tính tổng tài sản của một khách hàng
CREATE OR REPLACE FUNCTION fn_tinh_tong_tai_san(p_ma_kh VARCHAR)
RETURNS DECIMAL AS $$
DECLARE
    v_tong_tk DECIMAL := 0;
    v_tong_the DECIMAL := 0;
BEGIN
    SELECT COALESCE(SUM(so_du), 0) INTO v_tong_tk FROM tai_khoan WHERE ma_kh = p_ma_kh;
    SELECT COALESCE(SUM(t.so_du), 0) INTO v_tong_the 
    FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk 
    WHERE tk.ma_kh = p_ma_kh;
    
    RETURN v_tong_tk + v_tong_the;
END;
$$ LANGUAGE plpgsql;

-- Function 2: Tính tổng phí thường niên các thẻ của một khách hàng
CREATE OR REPLACE FUNCTION fn_tinh_phi_thuong_nien(p_ma_kh VARCHAR)
RETURNS DECIMAL AS $$
DECLARE
    v_tong_phi DECIMAL := 0;
BEGIN
    SELECT COALESCE(SUM(l.phi_thuong_nien), 0) INTO v_tong_phi
    FROM the t
    JOIN loai_the l ON t.ma_loai_the = l.ma_loai_the
    JOIN tai_khoan tk ON t.so_tk = tk.so_tk
    WHERE tk.ma_kh = p_ma_kh AND t.trang_thai = 'Hoat dong';
    
    RETURN v_tong_phi;
END;
$$ LANGUAGE plpgsql;

-- Function 3: Thống kê tổng tiền theo loại giao dịch (Nạp/Rút/Chuyển) của 1 tài khoản trong tháng hiện tại
CREATE OR REPLACE FUNCTION fn_thong_ke_gd_thang_nay(p_so_tk VARCHAR, p_loai_gd VARCHAR)
RETURNS DECIMAL AS $$
DECLARE
    v_tong_tien DECIMAL := 0;
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

-- =========================================================
-- 6. STORED PROCEDURES (5 Procedures)
-- =========================================================

-- Procedure 1: Khóa tài khoản và toàn bộ thẻ liên kết
CREATE OR REPLACE PROCEDURE sp_khoa_tai_khoan_va_the(p_so_tk VARCHAR)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE tai_khoan SET trang_thai = 'Da Khoa' WHERE so_tk = p_so_tk;
    UPDATE the SET trang_thai = 'Da Khoa' WHERE so_tk = p_so_tk;
END;
$$;

-- Procedure 2: Mở khóa tài khoản và toàn bộ thẻ liên kết
CREATE OR REPLACE PROCEDURE sp_mo_khoa_tai_khoan_va_the(p_so_tk VARCHAR)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE tai_khoan SET trang_thai = 'Hoat dong' WHERE so_tk = p_so_tk;
    UPDATE the SET trang_thai = 'Hoat dong' WHERE so_tk = p_so_tk;
END;
$$;

-- Procedure 3: Thực hiện nạp tiền
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

-- Procedure 4: Thực hiện rút tiền
CREATE OR REPLACE PROCEDURE sp_rut_tien(
    p_tk_nguon VARCHAR, 
    p_so_tien DECIMAL, 
    p_noi_dung TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_exists INT;
BEGIN
    IF length(p_tk_nguon) <= 15 THEN
        SELECT 1 INTO v_exists FROM tai_khoan WHERE so_tk = p_tk_nguon;
    ELSE
        SELECT 1 INTO v_exists FROM the WHERE so_the = p_tk_nguon;
    END IF;

    IF v_exists IS NULL THEN
        RAISE EXCEPTION 'Không tìm thấy số tài khoản hoặc số thẻ!';
    END IF;

    INSERT INTO giao_dich (tk_nguon, loai_gd, so_tien, noi_dung)
    VALUES (p_tk_nguon, 'Rút tiền', p_so_tien, p_noi_dung);
    COMMIT;
END;
$$;

-- Procedure 5: Thực hiện chuyển khoản an toàn
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
    -- 1. Xác định Nguồn
    IF length(p_tk_nguon) <= 15 THEN
        SELECT so_du, ma_kh INTO v_so_du, v_chu_tk FROM tai_khoan WHERE so_tk = p_tk_nguon;
    ELSE
        SELECT t.so_du, tk.ma_kh INTO v_so_du, v_chu_tk FROM the t JOIN tai_khoan tk ON t.so_tk = tk.so_tk WHERE t.so_the = p_tk_nguon;
    END IF;

    IF v_so_du IS NULL THEN RAISE EXCEPTION 'Nguồn trích tiền (TK/Thẻ) không tồn tại!'; END IF;
    IF p_ma_kh IS NOT NULL AND v_chu_tk != p_ma_kh THEN RAISE EXCEPTION 'Chỉ được chuyển tiền từ tài sản của chính mình!'; END IF;
    IF v_so_du < p_so_tien THEN RAISE EXCEPTION 'Số dư trong Thẻ/Tài khoản không đủ!'; END IF;

    -- 2. Xác định Đích
    IF length(p_tk_dich) <= 15 THEN
        SELECT 1 INTO v_exists FROM tai_khoan WHERE so_tk = p_tk_dich;
    ELSE
        SELECT 1 INTO v_exists FROM the WHERE so_the = p_tk_dich;
    END IF;

    IF v_exists IS NULL THEN RAISE EXCEPTION 'Đích nhận tiền không tồn tại!'; END IF;

    -- 3. Thêm bản ghi giao dịch
    INSERT INTO giao_dich (tk_nguon, tk_dich, loai_gd, so_tien, noi_dung)
    VALUES (p_tk_nguon, p_tk_dich, 'Chuyển khoản', p_so_tien, p_noi_dung);
    COMMIT;
END;
$$;

-- Procedure 6: Mở sổ tiết kiệm
CREATE OR REPLACE PROCEDURE sp_mo_so_tiet_kiem(
    p_so_tk VARCHAR,
    p_so_tien DECIMAL,
    p_ky_han INT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_so_du DECIMAL;
    v_lai_suat DECIMAL;
    v_ngay_dao_han DATE;
BEGIN
    SELECT so_du INTO v_so_du FROM tai_khoan WHERE so_tk = p_so_tk;
    IF v_so_du < p_so_tien + 50000 THEN
        RAISE EXCEPTION 'Số dư không đủ để mở sổ tiết kiệm (cần dư tối thiểu 50.000đ sau khi gửi)!';
    END IF;

    CASE p_ky_han
        WHEN 1 THEN v_lai_suat := 4.5;
        WHEN 3 THEN v_lai_suat := 5.0;
        WHEN 6 THEN v_lai_suat := 6.0;
        WHEN 12 THEN v_lai_suat := 7.0;
        WHEN 24 THEN v_lai_suat := 7.5;
        ELSE RAISE EXCEPTION 'Kỳ hạn không hợp lệ!';
    END CASE;

    v_ngay_dao_han := CURRENT_DATE + (p_ky_han || ' months')::INTERVAL;

    UPDATE tai_khoan SET so_du = so_du - p_so_tien WHERE so_tk = p_so_tk;

    INSERT INTO so_tiet_kiem (so_tk, so_tien_gui, ky_han, lai_suat, ngay_dao_han)
    VALUES (p_so_tk, p_so_tien, p_ky_han, v_lai_suat, v_ngay_dao_han);

    INSERT INTO giao_dich (tk_nguon, loai_gd, so_tien, noi_dung)
    VALUES (p_so_tk, 'Mở sổ tiết kiệm', p_so_tien, 'Trích tiền mở sổ tiết kiệm ' || p_ky_han || ' tháng');
END;
$$;

-- Procedure 7: Tất toán sổ tiết kiệm
CREATE OR REPLACE PROCEDURE sp_tat_toan_so_tiet_kiem(
    p_ma_so INT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_so_tk VARCHAR;
    v_so_tien_gui DECIMAL;
    v_lai_suat DECIMAL;
    v_ky_han INT;
    v_ngay_gui DATE;
    v_ngay_dao_han DATE;
    v_trang_thai VARCHAR;
    v_so_ngay_thuc_gui INT;
    v_tien_lai DECIMAL := 0;
    v_tong_tien_nhan DECIMAL;
BEGIN
    SELECT so_tk, so_tien_gui, lai_suat, ky_han, ngay_gui, ngay_dao_han, trang_thai
    INTO v_so_tk, v_so_tien_gui, v_lai_suat, v_ky_han, v_ngay_gui, v_ngay_dao_han, v_trang_thai
    FROM so_tiet_kiem WHERE ma_so = p_ma_so;

    IF v_trang_thai = 'Da tat toan' THEN
        RAISE EXCEPTION 'Sổ tiết kiệm này đã được tất toán!';
    END IF;

    v_so_ngay_thuc_gui := CURRENT_DATE - v_ngay_gui;
    
    IF CURRENT_DATE >= v_ngay_dao_han THEN
        v_tien_lai := v_so_tien_gui * (v_lai_suat / 100) * (v_ky_han * 30.0 / 365);
    ELSE
        v_tien_lai := v_so_tien_gui * (0.1 / 100) * (v_so_ngay_thuc_gui / 365.0);
    END IF;

    v_tong_tien_nhan := v_so_tien_gui + v_tien_lai;

    UPDATE so_tiet_kiem SET trang_thai = 'Da tat toan' WHERE ma_so = p_ma_so;

    UPDATE tai_khoan SET so_du = so_du + v_tong_tien_nhan WHERE so_tk = v_so_tk;

    INSERT INTO giao_dich (tk_dich, loai_gd, so_tien, noi_dung)
    VALUES (v_so_tk, 'Tất toán tiết kiệm', v_tong_tien_nhan, 'Tất toán sổ tiết kiệm (Lãi: ' || ROUND(v_tien_lai, 0) || 'đ)');
END;
$$;

-- =========================================================
-- 7. VIEWS (GÓC NHÌN DỮ LIỆU) (4 Views)
-- =========================================================

-- View 1: Thông tin tổng hợp Khách hàng và Tài khoản
CREATE OR REPLACE VIEW vw_thong_tin_khach_hang AS
SELECT 
    kh.ma_kh, 
    kh.ho_ten, 
    kh.cmnd, 
    tk.so_tk, 
    tk.so_du,
    tk.trang_thai AS trang_thai_tk
FROM khach_hang kh
LEFT JOIN tai_khoan tk ON kh.ma_kh = tk.ma_kh;

-- View 2: Chi tiết các thẻ đang phát hành và Chủ thẻ
CREATE OR REPLACE VIEW vw_chi_tiet_the AS
SELECT 
    t.so_the,
    l.ten_loai AS loai_the,
    kh.ho_ten AS ten_chu_the,
    t.so_tk AS tai_khoan_lien_ket,
    t.ngay_het_han,
    t.trang_thai
FROM the t
JOIN loai_the l ON t.ma_loai_the = l.ma_loai_the
JOIN tai_khoan tk ON t.so_tk = tk.so_tk
JOIN khach_hang kh ON tk.ma_kh = kh.ma_kh;

-- View 3: Lịch sử giao dịch 
CREATE OR REPLACE VIEW vw_sao_ke_giao_dich AS
SELECT 
    gd.ma_gd,
    gd.ngay_gd,
    gd.loai_gd,
    gd.tk_nguon,
    gd.tk_dich,
    gd.so_tien,
    gd.noi_dung
FROM giao_dich gd
ORDER BY gd.ngay_gd DESC;

-- View 4: Danh sách nhân viên
CREATE OR REPLACE VIEW vw_danh_sach_nhan_vien AS
SELECT ma_nv, ho_ten, vai_tro, luong
FROM nhan_vien;
