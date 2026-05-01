import logging
import os
import json
import sqlite3
from datetime import datetime, date, timedelta
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)

# ============================================================
# CONFIG & DATA STRUCTURES (NÂNG CẤP)
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

THIEN_CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
DIA_CHI   = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]

# Tàng Can (Lõi của Địa Chi)
TANG_CAN = {
    "Tý": ["Quý"], "Sửu": ["Kỷ", "Quý", "Tân"], "Dần": ["Giáp", "Bính", "Mậu"],
    "Mão": ["Ất"], "Thìn": ["Mậu", "Ất", "Quý"], "Tỵ": ["Bính", "Canh", "Mậu"],
    "Ngọ": ["Đinh", "Kỷ"], "Mùi": ["Kỷ", "Đinh", "Ất"], "Thân": ["Canh", "Nhâm", "Mậu"],
    "Dậu": ["Tân"], "Tuất": ["Mậu", "Tân", "Đinh"], "Hợi": ["Nhâm", "Giáp"]
}

LUC_HOP = {frozenset({"Tý", "Sửu"}), frozenset({"Dần", "Hợi"}), frozenset({"Mão", "Tuất"}), 
           frozenset({"Thìn", "Dậu"}), frozenset({"Tỵ", "Thân"}), frozenset({"Ngọ", "Mùi"})}

LUC_XUNG = {frozenset({"Tý", "Ngọ"}), frozenset({"Sửu", "Mùi"}), frozenset({"Dần", "Thân"}), 
            frozenset({"Mão", "Dậu"}), frozenset({"Thìn", "Tuất"}), frozenset({"Tỵ", "Hợi"})}

NGU_HANH = {"Giáp":"Mộc","Ất":"Mộc","Bính":"Hỏa","Đinh":"Hỏa","Mậu":"Thổ","Kỷ":"Thổ","Canh":"Kim","Tân":"Kim","Nhâm":"Thủy","Quý":"Thủy",
            "Dần":"Mộc","Mão":"Mộc","Tỵ":"Hỏa","Ngọ":"Hỏa","Thân":"Kim","Dậu":"Kim","Hợi":"Thủy","Tý":"Thủy","Sửu":"Thổ","Thìn":"Thổ","Mùi":"Thổ","Tuất":"Thổ"}

# ============================================================
# TOÁN HỌC LÝ SỐ NÂNG CAO
# ============================================================
def get_season_multiplier(month_chi, day_chi):
    # Logic Vượng Suy theo mùa
    day_nh = NGU_HANH.get(day_chi)
    seasons = {
        "Mộc": ["Dần", "Mão", "Thìn"], "Hỏa": ["Tỵ", "Ngọ", "Mùi"],
        "Kim": ["Thân", "Dậu", "Tuất"], "Thủy": ["Hợi", "Tý", "Sửu"]
    }
    vuong_element = next((k for k, v in seasons.items() if month_chi in v), None)
    return 1.2 if day_nh == vuong_element else 1.0

def phan_tich_ngay_sau(ngay_check: date, gio: int, sinh_info: dict):
    ls = sinh_info["la_so"]
    nhat_chu_can = ls["nhat_chu"]
    _, month_chi = get_tiet_khi(ngay_check)
    tt_now = build_tu_tru(ngay_check.year, month_chi, ngay_check, gio)
    
    diem_hung = 0.0
    chi_tiet = []
    
    # 1. Quét ma trận Xung - Hợp[cite: 1, 2]
    check_list = [("Ngày", tt_now["ngay"]["chi"], 1.5), ("Năm", tt_now["nam"]["chi"], 1.2)]
    targets = [("Nhật Chủ", ls["ngay"]["chi"], 8), ("Trụ Năm", ls["nam"]["chi"], 5)]

    for n_now, c_now, p_coeff in check_list:
        for n_tar, c_tar, weight in targets:
            # Kiểm tra Xung
            if frozenset({c_now, c_tar}) in LUC_XUNG:
                current_score = weight * p_coeff * get_season_multiplier(ls["thang"]["chi"], c_now)
                
                # CƠ CHẾ GIẢI XUNG: Nếu trụ đó đồng thời có Hợp thì giảm nhẹ[cite: 1, 2]
                is_saved = any(frozenset({c_now, other}) in LUC_HOP for _, other, _ in check_list if other != c_now)
                if is_saved:
                    current_score *= 0.4
                    chi_tiet.append(f"🛡️ {n_now} Xung {n_tar} nhưng được Hợp giải vây (Giảm nhẹ)")
                else:
                    chi_tiet.append(f"🔥 {n_now} Xung {n_tar} ({c_now}-{c_tar})")
                
                diem_hung += current_score

    # 2. Soi Tàng Can (Hidden Conflict)[cite: 1, 2]
    # Nếu Can của ngày hiện tại khắc Can của Nhật Chủ
    from_can = tt_now["ngay"]["can"]
    tt_label = tinh_thap_than(nhat_chu_can, from_can)
    if tt_label == "Thất Sát":
        diem_hung += 5
        chi_tiet.append(f"⚔️ Thiên Can phạm Thất Sát (Áp lực lớn)")

    # Phân loại mức độ
    if diem_hung >= 12: muc = "🔴 CỰC NẶNG"
    elif diem_hung >= 7: muc = "🟠 RẤT NẶNG"
    elif diem_hung >= 3: muc = "🟡 TRUNG BÌNH"
    else: muc = "✅ BÌNH THƯỜNG"

    return {"diem": round(diem_hung, 1), "muc": muc, "detail": chi_tiet}

# ============================================================
# RENDER LỆNH (GIỮ NGUYÊN CẤU TRÚC CŨ)
# ============================================================
async def cmd_canh_bao(u: Update, c: ContextTypes.DEFAULT_TYPE):
    user_id = u.effective_user.id
    info = get_data(user_id)
    if not info:
        await u.message.reply_text("❌ Chưa có dữ liệu. Dùng /nhapngaysinh"); return
    
    today = date.today()
    warns = []
    for i in range(1, 31):
        d = today + timedelta(days=i)
        res = phan_tich_ngay_sau(d, 12, info) # Dùng hàm nâng cấp mới[cite: 1, 2]
        if res["diem"] >= 7:
            warns.append(f"📅 *{d.strftime('%d/%m')}* ({res['diem']}đ): {res['muc']}\n   ↳ {', '.join(res['detail'])}")
    
    header = "⚠️ *QUÉT MA TRẬN HUNG INDEX (30 NGÀY)*\n━━━━━━━━━━━━━━\n"
    await u.message.reply_text(header + ("\n\n".join(warns) if warns else "✅ Không có biến động lớn."), parse_mode="Markdown")

# [Các hàm khởi tạo DB, build_tu_tru, get_tiet_khi... giữ nguyên như bản trước]
