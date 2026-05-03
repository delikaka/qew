import logging
import os
import json
import sqlite3
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

TZ_VN = ZoneInfo("Asia/Ho_Chi_Minh")  # UTC+7

def now_vn() -> datetime:
    """Trả về datetime hiện tại theo giờ Việt Nam (UTC+7)."""
    return datetime.now(TZ_VN)

def today_vn() -> date:
    """Trả về ngày hiện tại theo giờ Việt Nam."""
    return now_vn().date()
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)

# ============================================================
# CONFIG & LOGGING
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# TOÁN HỌC TỨ TRỤ NÂNG CAO (CHUYÊN GIA)
# ============================================================
THIEN_CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
DIA_CHI   = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]

NGU_HANH = {
    "Giáp":"Mộc","Ất":"Mộc","Bính":"Hỏa","Đinh":"Hỏa","Mậu":"Thổ","Kỷ":"Thổ","Canh":"Kim","Tân":"Kim","Nhâm":"Thủy","Quý":"Thủy",
    "Dần":"Mộc","Mão":"Mộc","Tỵ":"Hỏa","Ngọ":"Hỏa","Thân":"Kim","Dậu":"Kim","Hợi":"Thủy","Tý":"Thủy","Sửu":"Thổ","Thìn":"Thổ","Mùi":"Thổ","Tuất":"Thổ"
}

AM_DUONG_CAN = {"Giáp":"Dương","Ất":"Âm","Bính":"Dương","Đinh":"Âm","Mậu":"Dương","Kỷ":"Âm","Canh":"Dương","Tân":"Âm","Nhâm":"Dương","Quý":"Âm"}
TUONG_SINH = {"Mộc":"Hỏa","Hỏa":"Thổ","Thổ":"Kim","Kim":"Thủy","Thủy":"Mộc"}
TUONG_KHAC = {"Mộc":"Thổ","Thổ":"Thủy","Thủy":"Hỏa","Hỏa":"Kim","Kim":"Mộc"}

LUC_HOP = {frozenset({"Tý", "Sửu"}), frozenset({"Dần", "Hợi"}), frozenset({"Mão", "Tuất"}), frozenset({"Thìn", "Dậu"}), frozenset({"Tỵ", "Thân"}), frozenset({"Ngọ", "Mùi"})}
LUC_XUNG = {frozenset({"Tý", "Ngọ"}), frozenset({"Sửu", "Mùi"}), frozenset({"Dần", "Thân"}), frozenset({"Mão", "Dậu"}), frozenset({"Thìn", "Tuất"}), frozenset({"Tỵ", "Hợi"})}

# ============================================================
# BỔ SUNG: MA TRẬN TÀNG CAN (TỶ LỆ NĂNG LƯỢNG ẨN)
# ============================================================
TANG_CAN = {
    "Tý": {"Quý": 1.0},
    "Sửu": {"Kỷ": 0.6, "Quý": 0.3, "Tân": 0.1},
    "Dần": {"Giáp": 0.7, "Bính": 0.2, "Mậu": 0.1},
    "Mão": {"Ất": 1.0},
    "Thìn": {"Mậu": 0.6, "Ất": 0.3, "Quý": 0.1},
    "Tỵ": {"Bính": 0.7, "Canh": 0.2, "Mậu": 0.1},
    "Ngọ": {"Đinh": 0.6, "Kỷ": 0.3, "Giáp": 0.1},  # Fix #4: Bổ sung Giáp (Mộc ẩn trong Ngọ), chuẩn hóa tỷ lệ tổng = 1.0
    "Mùi": {"Kỷ": 0.6, "Đinh": 0.3, "Ất": 0.1},
    "Thân": {"Canh": 0.7, "Nhâm": 0.2, "Mậu": 0.1},
    "Dậu": {"Tân": 1.0},
    "Tuất": {"Mậu": 0.6, "Đinh": 0.3, "Tân": 0.1},
    "Hợi": {"Nhâm": 0.7, "Giáp": 0.3}
}
# ------------------------------------------------------------
# LÝ THUYẾT VÒNG TRƯỜNG SINH (GIỮ NGUYÊN)
# ------------------------------------------------------------
TRUONG_SINH_SEQ = ["Trường Sinh", "Mộc Dục", "Quan Đới", "Lâm Quan", "Đế Vượng", "Suy", "Bệnh", "Tử", "Mộ", "Tuyệt", "Thai", "Dưỡng"]
CAN_TS_START = {
    "Giáp":("Hợi", 1), "Ất":("Ngọ", -1), "Bính":("Dần", 1), "Đinh":("Dậu", -1), "Mậu":("Dần", 1), 
    "Kỷ":("Dậu", -1), "Canh":("Tỵ", 1), "Tân":("Tý", -1), "Nhâm":("Thân", 1), "Quý":("Mão", -1)
}
TS_HE_SO = {
    "Đế Vượng": 1.4, "Lâm Quan": 1.3, "Trường Sinh": 1.2, "Quan Đới": 1.1, "Mộc Dục": 1.0, 
    "Dưỡng": 1.0, "Thai": 0.9, "Suy": 0.9, "Mộ": 0.8, "Bệnh": 0.7, "Tử": 0.5, "Tuyệt": 0.4
}

