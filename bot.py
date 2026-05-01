#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Telegram - Tứ Trụ Đại Kỵ
Kết hợp: Tứ Trụ Thập Thần + Tử Vi + Tiết Khí + Vượng/Suy
"""

import logging
import os
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ============================================================
# CONFIG — đọc từ biến môi trường Railway
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("❌ Chưa set biến môi trường BOT_TOKEN!")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
# DỮ LIỆU TỨ TRỤ
# ============================================================

THIEN_CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
DIA_CHI   = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]

NGU_HANH_CAN = {
    "Giáp": "Mộc", "Ất": "Mộc",
    "Bính": "Hỏa", "Đinh": "Hỏa",
    "Mậu": "Thổ", "Kỷ": "Thổ",
    "Canh": "Kim", "Tân": "Kim",
    "Nhâm": "Thủy", "Quý": "Thủy"
}

NGU_HANH_CHI = {
    "Tý": "Thủy", "Sửu": "Thổ", "Dần": "Mộc", "Mão": "Mộc",
    "Thìn": "Thổ", "Tỵ": "Hỏa", "Ngọ": "Hỏa", "Mùi": "Thổ",
    "Thân": "Kim", "Dậu": "Kim", "Tuất": "Thổ", "Hợi": "Thủy"
}

AM_DUONG_CAN = {
    "Giáp": "Dương", "Ất": "Âm", "Bính": "Dương", "Đinh": "Âm",
    "Mậu": "Dương", "Kỷ": "Âm", "Canh": "Dương", "Tân": "Âm",
    "Nhâm": "Dương", "Quý": "Âm"
}

# Ngũ hành tương sinh / tương khắc
TUONG_SINH = {"Mộc": "Hỏa", "Hỏa": "Thổ", "Thổ": "Kim", "Kim": "Thủy", "Thủy": "Mộc"}
TUONG_KHAC = {"Mộc": "Thổ", "Thổ": "Thủy", "Thủy": "Hỏa", "Hỏa": "Kim", "Kim": "Mộc"}

# Thập Thần mapping (Nhật Chủ → Thập Thần theo ngũ hành can)
def tinh_thap_than(nhat_chu_can: str, can_khac: str) -> str:
    nh_hanh = NGU_HANH_CAN[nhat_chu_can]
    kh_hanh = NGU_HANH_CAN[can_khac]
    nh_am_duong = AM_DUONG_CAN[nhat_chu_can]
    kh_am_duong = AM_DUONG_CAN[can_khac]
    cung_am_duong = (nh_am_duong == kh_am_duong)

    if kh_hanh == nh_hanh:
        return "Kiếp Tài" if cung_am_duong else "Tỷ Kiên"
    if TUONG_SINH.get(kh_hanh) == nh_hanh:          # kh sinh nh
        return "Thiên Ấn" if cung_am_duong else "Chính Ấn"
    if TUONG_SINH.get(nh_hanh) == kh_hanh:          # nh sinh kh
        return "Thực Thần" if cung_am_duong else "Thương Quan"
    if TUONG_KHAC.get(nh_hanh) == kh_hanh:          # nh khắc kh
        return "Thiên Tài" if cung_am_duong else "Chính Tài"
    if TUONG_KHAC.get(kh_hanh) == nh_hanh:          # kh khắc nh
        return "Thất Sát" if cung_am_duong else "Chính Quan"
    return "?"

THAP_THAN_XAU = {"Thất Sát", "Thương Quan", "Kiếp Tài"}
THAP_THAN_TOT = {"Chính Ấn", "Thiên Ấn", "Chính Quan", "Chính Tài", "Thực Thần"}

# ============================================================
# TIẾT KHÍ 24 TIẾT (ngày dương lịch gần đúng)
# ============================================================
TIET_KHI = [
    (1,  6,  "Tiểu Hàn"),   (1, 20, "Đại Hàn"),
    (2,  4,  "Lập Xuân"),   (2, 19, "Vũ Thủy"),
    (3,  6,  "Kinh Trập"),  (3, 21, "Xuân Phân"),
    (4,  5,  "Thanh Minh"), (4, 20, "Cốc Vũ"),
    (5,  6,  "Lập Hạ"),     (5, 21, "Tiểu Mãn"),
    (6,  6,  "Mang Chủng"), (6, 21, "Hạ Chí"),
    (7,  7,  "Tiểu Thử"),   (7, 23, "Đại Thử"),
    (8,  7,  "Lập Thu"),    (8, 23, "Xử Thử"),
    (9,  8,  "Bạch Lộ"),    (9, 23, "Thu Phân"),
    (10, 8,  "Hàn Lộ"),     (10,23, "Sương Giáng"),
    (11, 7,  "Lập Đông"),   (11,22, "Tiểu Tuyết"),
    (12, 7,  "Đại Tuyết"),  (12,22, "Đông Chí"),
]

# Tháng âm lịch theo tiết khí (Lập Xuân = tháng Dần = tháng 1 âm)
# Index tiết khí chẵn (0,2,4...) = Lập tiết → bắt đầu tháng mới
THANG_AM_LICH_BY_TIET = {
    "Lập Xuân": ("Dần", 1), "Kinh Trập": ("Mão", 2), "Thanh Minh": ("Thìn", 3),
    "Lập Hạ":   ("Tỵ",  4), "Mang Chủng": ("Ngọ", 5), "Tiểu Thử": ("Mùi", 6),
    "Lập Thu":  ("Thân",7), "Bạch Lộ": ("Dậu", 8),   "Hàn Lộ": ("Tuất", 9),
    "Lập Đông": ("Hợi",10), "Đại Tuyết": ("Tý", 11),  "Tiểu Hàn": ("Sửu", 12),
}

def get_tiet_khi_hien_tai(ngay: date) -> tuple:
    """Trả về (tên tiết khí hiện tại, tháng chi âm lịch, số tháng)"""
    tiet_hien_tai = None
    for (thang, ngay_tiet, ten) in reversed(TIET_KHI):
        tiet_date = date(ngay.year, thang, ngay_tiet)
        if ngay >= tiet_date:
            tiet_hien_tai = ten
            break
    if tiet_hien_tai is None:
        tiet_hien_tai = "Đông Chí"

    # Tìm tiết Lập gần nhất trước đó
    for ten, (chi, so_thang) in THANG_AM_LICH_BY_TIET.items():
        # Tìm xem tháng hiện tại thuộc tiết nào
        pass

    # Xác định tháng Can Chi hiện tại theo tiết khí
    thang_chi = "Dần"
    so_thang = 1
    for (thang, ngay_tiet, ten) in reversed(TIET_KHI):
        tiet_date = date(ngay.year, thang, ngay_tiet)
        if ngay >= tiet_date and ten in THANG_AM_LICH_BY_TIET:
            thang_chi, so_thang = THANG_AM_LICH_BY_TIET[ten]
            break

    return tiet_hien_tai, thang_chi, so_thang

# ============================================================
# TÍNH TỨ TRỤ
# ============================================================

def tinh_can_nam(nam: int) -> str:
    return THIEN_CAN[(nam - 4) % 10]

def tinh_chi_nam(nam: int) -> str:
    return DIA_CHI[(nam - 4) % 12]

def tinh_can_thang(nam: int, thang_chi: str) -> str:
    # Can tháng phụ thuộc vào Can năm
    can_nam = tinh_can_nam(nam)
    nh = NGU_HANH_CAN[can_nam]
    # Công thức: Can tháng bắt đầu từ can năm
    # Giáp/Kỷ → tháng Dần bắt đầu Bính Dần
    MAP_CAN_NAM_TO_CAN_THANG_DIEM = {
        "Giáp": 2, "Kỷ": 2,   # Bính
        "Ất":  4, "Canh": 4,   # Mậu
        "Bính": 6, "Tân": 6,   # Canh
        "Đinh": 8, "Nhâm": 8,  # Nhâm
        "Mậu": 0, "Quý": 0,    # Giáp
    }
    chi_idx = DIA_CHI.index(thang_chi)
    # Tháng Dần = index 2, tính offset từ Dần
    offset_tu_dan = (chi_idx - 2) % 12
    can_diem = MAP_CAN_NAM_TO_CAN_THANG_DIEM[can_nam]
    can_idx = (can_diem + offset_tu_dan) % 10
    return THIEN_CAN[can_idx]

def tinh_can_ngay(ngay: date) -> str:
    # Công thức Chu Kỳ 60: tham chiếu ngày cố định
    # 1/1/1900 = Giáp Tuất → idx 10 trong bảng 60
    ref = date(1900, 1, 1)
    delta = (ngay - ref).days
    can_idx = (delta + 10) % 10  # Giáp=0 → +10 offset
    return THIEN_CAN[can_idx % 10]

def tinh_chi_ngay(ngay: date) -> str:
    ref = date(1900, 1, 1)
    delta = (ngay - ref).days
    chi_idx = (delta + 10) % 12
    return DIA_CHI[chi_idx]

def tinh_can_gio(gio: int, nhat_chu_can: str) -> str:
    # Can giờ dựa vào Nhật Chủ Can và địa chi giờ
    chi_gio = tinh_chi_gio(gio)
    chi_idx = DIA_CHI.index(chi_gio)
    MAP_NHAT_CHU_TO_CAN_TY = {
        "Giáp": 0, "Kỷ": 0,
        "Ất":  2, "Canh": 2,
        "Bính": 4, "Tân": 4,
        "Đinh": 6, "Nhâm": 6,
        "Mậu": 8, "Quý": 8,
    }
    can_ty = MAP_NHAT_CHU_TO_CAN_TY[nhat_chu_can]
    can_idx = (can_ty + chi_idx) % 10
    return THIEN_CAN[can_idx]

def tinh_chi_gio(gio: int) -> str:
    # Tý: 23-1h, Sửu: 1-3h, Dần: 3-5h, ...
    CHI_GIO = [
        (23, 1,  "Tý"),   (1,  3,  "Sửu"),  (3,  5,  "Dần"),
        (5,  7,  "Mão"),  (7,  9,  "Thìn"), (9,  11, "Tỵ"),
        (11, 13, "Ngọ"),  (13, 15, "Mùi"),  (15, 17, "Thân"),
        (17, 19, "Dậu"),  (19, 21, "Tuất"), (21, 23, "Hợi"),
    ]
    for (h_start, h_end, chi) in CHI_GIO:
        if h_start == 23:
            if gio >= 23 or gio < 1:
                return chi
        else:
            if h_start <= gio < h_end:
                return chi
    return "Tý"

def build_tu_tru(nam: int, thang_chi: str, ngay: date, gio: int) -> dict:
    can_nam = tinh_can_nam(nam)
    chi_nam = tinh_chi_nam(nam)
    can_thang = tinh_can_thang(nam, thang_chi)
    chi_thang = thang_chi
    can_ngay = tinh_can_ngay(ngay)
    chi_ngay = tinh_chi_ngay(ngay)
    chi_gio_val = tinh_chi_gio(gio)
    can_gio = tinh_can_gio(gio, can_ngay)

    return {
        "nam":    {"can": can_nam,   "chi": chi_nam},
        "thang":  {"can": can_thang, "chi": chi_thang},
        "ngay":   {"can": can_ngay,  "chi": chi_ngay},
        "gio":    {"can": can_gio,   "chi": chi_gio_val},
        "nhat_chu": can_ngay,
    }

# ============================================================
# VƯỢNG / SUY THEO TIẾT KHÍ
# ============================================================

VUONG_SUY_TABLE = {
    # (Tiết khí / mùa): {ngũ hành: trạng thái}
    "xuan":  {"Mộc": "Vượng", "Hỏa": "Tướng", "Thủy": "Hưu",  "Kim": "Tù",   "Thổ": "Tử"},
    "ha":    {"Hỏa": "Vượng", "Thổ": "Tướng", "Mộc":  "Hưu",  "Thủy": "Tù",  "Kim": "Tử"},
    "cuoi_ha": {"Thổ": "Vượng","Kim": "Tướng", "Hỏa":  "Hưu",  "Mộc": "Tù",  "Thủy": "Tử"},
    "thu":   {"Kim": "Vượng", "Thủy": "Tướng","Thổ":  "Hưu",  "Hỏa": "Tù",   "Mộc": "Tử"},
    "dong":  {"Thủy": "Vượng","Mộc":  "Tướng","Kim":  "Hưu",  "Thổ": "Tù",   "Hỏa": "Tử"},
}

MUA_BY_TIET = {
    "Lập Xuân": "xuan", "Vũ Thủy": "xuan", "Kinh Trập": "xuan", "Xuân Phân": "xuan",
    "Thanh Minh": "xuan", "Cốc Vũ": "xuan",
    "Lập Hạ": "ha", "Tiểu Mãn": "ha", "Mang Chủng": "ha", "Hạ Chí": "ha",
    "Tiểu Thử": "ha", "Đại Thử": "ha",
    "Lập Thu": "cuoi_ha", "Xử Thử": "thu", "Bạch Lộ": "thu", "Thu Phân": "thu",
    "Hàn Lộ": "thu", "Sương Giáng": "thu",
    "Lập Đông": "dong", "Tiểu Tuyết": "dong", "Đại Tuyết": "dong", "Đông Chí": "dong",
    "Tiểu Hàn": "dong", "Đại Hàn": "dong",
}

def get_vuong_suy(nhat_chu_can: str, tiet_khi: str) -> str:
    mua = MUA_BY_TIET.get(tiet_khi, "xuan")
    nh = NGU_HANH_CAN[nhat_chu_can]
    return VUONG_SUY_TABLE[mua].get(nh, "?")

# ============================================================
# PHÂN TÍCH ĐẠI KỴ
# ============================================================

# Lục Hại (6 cặp địa chi xung khắc nặng)
LUC_HAI = {
    frozenset({"Tý", "Mùi"}), frozenset({"Sửu", "Ngọ"}),
    frozenset({"Dần", "Tỵ"}), frozenset({"Mão", "Thìn"}),
    frozenset({"Thân", "Hợi"}), frozenset({"Dậu", "Tuất"}),
}

# Lục Xung (6 cặp)
LUC_XUNG = {
    frozenset({"Tý", "Ngọ"}), frozenset({"Sửu", "Mùi"}),
    frozenset({"Dần", "Thân"}), frozenset({"Mão", "Dậu"}),
    frozenset({"Thìn", "Tuất"}), frozenset({"Tỵ", "Hợi"}),
}

# Tam Hình (3 cặp nguy hiểm)
TAM_HINH = [
    {"Dần", "Tỵ", "Thân"},
    {"Sửu", "Tuất", "Mùi"},
    {"Tý", "Mão"},
]

# Sao xấu Tử Vi theo tháng (đơn giản hóa - La Hầu/Kế Đô chu kỳ 18 năm)
def get_sao_xau_ngay(ngay: date) -> list:
    """Trả về list sao xấu Tử Vi ảnh hưởng ngày đó"""
    saos = []
    # La Hầu - Kế Đô (đối nghịch nhau, chu kỳ 18 năm, 1.5 năm/cung)
    # Tham chiếu: La Hầu vào cung Dần năm 2000
    nam_ref = 2000
    delta_nam = ngay.year - nam_ref
    delta_thang = delta_nam * 12 + ngay.month
    la_hau_idx = (delta_thang // 18) % 12
    ke_do_idx = (la_hau_idx + 6) % 12
    la_hau_chi = DIA_CHI[la_hau_idx]
    ke_do_chi = DIA_CHI[ke_do_idx]

    # Thái Tuế = chi năm hiện tại
    thai_tue_chi = DIA_CHI[(ngay.year - 4) % 12]

    # Bạch Hổ, Quan Phù, Tang Môn (vị trí theo tháng - chu kỳ 12 tháng từ Dần)
    thang_offset = (ngay.month - 1) % 12
    bach_ho_chi   = DIA_CHI[(thang_offset + 6) % 12]
    quan_phu_chi  = DIA_CHI[(thang_offset + 4) % 12]

    return {
        "La Hầu": la_hau_chi,
        "Kế Đô": ke_do_chi,
        "Thái Tuế": thai_tue_chi,
        "Bạch Hổ": bach_ho_chi,
        "Quan Phù": quan_phu_chi,
    }

def kiem_tra_xung_khi(chi1: str, chi2: str) -> list:
    """Kiểm tra xung/hại/hình giữa 2 địa chi"""
    kets = []
    pair = frozenset({chi1, chi2})
    if pair in LUC_XUNG: kets.append("Lục Xung")
    if pair in LUC_HAI:  kets.append("Lục Hại")
    for hinh in TAM_HINH:
        if chi1 in hinh and chi2 in hinh:
            kets.append("Tam Hình")
            break
    return kets

def phan_tich_ngay(ngay_check: date, gio: int, sinh_info: dict) -> dict:
    """
    Phân tích đầy đủ 1 ngày cụ thể
    sinh_info: {nam, thang_sinh (số), ngay_sinh, gio_sinh, la_so_tu_tru}
    """
    # Tứ Trụ bản mệnh
    la_so = sinh_info["la_so"]
    nhat_chu = la_so["nhat_chu"]

    # Tiết khí ngày check
    tiet_khi_ten, thang_chi_check, _ = get_tiet_khi_hien_tai(ngay_check)

    # Tứ Trụ ngày check
    tt_check = build_tu_tru(ngay_check.year, thang_chi_check, ngay_check, gio)

    vuong_suy = get_vuong_suy(nhat_chu, tiet_khi_ten)
    sao_xau = get_sao_xau_ngay(ngay_check)

    diem_xau = 0
    chi_tiet = []

    # === PHÂN TÍCH 4 TRỤ CHECK VS BẢN MỆNH ===
    tru_check_list = [
        ("Giờ",   tt_check["gio"]["can"],   tt_check["gio"]["chi"]),
        ("Ngày",  tt_check["ngay"]["can"],  tt_check["ngay"]["chi"]),
        ("Tháng", tt_check["thang"]["can"], tt_check["thang"]["chi"]),
        ("Năm",   tt_check["nam"]["can"],   tt_check["nam"]["chi"]),
    ]
    tru_ban_menh = [
        ("Giờ",   la_so["gio"]["can"],   la_so["gio"]["chi"]),
        ("Ngày",  la_so["ngay"]["can"],  la_so["ngay"]["chi"]),
        ("Tháng", la_so["thang"]["can"], la_so["thang"]["chi"]),
        ("Năm",   la_so["nam"]["can"],   la_so["nam"]["chi"]),
    ]

    tru_xau_count = 0  # đếm số trụ xấu để kiểm tra "đồng phase"

    for (ten_tru, can_c, chi_c) in tru_check_list:
        # Thập Thần Can
        thap_than = tinh_thap_than(nhat_chu, can_c)
        is_can_xau = thap_than in THAP_THAN_XAU
        if is_can_xau:
            diem_xau += 2
            chi_tiet.append(f"  • {ten_tru} Can [{can_c}] = {thap_than} ⚠️")
            tru_xau_count += 1

        # Xung/Hại/Hình địa chi vs bản mệnh
        for (ten_bm, _, chi_bm) in tru_ban_menh:
            xungs = kiem_tra_xung_khi(chi_c, chi_bm)
            for x in xungs:
                diem_xau += 3
                chi_tiet.append(f"  • {ten_tru} Chi [{chi_c}] {x} {ten_bm} Mệnh [{chi_bm}] 🔥")
                tru_xau_count += 1

        # Kiểm tra sao xấu trên địa chi trụ
        for sao, sao_chi in sao_xau.items():
            if chi_c == sao_chi:
                diem_xau += 2
                chi_tiet.append(f"  • {ten_tru} [{chi_c}] gặp sao {sao} 👿")

    # Vượng/Suy ảnh hưởng
    if vuong_suy == "Tử":
        diem_xau += 3
        chi_tiet.append(f"  • Nhật Chủ {nhat_chu} đang ở trạng thái TỬ (cực suy) 💀")
    elif vuong_suy == "Tù":
        diem_xau += 2
        chi_tiet.append(f"  • Nhật Chủ {nhat_chu} đang ở trạng thái TÙ (suy yếu) 😰")
    elif vuong_suy == "Vượng":
        diem_xau -= 1  # bù trừ
        chi_tiet.append(f"  • Nhật Chủ {nhat_chu} đang VƯỢNG - giảm bớt hung khí ✨")

    # === KIỂM TRA ĐỒNG PHASE 4 KHUNG ===
    dong_phase = False
    # Đồng phase: cả 4 trụ ngày check đều có yếu tố xấu vs bản mệnh
    if tru_xau_count >= 4:
        dong_phase = True
        diem_xau += 10
        chi_tiet.insert(0, "  🚨🚨 ĐỒNG PHASE 4 KHUNG - CỰC KỲ NGUY HIỂM! 🚨🚨")
    elif tru_xau_count == 3:
        diem_xau += 5
        chi_tiet.insert(0, "  ⚠️⚠️ ĐỒNG PHASE 3 KHUNG - RẤT NẶNG! ⚠️⚠️")

    # Phân loại mức độ
    if diem_xau >= 15 or dong_phase:
        muc_do = "🔴 CỰC KỲ NẶNG"
    elif diem_xau >= 9:
        muc_do = "🟠 RẤT NẶNG"
    elif diem_xau >= 5:
        muc_do = "🟡 TRUNG BÌNH"
    elif diem_xau >= 2:
        muc_do = "🟢 NHẸ"
    else:
        muc_do = "✅ BÌNH THƯỜNG"

    return {
        "diem_xau": diem_xau,
        "muc_do": muc_do,
        "chi_tiet": chi_tiet,
        "tiet_khi": tiet_khi_ten,
        "vuong_suy": vuong_suy,
        "tt_check": tt_check,
        "dong_phase": dong_phase,
        "tru_xau_count": tru_xau_count,
        "sao_xau": sao_xau,
    }

def lay_ngay_dai_ky_trong_thang(nam: int, thang: int, sinh_info: dict) -> list:
    """Lấy tất cả ngày đại kỵ (diem_xau >= 5) trong 1 tháng"""
    ngay_xau = []
    ngay_dau = date(nam, thang, 1)
    if thang == 12:
        ngay_cuoi = date(nam + 1, 1, 1) - timedelta(days=1)
    else:
        ngay_cuoi = date(nam, thang + 1, 1) - timedelta(days=1)

    current = ngay_dau
    while current <= ngay_cuoi:
        gio_check = datetime.now().hour if current == date.today() else 12
        kt = phan_tich_ngay(current, gio_check, sinh_info)
        if kt["diem_xau"] >= 2:  # lấy cả nhẹ để hiện đầy đủ
            ngay_xau.append({
                "ngay": current,
                "ket_qua": kt
            })
        current += timedelta(days=1)

    return ngay_xau

# ============================================================
# LƯU TRỮ THÔNG TIN NGƯỜI DÙNG (file đơn giản)
# ============================================================
import json, os, sqlite3

# Railway persistent volume mount tại /data (set trong Railway dashboard)
# Fallback về thư mục hiện tại nếu không có volume
DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", ".")
DB_PATH = os.path.join(DATA_DIR, "daiky.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            data TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def load_user_data() -> dict:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT user_id, data FROM users").fetchall()
    conn.close()
    return {row[0]: json.loads(row[1]) for row in rows}

def save_user_data(data: dict):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    for uid, udata in data.items():
        conn.execute(
            "INSERT OR REPLACE INTO users (user_id, data) VALUES (?, ?)",
            (str(uid), json.dumps(udata, ensure_ascii=False, default=str))
        )
    conn.commit()
    conn.close()

def get_sinh_info(user_id: str) -> dict | None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT data FROM users WHERE user_id=?", (str(user_id),)).fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

def set_sinh_info(user_id: str, sinh_info: dict):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO users (user_id, data) VALUES (?, ?)",
        (str(user_id), json.dumps(sinh_info, ensure_ascii=False, default=str))
    )
    conn.commit()
    conn.close()

# ============================================================
# CONVERSATION STATES
# ============================================================
NHAP_NAM_SINH, NHAP_THANG_SINH, NHAP_NGAY_SINH, NHAP_GIO_SINH = range(4)

# ============================================================
# HANDLERS
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sinh_info = get_sinh_info(str(update.effective_user.id))
    trang_thai = "✅ Đã có thông tin bản mệnh" if sinh_info else "❌ Chưa nhập ngày sinh"

    text = f"""
