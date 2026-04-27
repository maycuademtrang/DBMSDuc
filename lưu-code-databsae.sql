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