def get_truong_sinh(can, chi):
    if can not in CAN_TS_START or chi not in DIA_CHI: return "N/A"
    start_chi, step = CAN_TS_START[can]
    idx_start = DIA_CHI.index(start_chi)
    idx_target = DIA_CHI.index(chi)
    dist = (idx_target - idx_start) * step
    return TRUONG_SINH_SEQ[dist % 12]

# ------------------------------------------------------------
# HÀM TÍNH TOÁN LOGIC (ĐÃ SỬA LỖI KIẾN THỨC)
# ------------------------------------------------------------
def tinh_thap_than(nhat_chu, can_check):
    if nhat_chu not in NGU_HANH or can_check not in NGU_HANH: return "N/A"
    nh_chu, nh_check = NGU_HANH[nhat_chu], NGU_HANH[can_check]
    cung_ad = (AM_DUONG_CAN[nhat_chu] == AM_DUONG_CAN[can_check])
    # Đã sửa: Cùng Âm Dương là Tỷ Kiên, khác là Kiếp Tài[cite: 2]
    if nh_check == nh_chu: return "Tỷ Kiên" if cung_ad else "Kiếp Tài"
    if TUONG_SINH.get(nh_check) == nh_chu: return "Thiên Ấn" if cung_ad else "Chính Ấn"
    if TUONG_SINH.get(nh_chu) == nh_check: return "Thực Thần" if cung_ad else "Thương Quan"
    if TUONG_KHAC.get(nh_chu) == nh_check: return "Thiên Tài" if cung_ad else "Chính Tài"
    if TUONG_KHAC.get(nh_check) == nh_chu: return "Thất Sát" if cung_ad else "Chính Quan"
    return "N/A"

def get_tiet_khi(ngay: date):
    TK = [(1,6,"Tiểu Hàn"),(2,4,"Lập Xuân"),(3,6,"Kinh Trập"),(4,5,"Thanh Minh"),(5,6,"Lập Hạ"),(6,6,"Mang Chủng"),(7,7,"Tiểu Thử"),(8,7,"Lập Thu"),(9,8,"Bạch Lộ"),(10,8,"Hàn Lộ"),(11,7,"Lập Đông"),(12,7,"Đại Tuyết")]
    t, c = "Đông Chí", "Tý"
    for m, d, name in reversed(TK):
        try:
            if ngay >= date(ngay.year, m, d): t = name; break
        except ValueError: continue
    MAP = {"Lập Xuân":"Dần","Kinh Trập":"Mão","Thanh Minh":"Thìn","Lập Hạ":"Tỵ","Mang Chủng":"Ngọ","Tiểu Thử":"Mùi","Lập Thu":"Thân","Bạch Lộ":"Dậu","Hàn Lộ":"Tuất","Lập Đông":"Hợi","Đại Tuyết":"Tý","Tiểu Hàn":"Sửu"}
    return t, MAP.get(t, "Tý")