🌟 *BOT TỨ TRỤ ĐẠI KỴ* 🌟
━━━━━━━━━━━━━━━━━━
Kết hợp: Tứ Trụ + Tử Vi + Tiết Khí

📊 Trạng thái: {trang_thai}

📋 *DANH SÁCH LỆNH:*

🔧 `/nhapngaysinh` — Nhập/cập nhật ngày giờ sinh của mày
📅 `/ngaydaiky` — Xem ngày đại kỵ tháng này
📅 `/ngaydaiky MM` — Xem tháng cụ thể (vd: /ngaydaiky 08)
📅 `/ngaydaikynam YYYY` — Xem tổng quan cả năm
☀️ `/homnay` — Phân tích hôm nay (theo giờ thực)
⚠️ `/canhbao` — Cảnh báo ngày đại kỵ sắp tới trong tháng
📖 `/bamenh` — Xem lá số Tứ Trụ bản mệnh đầy đủ
ℹ️ `/help` — Hướng dẫn chi tiết

━━━━━━━━━━━━━━━━━━
⚡ _Dữ liệu theo thời gian thực - Tiết Khí chính xác_
"""
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_nhap_ngay_sinh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📅 *NHẬP THÔNG TIN NGÀY SINH*\n\n"
        "Bước 1/4: Nhập *NĂM SINH* (vd: 1990)",
        parse_mode="Markdown"
    )
    return NHAP_NAM_SINH

async def nhan_nam_sinh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nam = int(update.message.text.strip())
        if nam < 1900 or nam > 2010:
            await update.message.reply_text("❌ Năm sinh không hợp lệ! Nhập lại (vd: 1990):")
            return NHAP_NAM_SINH
        context.user_data["nam_sinh"] = nam
        await update.message.reply_text(
            f"✅ Năm sinh: *{nam}*\n\nBước 2/4: Nhập *THÁNG SINH* (1-12):",
            parse_mode="Markdown"
        )
        return NHAP_THANG_SINH
    except:
        await update.message.reply_text("❌ Chỉ nhập số! Ví dụ: 1990")
        return NHAP_NAM_SINH

async def nhan_thang_sinh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        thang = int(update.message.text.strip())
        if thang < 1 or thang > 12:
            await update.message.reply_text("❌ Tháng phải từ 1-12. Nhập lại:")
            return NHAP_THANG_SINH
        context.user_data["thang_sinh"] = thang
        await update.message.reply_text(
            f"✅ Tháng sinh: *{thang}*\n\nBước 3/4: Nhập *NGÀY SINH* (1-31):",
            parse_mode="Markdown"
        )
        return NHAP_NGAY_SINH
    except:
        await update.message.reply_text("❌ Chỉ nhập số! Ví dụ: 15")
        return NHAP_THANG_SINH

async def nhan_ngay_sinh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ngay_val = int(update.message.text.strip())
        nam = context.user_data["nam_sinh"]
        thang = context.user_data["thang_sinh"]
        # Kiểm tra ngày hợp lệ
        date(nam, thang, ngay_val)
        context.user_data["ngay_sinh"] = ngay_val
        await update.message.reply_text(
            f"✅ Ngày sinh: *{ngay_val}/{thang}/{nam}*\n\n"
            f"Bước 4/4: Nhập *GIỜ SINH* (0-23, giờ 24h):\n"
            f"_(Nếu không biết, nhập 12 để tính giờ Ngọ)_",
            parse_mode="Markdown"
        )
        return NHAP_GIO_SINH
    except ValueError:
        await update.message.reply_text("❌ Ngày không hợp lệ! Nhập lại:")
        return NHAP_NGAY_SINH

async def nhan_gio_sinh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        gio = int(update.message.text.strip())
        if gio < 0 or gio > 23:
            await update.message.reply_text("❌ Giờ phải từ 0-23. Nhập lại:")
            return NHAP_GIO_SINH

        nam = context.user_data["nam_sinh"]
        thang = context.user_data["thang_sinh"]
        ngay_val = context.user_data["ngay_sinh"]
        ngay_sinh_date = date(nam, thang, ngay_val)

        # Tính Tứ Trụ bản mệnh
        _, thang_chi_sinh, _ = get_tiet_khi_hien_tai(ngay_sinh_date)
        la_so = build_tu_tru(nam, thang_chi_sinh, ngay_sinh_date, gio)
        vuong_suy_sinh = get_vuong_suy(la_so["nhat_chu"],
                                        get_tiet_khi_hien_tai(ngay_sinh_date)[0])

        sinh_info = {
            "nam": nam, "thang": thang, "ngay": ngay_val, "gio": gio,
            "ngay_sinh_str": ngay_sinh_date.isoformat(),
            "la_so": la_so,
            "vuong_suy_menh": vuong_suy_sinh,
        }
        set_sinh_info(str(update.effective_user.id), sinh_info)

        chi_gio = tinh_chi_gio(gio)
        text = f"""
