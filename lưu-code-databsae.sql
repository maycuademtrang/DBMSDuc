-- 1. XÓA BẢNG CŨ
DROP TABLE IF EXISTS giao_dich CASCADE;
DROP TABLE IF EXISTS the CASCADE;
DROP TABLE IF EXISTS loai_the CASCADE;
DROP TABLE IF EXISTS tai_khoan CASCADE;
DROP TABLE IF EXISTS khach_hang CASCADE;
DROP TABLE IF EXISTS nhan_vien CASCADE;

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
    mo_ta TEXT
);

CREATE TABLE the (
    so_the VARCHAR(20) PRIMARY KEY, 
    so_tk VARCHAR(15) NOT NULL REFERENCES tai_khoan(so_tk), 
    ma_loai_the VARCHAR(10) NOT NULL REFERENCES loai_the(ma_loai_the), 
    ngay_phat_hanh DATE DEFAULT CURRENT_DATE, 
    ngay_het_han DATE NOT NULL, 
    pin VARCHAR(255) NOT NULL, 
    trang_thai VARCHAR(20) DEFAULT 'Hoat dong'
);

CREATE TABLE giao_dich (
    ma_gd SERIAL PRIMARY KEY, 
    tk_nguon VARCHAR(15) REFERENCES tai_khoan(so_tk), 
    tk_dich VARCHAR(15) REFERENCES tai_khoan(so_tk), 
    loai_gd VARCHAR(50), 
    so_tien DECIMAL(15, 2) NOT NULL, 
    ngay_gd TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
    noi_dung TEXT
);

-- 3. TỰ ĐỘNG CHÈN DỮ LIỆU MẪU NGAY SAU KHI TẠO BẢNG
-- Tạo Giám đốc
INSERT INTO nhan_vien (ma_nv, ho_ten, username, password, vai_tro, luong) 
VALUES ('ADMIN01', 'Tổng Giám Đốc', 'admin', '123456', 'admin', 99000000);

-- Tạo sẵn các loại thẻ danh mục
INSERT INTO loai_the (ma_loai_the, ten_loai, mo_ta) VALUES 
('NAPAS', 'Thẻ ATM Nội Địa', 'Rút tiền và thanh toán trong nước'),
('VISA_DB', 'Visa Debit', 'Thẻ ghi nợ quốc tế');

-- =========================================================
-- 4. FUNCTION & TRIGGER
-- =========================================================

-- Trigger: Kiểm tra số dư trước khi thực hiện giao dịch (đảm bảo số dư tối thiểu 50k)
CREATE OR REPLACE FUNCTION fn_check_so_du()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.loai_gd IN ('Rút tiền', 'Chuyển khoản') THEN
        IF NOT EXISTS (
            SELECT 1 FROM tai_khoan 
            WHERE so_tk = NEW.tk_nguon AND (so_du - NEW.so_tien) >= 50000
        ) THEN
            RAISE EXCEPTION 'Số dư không đủ để thực hiện giao dịch (cần duy trì tối thiểu 50.000đ)';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_so_du
BEFORE INSERT ON giao_dich
FOR EACH ROW
EXECUTE FUNCTION fn_check_so_du();

-- Trigger: Cập nhật số dư tự động sau khi giao dịch thành công
CREATE OR REPLACE FUNCTION update_so_du_sau_giao_dich()
RETURNS TRIGGER AS $$
BEGIN
    -- Trừ tiền tài khoản nguồn nếu là rút tiền hoặc chuyển khoản
    IF NEW.loai_gd IN ('Rút tiền', 'Chuyển khoản') AND NEW.tk_nguon IS NOT NULL THEN
        UPDATE tai_khoan 
        SET so_du = so_du - NEW.so_tien 
        WHERE so_tk = NEW.tk_nguon;
    END IF;

    -- Cộng tiền tài khoản đích nếu là nạp tiền hoặc chuyển khoản
    IF NEW.loai_gd IN ('Nạp tiền', 'Chuyển khoản') AND NEW.tk_dich IS NOT NULL THEN
        UPDATE tai_khoan 
        SET so_du = so_du + NEW.so_tien 
        WHERE so_tk = NEW.tk_dich;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_cap_nhat_so_du
AFTER INSERT ON giao_dich
FOR EACH ROW
EXECUTE FUNCTION update_so_du_sau_giao_dich();

-- =========================================================
-- 5. STORED PROCEDURE
-- =========================================================

-- Procedure: Khóa tài khoản và toàn bộ thẻ liên kết
CREATE OR REPLACE PROCEDURE sp_khoa_tai_khoan_va_the(p_so_tk VARCHAR)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Khóa tài khoản
    UPDATE tai_khoan 
    SET trang_thai = 'Khóa' 
    WHERE so_tk = p_so_tk;

    -- Khóa các thẻ liên kết với tài khoản này
    UPDATE the 
    SET trang_thai = 'Khóa' 
    WHERE so_tk = p_so_tk;
END;
$$;

-- Procedure: Thực hiện chuyển khoản an toàn
CREATE OR REPLACE PROCEDURE sp_chuyen_khoan(
    p_tk_nguon VARCHAR, 
    p_tk_dich VARCHAR, 
    p_so_tien DECIMAL, 
    p_noi_dung TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Thêm bản ghi giao dịch (Trigger sẽ tự động kiểm tra và cập nhật số dư)
    INSERT INTO giao_dich (tk_nguon, tk_dich, loai_gd, so_tien, noi_dung)
    VALUES (p_tk_nguon, p_tk_dich, 'Chuyển khoản', p_so_tien, p_noi_dung);
END;
$$;