NGU_HO_DUN = {0: 2, 1: 4, 2: 6, 3: 8, 4: 0}  

def get_can_thang(can_nam: str, chi_thang: str) -> str:
    idx_can_nam = THIEN_CAN.index(can_nam)
    idx_chi_thang = DIA_CHI.index(chi_thang)
    start_can_idx = NGU_HO_DUN[idx_can_nam % 5]
    chi_offset = (idx_chi_thang - 2) % 12 
    can_thang_idx = (start_can_idx + chi_offset) % 10
    return THIEN_CAN[can_thang_idx]

def build_tu_tru(nam, tc, ngay, gio):
    ngay_tinh_nhat_chu = ngay
    if gio >= 23:
        ngay_tinh_nhat_chu = ngay + timedelta(days=1)

    cn = THIEN_CAN[(nam - 4) % 10]
    chin = DIA_CHI[(nam - 4) % 12]

    d_diff = (ngay_tinh_nhat_chu - date(1900, 1, 1)).days
    idx_can_ngay = (d_diff + 0) % 10  
    idx_chi_ngay = (d_diff + 10) % 12 
    cng = THIEN_CAN[idx_can_ngay]
    ching = DIA_CHI[idx_chi_ngay]

    cthang = get_can_thang(cn, tc) 

    idx_gio = (gio + 1) // 2
    if idx_gio == 12: idx_gio = 0 
    
    start_can_gio_idx = (idx_can_ngay % 5) * 2
    cg = THIEN_CAN[(start_can_gio_idx + idx_gio) % 10]
    chig = DIA_CHI[idx_gio]

    return {
        "nam": {"can": cn, "chi": chin},
        "thang": {"can": cthang, "chi": tc},
        "ngay": {"can": cng, "chi": ching},
        "gio": {"can": cg, "chi": chig},
        "nhat_chu": cng
    }

# ------------------------------------------------------------
# THUẬT TOÁN ĐỊNH LƯỢNG NĂNG LƯỢNG (KHÔI PHỤC TỪ CL4)
# ------------------------------------------------------------
TRONG_SO_NL = {
    "can_nam": 1.0, "chi_nam": 1.5,
    "can_thang": 1.0, "chi_thang": 3.5, 
    "can_ngay": 0.0, "chi_ngay": 1.5, 
    "can_gio": 1.0, "chi_gio": 1.5
}

def dinh_luong_nang_luong(ls):
    nc_hanh = NGU_HANH[ls["nhat_chu"]]
    hanh_sinh_nc = next((k for k, v in TUONG_SINH.items() if v == nc_hanh), None)
    
    diem_tuong_tro = 0.0
    diem_that_tho = 0.0
    chi_tiet_hanh = {"Mộc": 0.0, "Hỏa": 0.0, "Thổ": 0.0, "Kim": 0.0, "Thủy": 0.0}

    # 1. Xử lý Thiên Can (Lộ diện: Nhận 100% năng lượng của hành đó)
    cac_can = {
        "can_nam": ls["nam"]["can"],
        "can_thang": ls["thang"]["can"],
        "can_ngay": ls["ngay"]["can"],
        "can_gio": ls["gio"]["can"]
    }
    for vitri, can in cac_can.items():
        if vitri in TRONG_SO_NL and TRONG_SO_NL[vitri] > 0:
            hanh = NGU_HANH.get(can)
            if hanh:
                chi_tiet_hanh[hanh] += TRONG_SO_NL[vitri]

    # 2. Xử lý Địa Chi (Ẩn tàng: Phân bổ điểm năng lượng theo tỷ lệ % Tàng Can)
    cac_chi = {
        "chi_nam": ls["nam"]["chi"],
        "chi_thang": ls["thang"]["chi"],
        "chi_ngay": ls["ngay"]["chi"],
        "chi_gio": ls["gio"]["chi"]
    }
    for vitri, chi in cac_chi.items():
        if vitri in TRONG_SO_NL and TRONG_SO_NL[vitri] > 0:
            tong_diem_chi = TRONG_SO_NL[vitri]
            tang_can_dict = TANG_CAN.get(chi, {})
            for can_an, ti_le in tang_can_dict.items():
                hanh_an = NGU_HANH.get(can_an)
                if hanh_an:
                    chi_tiet_hanh[hanh_an] += tong_diem_chi * ti_le

    # 3. Tính toán Thân Vượng/Nhược dựa trên chi_tiet_hanh đã bóc tách siêu chuẩn
    for hanh, diem in chi_tiet_hanh.items():
        if hanh == nc_hanh or hanh == hanh_sinh_nc:
            diem_tuong_tro += diem
        else:
            diem_that_tho += diem

    # Làm tròn để tránh lỗi số học thập phân (floating point)
    return round(diem_tuong_tro, 2), round(diem_that_tho, 2), {k: round(v, 2) for k, v in chi_tiet_hanh.items()}