✅ *ĐÃ LƯU THÔNG TIN BẢN MỆNH*
━━━━━━━━━━━━━━━━━━
🗓 Ngày sinh: {ngay_val}/{thang}/{nam} — {gio}h ({chi_gio})

*📊 TỨ TRỤ BẢN MỆNH:*
┌──────┬──────┬──────┬──────┐
│ NĂM  │ THÁNG│ NGÀY │ GIỜ  │
│ {la_so['nam']['can']:^4} │ {la_so['thang']['can']:^4} │ {la_so['ngay']['can']:^4} │ {la_so['gio']['can']:^4} │
│ {la_so['nam']['chi']:^4} │ {la_so['thang']['chi']:^4} │ {la_so['ngay']['chi']:^4} │ {la_so['gio']['chi']:^4} │
└──────┴──────┴──────┴──────┘

🌟 *Nhật Chủ (Ngày):* {la_so['nhat_chu']} ({NGU_HANH_CAN[la_so['nhat_chu']]})
⚡ *Vượng/Suy lúc sinh:* {vuong_suy_sinh}

Dùng /ngaydaiky để xem ngay!
"""
        await update.message.reply_text(text, parse_mode="Markdown")
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Lỗi! Nhập lại giờ sinh (0-23):")
        return NHAP_GIO_SINH

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Đã hủy.")
    return ConversationHandler.END

async def cmd_ba_menh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sinh_info = get_sinh_info(str(update.effective_user.id))
    if not sinh_info:
        await update.message.reply_text("❌ Chưa nhập ngày sinh! Dùng /nhapngaysinh trước.")
        return

    la_so = sinh_info["la_so"]
    nhat_chu = la_so["nhat_chu"]
    nh_nhat_chu = NGU_HANH_CAN[nhat_chu]
    tiet_hien_tai, _, _ = get_tiet_khi_hien_tai(date.today())
    vs_hien_tai = get_vuong_suy(nhat_chu, tiet_hien_tai)

    # Thập Thần các trụ so với Nhật Chủ
    def tt_tru(can):
        if can == nhat_chu:
            return "Nhật Chủ"
        return tinh_thap_than(nhat_chu, can)

    sao_xau = get_sao_xau_ngay(date.today())

    text = f"""
📖 *LÁ SỐ TỨ TRỤ BẢN MỆNH*
━━━━━━━━━━━━━━━━━━
🗓 Ngày: {sinh_info['ngay']}/{sinh_info['thang']}/{sinh_info['nam']} — {sinh_info['gio']}h

┌────────┬──────┬──────┬──────┬──────┐
│        │ NĂM  │ THÁNG│ NGÀY │  GIỜ │
├────────┼──────┼──────┼──────┼──────┤
│ Thiên Can│{la_so['nam']['can']:^4}│{la_so['thang']['can']:^4}│{la_so['ngay']['can']:^4}│{la_so['gio']['can']:^4}│
│ Địa Chi │{la_so['nam']['chi']:^4}│{la_so['thang']['chi']:^4}│{la_so['ngay']['chi']:^4}│{la_so['gio']['chi']:^4}│
│ Ngũ Hành│{NGU_HANH_CAN[la_so['nam']['can']]:^4}│{NGU_HANH_CAN[la_so['thang']['can']]:^4}│{NGU_HANH_CAN[la_so['ngay']['can']]:^4}│{NGU_HANH_CAN[la_so['gio']['can']]:^4}│
│ Thập Thần│{tt_tru(la_so['nam']['can']):^6}│{tt_tru(la_so['thang']['can']):^6}│Nhật Chủ│{tt_tru(la_so['gio']['can']):^6}│
└────────┴──────┴──────┴──────┴──────┘