def xac_dinh_dung_than(ls):
    nc_hanh = NGU_HANH[ls["nhat_chu"]]
    hanh_sinh_nc = next((k for k, v in TUONG_SINH.items() if v == nc_hanh), None) 
    hanh_nc_sinh = TUONG_SINH.get(nc_hanh) 
    hanh_khac_nc = next((k for k, v in TUONG_KHAC.items() if v == nc_hanh), None) 
    hanh_nc_khac = TUONG_KHAC.get(nc_hanh) 
    diem_tuong_tro, diem_that_tho, chi_tiet_hanh = dinh_luong_nang_luong(ls)

    # Thuật toán Decision Tree chuẩn từ cl4
    # Fix #12: Ngưỡng Tòng 2.0 (~18% tổng trọng số 11.0) — tính từ TRONG_SO_NL
    # 1.5 cũ (~13%) quá thấp; 2.0 phản ánh đúng mức gần như không có lực đỡ
    if diem_tuong_tro <= 2.0:
        hanh_manh_nhat = max(chi_tiet_hanh, key=chi_tiet_hanh.get)
        return [hanh_manh_nhat, TUONG_SINH.get(hanh_manh_nhat)], "Tòng Nhược (Đặc Biệt)"
    if diem_that_tho <= 2.0:
        return [hanh_nc_sinh, nc_hanh], "Tòng Cường (Đặc Biệt)"
    if diem_tuong_tro >= 5.5:
        dung_than = [h for h in [hanh_nc_khac, hanh_nc_sinh, hanh_khac_nc] if h is not None]
        return dung_than, "Vượng"
    else:
        dung_than = [h for h in [hanh_sinh_nc, nc_hanh] if h is not None]
        return dung_than, "Nhược"

# ------------------------------------------------------------
# LOGIC BÌNH GIẢI (HỢP NHẤT)
# ------------------------------------------------------------
def get_season_multiplier(month_chi, day_chi):
    # Fix #2: Hàm này dùng Tam Hội (3 chi liên tiếp) để tính hệ số xung theo mùa.
    # Phân biệt với tinh_suc_manh_nhat_chu dùng Tam Hợp/Trường Sinh — hai mục đích khác nhau.
    day_nh = NGU_HANH.get(day_chi)
    seasons = {"Mộc":["Dần","Mão","Thìn"],"Hỏa":["Tỵ","Ngọ","Mùi"],"Kim":["Thân","Dậu","Tuất"],"Thủy":["Hợi","Tý","Sửu"]}
    vuong_element = next((k for k, v in seasons.items() if month_chi in v), None)
    return 1.3 if day_nh == vuong_element else 1.0