🌟 *Nhật Chủ:* {nhat_chu} ({nh_nhat_chu}) — {AM_DUONG_CAN[nhat_chu]}

⚡ *Vượng/Suy hiện tại* (Tiết: {tiet_hien_tai}): *{vs_hien_tai}*

🔮 *Sao hôm nay:*
  • La Hầu cung: {sao_xau['La Hầu']}
  • Kế Đô cung: {sao_xau['Kế Đô']}
  • Thái Tuế: {sao_xau['Thái Tuế']}
  • Bạch Hổ: {sao_xau['Bạch Hổ']}
"""
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_hom_nay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sinh_info = get_sinh_info(str(update.effective_user.id))
    if not sinh_info:
        await update.message.reply_text("❌ Chưa nhập ngày sinh! Dùng /nhapngaysinh trước.")
        return

    hom_nay = date.today()
    gio_hien_tai = datetime.now().hour
    kt = phan_tich_ngay(hom_nay, gio_hien_tai, sinh_info)

    tiet, _, _ = get_tiet_khi_hien_tai(hom_nay)
    tt = kt["tt_check"]
    la_so = sinh_info["la_so"]

    chi_tiet_str = "\n".join(kt["chi_tiet"]) if kt["chi_tiet"] else "  ✅ Không có yếu tố xấu đáng kể"

    text = f"""
☀️ *PHÂN TÍCH HÔM NAY*
━━━━━━━━━━━━━━━━━━
📅 {hom_nay.strftime('%d/%m/%Y')} — {gio_hien_tai}h ({tinh_chi_gio(gio_hien_tai)})
🌿 Tiết khí: {tiet}

*📊 TỨ TRỤ HÔM NAY:*
  Giờ: {tt['gio']['can']} {tt['gio']['chi']} | Ngày: {tt['ngay']['can']} {tt['ngay']['chi']}
  Tháng: {tt['thang']['can']} {tt['thang']['chi']} | Năm: {tt['nam']['can']} {tt['nam']['chi']}

*🌟 Nhật Chủ {la_so['nhat_chu']}:* {kt['vuong_suy']} trong tiết này

━━━━━━━━━━━━━━━━━━
*📊 MỨC ĐỘ ĐẠI KỴ: {kt['muc_do']}*
Điểm hung: {kt['diem_xau']} | Trụ xấu: {kt['tru_xau_count']}/4

*🔍 CHI TIẾT:*
{chi_tiet_str}

━━━━━━━━━━━━━━━━━━
*🔮 Sao hôm nay:*
  La Hầu: {kt['sao_xau']['La Hầu']} | Kế Đô: {kt['sao_xau']['Kế Đô']}
  Thái Tuế: {kt['sao_xau']['Thái Tuế']} | Bạch Hổ: {kt['sao_xau']['Bạch Hổ']}