def tinh_suc_manh_nhat_chu(ls):
    nh_chu = NGU_HANH[ls["nhat_chu"]]
    chi_thang = ls["thang"]["chi"]
    mua_vuong = {"Mộc":["Dần","Mão","Hợi"],"Hỏa":["Tỵ","Ngọ","Dần"],"Thổ":["Sửu","Thìn","Mùi","Tuất"],"Kim":["Thân","Dậu","Sửu"],"Thủy":["Tý","Hợi","Dậu"]}
    return 1.2 if chi_thang in mua_vuong.get(nh_chu, []) else 0.8

def get_dich_ma(chi):
    ma_map = {"Thân":"Dần","Tý":"Dần","Thìn":"Dần","Tỵ":"Hợi","Dậu":"Hợi","Sửu":"Hợi","Dần":"Thân","Ngọ":"Thân","Tuất":"Thân","Hợi":"Tỵ","Mão":"Tỵ","Mùi":"Tỵ"}
    return ma_map.get(chi)

def phan_tich_chuyen_gia_3_mon(ngay_check: date, ls: dict):
    _, month_chi = get_tiet_khi(ngay_check)
    tt_now = build_tu_tru(ngay_check.year, month_chi, ngay_check, 12)
    thap_than = tinh_thap_than(ls["nhat_chu"], tt_now["ngay"]["can"])
    suc_manh = tinh_suc_manh_nhat_chu(ls)
    chi_ngay = tt_now["ngay"]["chi"]
    ngay_hanh = NGU_HANH.get(chi_ngay)
    
    dung_than, _ = xac_dinh_dung_than(ls)
    ts_state = get_truong_sinh(ls["nhat_chu"], chi_ngay)
    he_so_ts = TS_HE_SO.get(ts_state, 1.0)
    
    s_trade = 5.0 + (3.5 * suc_manh if thap_than in ["Thiên Tài", "Chính Tài"] else -3.0 if thap_than == "Kiếp Tài" else 0)
    if frozenset({chi_ngay, ls["ngay"]["chi"]}) in LUC_XUNG: s_trade -= 2.5
    s_study = 5.0 + (3.0 if thap_than in ["Chính Ấn", "Thiên Ấn"] else 0) + (1.0 if NGU_HANH[chi_ngay] in ["Thủy", "Mộc"] else 0)
    s_move = 5.0 + (4.5 if chi_ngay in [get_dich_ma(ls["nam"]["chi"]), get_dich_ma(ls["ngay"]["chi"])] else 0)
    if frozenset({chi_ngay, ls["ngay"]["chi"]}) in LUC_XUNG: s_move -= 4.0

    # Sức khỏe: dựa vào Trường Sinh state (thân thể khí lực) + Thủy/Mộc (tạng phủ)
    # + Xung Nhật Chủ trực tiếp (thân thể bất an)
    s_health = 5.0
    if ts_state in ["Đế Vượng", "Lâm Quan", "Trường Sinh"]: s_health += 3.0
    elif ts_state in ["Tuyệt", "Tử", "Bệnh"]: s_health -= 3.0
    elif ts_state in ["Suy", "Mộ"]: s_health -= 1.5
    if NGU_HANH[chi_ngay] in ["Thủy", "Mộc"]: s_health += 1.0
    if frozenset({chi_ngay, ls["ngay"]["chi"]}) in LUC_XUNG: s_health -= 2.5

    # Công việc: Quan tinh (Chính Quan/Thất Sát) = áp lực/cơ hội từ tổ chức
    # Thực Thần/Thương Quan = năng lực thực thi
    # Xung Trụ Tháng = môi trường làm việc bất ổn
    s_work = 5.0
    if thap_than in ["Chính Quan"]: s_work += 3.0
    elif thap_than in ["Thất Sát"]: s_work += 1.5  # áp lực nhưng vẫn có cơ hội nếu thân vượng
    elif thap_than in ["Thực Thần"]: s_work += 2.5
    elif thap_than in ["Thương Quan"]: s_work += 1.0
    elif thap_than in ["Kiếp Tài"]: s_work -= 2.0  # cạnh tranh, tiểu nhân
    if frozenset({chi_ngay, ls["thang"]["chi"]}) in LUC_XUNG: s_work -= 3.0  # xung trụ tháng = công việc chao đảo

    if ngay_hanh in dung_than:
        s_trade += 2.0; s_study += 2.0; s_move += 2.0
        s_health += 1.5; s_work += 2.0
    else:
        s_trade -= 1.5; s_study -= 1.0; s_move -= 1.5
        s_health -= 1.0; s_work -= 1.5

    s_trade *= he_so_ts; s_study *= he_so_ts; s_move *= he_so_ts
    s_health *= he_so_ts; s_work *= he_so_ts
    return {k: round(max(0, min(10, v)), 1) for k, v in {
        "trading": s_trade, "study": s_study, "move": s_move,
        "health": s_health, "work": s_work
    }.items()}