"""
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_ngay_dai_ky(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sinh_info = get_sinh_info(str(update.effective_user.id))
    if not sinh_info:
        await update.message.reply_text("❌ Chưa nhập ngày sinh! Dùng /nhapngaysinh trước.")
        return

    # Parse tháng từ tham số
    hom_nay = date.today()
    try:
        if context.args and len(context.args) > 0:
            thang_check = int(context.args[0])
            nam_check = hom_nay.year
        else:
            thang_check = hom_nay.month
            nam_check = hom_nay.year
    except:
        thang_check = hom_nay.month
        nam_check = hom_nay.year

    await update.message.reply_text(f"⏳ Đang tính ngày đại kỵ tháng {thang_check}/{nam_check}...")

    ngay_xau_list = lay_ngay_dai_ky_trong_thang(nam_check, thang_check, sinh_info)

    if not ngay_xau_list:
        await update.message.reply_text(f"✅ Tháng {thang_check}/{nam_check} không có ngày xấu đáng kể!")
        return

    lines = [f"📅 *NGÀY ĐẠI KỴ THÁNG {thang_check}/{nam_check}*"]
    lines.append("━━━━━━━━━━━━━━━━━━")

    hom_nay_str = hom_nay.isoformat()
    for item in ngay_xau_list:
        ng = item["ngay"]
        kt = item["ket_qua"]
        marker = " 👈 HÔM NAY" if ng.isoformat() == hom_nay_str else ""
        canh_bao = ""
        days_until = (ng - hom_nay).days
        if 0 < days_until <= 3:
            canh_bao = f" ⚠️ CÒN {days_until} NGÀY"

        dong_phase_str = ""
        if kt["dong_phase"]:
            dong_phase_str = "\n    🚨 ĐỒNG PHASE 4 KHUNG"
        elif kt["tru_xau_count"] >= 3:
            dong_phase_str = "\n    ⚠️ ĐỒNG PHASE 3 KHUNG"

        lines.append(
            f"\n📆 *{ng.strftime('%d/%m/%Y')}* ({ng.strftime('%A')}){marker}{canh_bao}\n"
            f"   {kt['muc_do']} | Điểm: {kt['diem_xau']} | Trụ xấu: {kt['tru_xau_count']}/4\n"
            f"   Tiết: {kt['tiet_khi']} | Nhật Chủ: {kt['vuong_suy']}{dong_phase_str}"
        )

    lines.append("\n━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 Tổng: {len(ngay_xau_list)} ngày cần chú ý")
    lines.append("🔴 ≥15đ | 🟠 ≥9đ | 🟡 ≥5đ | 🟢 ≥2đ")

    text = "\n".join(lines)
    # Chia nhỏ nếu quá dài
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_ngay_dai_ky_nam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sinh_info = get_sinh_info(str(update.effective_user.id))
    if not sinh_info:
        await update.message.reply_text("❌ Chưa nhập ngày sinh! Dùng /nhapngaysinh trước.")
        return

    hom_nay = date.today()
    try:
        nam_check = int(context.args[0]) if context.args else hom_nay.year
    except:
        nam_check = hom_nay.year

    await update.message.reply_text(f"⏳ Đang tính tổng quan năm {nam_check} (12 tháng)...")

    lines = [f"📅 *TỔNG QUAN ĐẠI KỴ NĂM {nam_check}*"]
    lines.append("━━━━━━━━━━━━━━━━━━")

    tong_ngay_xau = 0
    thang_nguy_hiem = []

    for thang in range(1, 13):
        ngay_xau_list = lay_ngay_dai_ky_trong_thang(nam_check, thang, sinh_info)
        ngay_nang = [x for x in ngay_xau_list if x["ket_qua"]["diem_xau"] >= 9]
        ngay_cc = [x for x in ngay_xau_list if x["ket_qua"]["diem_xau"] >= 5]
        ngay_dong = [x for x in ngay_xau_list if x["ket_qua"]["dong_phase"]]
        tong_ngay_xau += len(ngay_xau_list)

        icon = "🔴" if ngay_nang else ("🟠" if ngay_cc else "🟢")
        dong_str = f" 🚨×{len(ngay_dong)}" if ngay_dong else ""
        lines.append(
            f"{icon} Tháng {thang:02d}: {len(ngay_xau_list)} ngày xấu "
            f"({len(ngay_nang)} nặng){dong_str}"
        )
        if ngay_nang:
            thang_nguy_hiem.append(thang)

    lines.append("\n━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 Tổng: {tong_ngay_xau} ngày cần chú ý")
    if thang_nguy_hiem:
        lines.append(f"🔴 Tháng cần cảnh giác: {', '.join(str(t) for t in thang_nguy_hiem)}")
    lines.append("\n_Dùng /ngaydaiky MM để xem chi tiết từng tháng_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_canh_bao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sinh_info = get_sinh_info(str(update.effective_user.id))
    if not sinh_info:
        await update.message.reply_text("❌ Chưa nhập ngày sinh! Dùng /nhapngaysinh trước.")
        return

    hom_nay = date.today()
    ngay_xau_list = lay_ngay_dai_ky_trong_thang(hom_nay.year, hom_nay.month, sinh_info)

    # Lọc ngày trong tương lai (trong tháng này) có diem >= 5
    sap_toi = [
        x for x in ngay_xau_list
        if x["ngay"] >= hom_nay and x["ket_qua"]["diem_xau"] >= 5
    ]

    if not sap_toi:
        await update.message.reply_text(
            f"✅ Tháng {hom_nay.month}/{hom_nay.year} không có ngày đại kỵ nặng sắp tới!"
        )
        return

    lines = [f"⚠️ *CẢNH BÁO ĐẠI KỴ THÁNG {hom_nay.month}/{hom_nay.year}*"]
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append(f"🕐 Hôm nay: {hom_nay.strftime('%d/%m/%Y')}\n")

    for item in sap_toi:
        ng = item["ngay"]
        kt = item["ket_qua"]
        days_until = (ng - hom_nay).days
        if days_until == 0:
            countdown = "⚡ HÔM NAY"
        elif days_until == 1:
            countdown = "🔔 NGÀY MAI"
        else:
            countdown = f"📅 Còn {days_until} ngày"

        dong_str = ""
        if kt["dong_phase"]:
            dong_str = "\n   🚨🚨 ĐỒNG PHASE 4 KHUNG"
        elif kt["tru_xau_count"] >= 3:
            dong_str = "\n   ⚠️ ĐỒNG PHASE 3 KHUNG"

        lines.append(
            f"*{ng.strftime('%d/%m/%Y')}* — {countdown}\n"
            f"  {kt['muc_do']} | Điểm hung: {kt['diem_xau']}\n"
            f"  Nhật Chủ: {kt['vuong_suy']} | Tiết: {kt['tiet_khi']}{dong_str}\n"
        )

    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("💡 _Tránh quyết định lớn, giao dịch, phẫu thuật trong ngày xấu_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
ℹ️ *HƯỚNG DẪN CHI TIẾT*
━━━━━━━━━━━━━━━━━━

*🔢 THANG ĐIỂM ĐẠI KỴ:*
🔴 ≥15 điểm = Cực kỳ nặng
🟠 9-14 điểm = Rất nặng
🟡 5-8 điểm = Trung bình
🟢 2-4 điểm = Nhẹ
✅ 0-1 điểm = Bình thường

*🚨 ĐỒNG PHASE:*
• 4 khung (Giờ+Ngày+Tháng+Năm cùng xấu) = +10 điểm = Cực nguy
• 3 khung = +5 điểm = Rất nặng

*📊 NGUỒN TÍNH ĐIỂM:*
• Thập Thần xấu (Thất Sát, Thương Quan, Kiếp Tài): +2đ/trụ
• Lục Xung/Lục Hại/Tam Hình địa chi: +3đ/cặp
• Sao xấu Tử Vi (La Hầu, Kế Đô, Thái Tuế, Bạch Hổ): +2đ
• Nhật Chủ Tử: +3đ | Tù: +2đ
• Nhật Chủ Vượng: -1đ (giảm hung khí)

*⚡ TIẾT KHÍ & VƯỢNG/SUY:*
Vượng > Tướng > Hưu > Tù > Tử
Nhật Chủ Vượng/Tướng = bản thân mạnh = chịu đựng tốt hơn

*📅 CÁCH DÙNG:*
/ngaydaiky — Tháng hiện tại
/ngaydaiky 8 — Tháng 8
/ngaydaikynam 2025 — Cả năm 2025
"""
    await update.message.reply_text(text, parse_mode="Markdown")

# ============================================================
# MAIN
# ============================================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler nhập ngày sinh
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("nhapngaysinh", cmd_nhap_ngay_sinh)],
        states={
            NHAP_NAM_SINH:   [MessageHandler(filters.TEXT & ~filters.COMMAND, nhan_nam_sinh)],
            NHAP_THANG_SINH: [MessageHandler(filters.TEXT & ~filters.COMMAND, nhan_thang_sinh)],
            NHAP_NGAY_SINH:  [MessageHandler(filters.TEXT & ~filters.COMMAND, nhan_ngay_sinh)],
            NHAP_GIO_SINH:   [MessageHandler(filters.TEXT & ~filters.COMMAND, nhan_gio_sinh)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start",         cmd_start))
    app.add_handler(CommandHandler("help",          cmd_help))
    app.add_handler(CommandHandler("bamenh",        cmd_ba_menh))
    app.add_handler(CommandHandler("homnay",        cmd_hom_nay))
    app.add_handler(CommandHandler("ngaydaiky",     cmd_ngay_dai_ky))
    app.add_handler(CommandHandler("ngaydaikynam",  cmd_ngay_dai_ky_nam))
    app.add_handler(CommandHandler("canhbao",       cmd_canh_bao))

    logger.info("Bot đang chạy...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