def phan_tich_ngay_sau(ngay_check: date, gio: int, sinh_info: dict):
    ls = sinh_info["la_so"]
    nhat_chu_can = ls["nhat_chu"]
    _, month_chi = get_tiet_khi(ngay_check)
    tt_now = build_tu_tru(ngay_check.year, month_chi, ngay_check, gio)
    
    diem_hung = 0.0; chi_tiet = []
    check_list = [("Ngày", tt_now["ngay"]["chi"], 1.5), ("Năm", tt_now["nam"]["chi"], 1.2)]
    targets = [("Nhật Chủ", ls["ngay"]["chi"], 8), ("Trụ Năm", ls["nam"]["chi"], 5)]

    dung_than, _ = xac_dinh_dung_than(ls)
    ngay_hanh = NGU_HANH.get(tt_now["ngay"]["chi"])
    ts_state = get_truong_sinh(nhat_chu_can, tt_now["ngay"]["chi"])
    
    if ngay_hanh in dung_than:
        chi_tiet.append(f"✨ Hành {ngay_hanh} là DỤNG THẦN (Đỡ được hung hiểm)")
        diem_hung -= 3.0
    else:
        chi_tiet.append(f"⚠️ Hành {ngay_hanh} là KỴ THẦN (Cẩn thận rủi ro)")
        diem_hung += 2.0
        
    chi_tiet.append(f"🔋 Năng lượng: {ts_state}")
    if ts_state in ["Tuyệt", "Tử", "Bệnh"]:
        diem_hung += 3.0
        chi_tiet.append(f"📉 Mệnh rơi vào cung {ts_state}, khí lực suy kiệt.")
    elif ts_state in ["Đế Vượng", "Lâm Quan", "Trường Sinh"]:
        diem_hung -= 2.0

    # Fix #11: Hợp giải xung phải check chi ngày hiện tại có Lục Hợp với chi nào trong LÁ SỐ GỐC.
    # Logic cũ tự check trong check_list → gần như không bao giờ đúng.
    all_la_so_chi = {ls["nam"]["chi"], ls["thang"]["chi"], ls["ngay"]["chi"], ls["gio"]["chi"]}
    for n_now, c_now, p_coeff in check_list:
        for n_tar, c_tar, weight in targets:
            if frozenset({c_now, c_tar}) in LUC_XUNG:
                current_score = weight * p_coeff * get_season_multiplier(month_chi, c_now)
                is_saved = any(frozenset({c_now, chi_gs}) in LUC_HOP for chi_gs in all_la_so_chi)
                if is_saved: chi_tiet.append(f"🛡️ {n_now} Xung {n_tar} nhưng có Hợp giải từ lá số gốc")
                else:
                    diem_hung += current_score
                    chi_tiet.append(f"🔥 {n_now} Xung {n_tar} ({c_now}-{c_tar})")

    if tinh_thap_than(nhat_chu_can, tt_now["ngay"]["can"]) == "Thất Sát":
        diem_hung += 5; chi_tiet.append(f"⚔️ Thiên Can phạm Thất Sát")

    if diem_hung >= 12: muc = "🔴 CỰC NẶNG"
    elif diem_hung >= 7: muc = "🟠 RẤT NẶNG"
    elif diem_hung >= 3: muc = "🟡 TRUNG BÌNH"
    else: muc = "✅ BÌNH THƯỜNG"
    return {"diem": round(diem_hung, 1), "muc": muc, "detail": chi_tiet, "is_dangerous": diem_hung >= 7}

# ============================================================
# DB & BOT HANDLERS (GIỮ NGUYÊN TỪ CL5)
# ============================================================
DB_PATH = "daiky.db"
def init_db():
    conn = sqlite3.connect(DB_PATH); conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, data TEXT)"); conn.commit(); conn.close()
def get_data(uid):
    conn = sqlite3.connect(DB_PATH); r = conn.execute("SELECT data FROM users WHERE user_id=?", (str(uid),)).fetchone(); conn.close()
    return json.loads(r[0]) if r else None

NHAP_N, NHAP_T, NHAP_D, NHAP_G = range(4)

async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    txt = "🌟 *BOT ĐẠI KỴ - MA TRẬN TỨ TRỤ*\n\n📜 *MENU LỆNH:*\n• /nhapngaysinh - Thiết lập lá số\n• /ngaydaiky - Danh sách ngày xấu tháng này\n• /canhbao - Quét chi tiết 30 ngày tới\n• /homnay - Khí vận giờ hiện tại"
    await u.message.reply_text(txt, parse_mode="Markdown")

async def nhap_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("Nhập NĂM SINH (vd: 1990):"); return NHAP_N

async def nhap_n(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        c.user_data["n"] = int(u.message.text); await u.message.reply_text("Nhập THÁNG SINH (1-12):"); return NHAP_T
    except ValueError: await u.message.reply_text("Nhập số hộ tao cái! Nhập lại NĂM:"); return NHAP_N

async def nhap_t(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        val = int(u.message.text)
        if 1 <= val <= 12: c.user_data["t"] = val; await u.message.reply_text("Nhập NGÀY SINH (1-31):"); return NHAP_D
        await u.message.reply_text("Tháng gì lạ vậy? Nhập lại từ 1 đến 12:"); return NHAP_T
    except ValueError: await u.message.reply_text("Đừng gõ chữ! Hãy nhập THÁNG bằng số (1-12):"); return NHAP_T

async def nhap_d(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        val = int(u.message.text)
        if 1 <= val <= 31: c.user_data["d"] = val; await u.message.reply_text("Nhập GIỜ SINH (0-23):"); return NHAP_G
        await u.message.reply_text("Ngày không hợp lệ! Nhập lại từ 1 đến 31:"); return NHAP_D
    except ValueError: await u.message.reply_text("Đừng gõ chữ! Hãy nhập NGÀY bằng số (1-31):"); return NHAP_D

async def nhap_g(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        g = int(u.message.text)
        if not (0 <= g <= 23): await u.message.reply_text("Giờ sinh phải từ 0 đến 23. Nhập lại:"); return NHAP_G
        n, t, d = c.user_data["n"], c.user_data["t"], c.user_data["d"]
        try:
            ngay_sinh = date(n, t, d)
        except ValueError:
            await u.message.reply_text(f"❌ Lỗi: Ngày {d}/{t}/{n} không tồn tại. Gõ /nhapngaysinh lại!"); return ConversationHandler.END
        _, tc = get_tiet_khi(ngay_sinh); ls = build_tu_tru(n, tc, ngay_sinh, g)
        conn = sqlite3.connect(DB_PATH); conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (str(u.effective_user.id), json.dumps({"n":n,"t":t,"d":d,"g":g,"la_so":ls}))); conn.commit(); conn.close()
        await u.message.reply_text("✅ Xong! Cấu hình thành công.Gõ /canhbao & /ngaydaiky & /homnay để xem hạn nhé."); return ConversationHandler.END
    except ValueError: await u.message.reply_text("Lại gõ chữ à? Hãy nhập GIỜ bằng số (0-23):"); return NHAP_G

async def cmd_canh_bao(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: await u.message.reply_text("Mày chưa nhập thông tin! Gõ /nhapngaysinh đi đã."); return
    today = today_vn(); warns = []
    for i in range(1, 31):
        d = today + timedelta(days=i); res = phan_tich_ngay_sau(d, 12, info)
        if res["is_dangerous"]: warns.append(f"📅 *{d.strftime('%d/%m')}* ({res['diem']}đ): {res['muc']}\n   ↳ {', '.join(res['detail'])}")
    await u.message.reply_text("⚠️ *QUÉT 30 NGÀY TỚI*\n━━━━━━━━━━━━━━\n\n" + ("\n\n".join(warns) if warns else "✅ Mọi sự bình an."), parse_mode="Markdown")

async def cmd_ngay_dai_ky(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: await u.message.reply_text("Mày chưa nhập thông tin! Gõ /nhapngaysinh đi đã."); return
    m = int(c.args[0]) if c.args and c.args[0].isdigit() else today_vn().month
    y = today_vn().year; msg = [f"📅 *NGÀY XUNG THÁNG {m}/{y}*\n━━━━━━━━━━━━━━"]; curr = date(y, m, 1); found = False
    while curr.month == m:
        res = phan_tich_ngay_sau(curr, 12, info)
        if res["is_dangerous"]: msg.append(f"• *{curr.strftime('%d/%m')}*: {res['muc']} ({res['diem']}đ)"); found = True
        curr += timedelta(days=1)
    if not found: msg.append("✅ Không có ngày xung nặng.")
    await u.message.reply_text("\n".join(msg), parse_mode="Markdown")

async def cmd_hom_nay(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: await u.message.reply_text("Mày chưa nhập thông tin! Gõ /nhapngaysinh đi đã."); return
    res = phan_tich_ngay_sau(today_vn(), now_vn().hour, info); exp = phan_tich_chuyen_gia_3_mon(today_vn(), info["la_so"])
    dung_than, than_loai = xac_dinh_dung_than(info["la_so"]) 
    def bar(s): return "🟢" * int(s/2) + "⚪" * (5 - int(s/2))
    txt = f"☀️ *KHÍ VẬN HIỆN TẠI (Thuật toán cl4):*\n━━━━━━━━━━\n" \
          f"👤 Thân {than_loai} - Dụng Thần: {', '.join(dung_than)}\n\n" \
          f"📊 *Chỉ số (Thang 10):*\n" \
          f"💰 Trading: {exp['trading']} {bar(exp['trading'])}\n" \
          f"📚 Học tập: {exp['study']} {bar(exp['study'])}\n" \
          f"🚗 Di chuyển: {exp['move']} {bar(exp['move'])}\n" \
          f"❤️ Sức khỏe: {exp['health']} {bar(exp['health'])}\n" \
          f"💼 Công việc: {exp['work']} {bar(exp['work'])}\n\n" \
          f"*Kết quả:* {res['muc']} ({res['diem']}đ)\n" + "\n".join(res['detail'])
    await u.message.reply_text(txt, parse_mode="Markdown")

def main():
    if not BOT_TOKEN: return
    init_db(); app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(entry_points=[CommandHandler("nhapngaysinh", nhap_start)], states={NHAP_N:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_n)], NHAP_T:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_t)], NHAP_D:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_d)], NHAP_G:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_g)]}, fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)])
    app.add_handler(conv); app.add_handler(CommandHandler("start", cmd_start)); app.add_handler(CommandHandler("canhbao", cmd_canh_bao)); app.add_handler(CommandHandler("ngaydaiky", cmd_ngay_dai_ky)); app.add_handler(CommandHandler("homnay", cmd_hom_nay)); app.run_polling()

if __name__ == "__main__": main()
