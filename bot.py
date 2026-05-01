#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Telegram - Tứ Trụ Đại Kỵ (Bản Cập Nhật: Tập Trung Chính Xung)
Phát triển bởi: Chau Khac Khoa
"""

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
# CONFIG
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("❌ Chưa set biến môi trường BOT_TOKEN!")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# DỮ LIỆU TỨ TRỤ & LOGIC XUNG KHẮC
# ============================================================
THIEN_CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
DIA_CHI   = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]

NGU_HANH_CAN = {"Giáp": "Mộc", "Ất": "Mộc", "Bính": "Hỏa", "Đinh": "Hỏa", "Mậu": "Thổ", "Kỷ": "Thổ", "Canh": "Kim", "Tân": "Kim", "Nhâm": "Thủy", "Quý": "Thủy"}
AM_DUONG_CAN = {"Giáp": "Dương", "Ất": "Âm", "Bính": "Dương", "Đinh": "Âm", "Mậu": "Dương", "Kỷ": "Âm", "Canh": "Dương", "Tân": "Âm", "Nhâm": "Dương", "Quý": "Âm"}
TUONG_SINH = {"Mộc": "Hỏa", "Hỏa": "Thổ", "Thổ": "Kim", "Kim": "Thủy", "Thủy": "Mộc"}
TUONG_KHAC = {"Mộc": "Thổ", "Thổ": "Thủy", "Thủy": "Hỏa", "Hỏa": "Kim", "Kim": "Mộc"}

# LỤC XUNG (CHÍNH XUNG) - Trọng tâm của bài toán
LUC_XUNG = {
    frozenset({"Tý", "Ngọ"}), frozenset({"Sửu", "Mùi"}),
    frozenset({"Dần", "Thân"}), frozenset({"Mão", "Dậu"}),
    frozenset({"Thìn", "Tuất"}), frozenset({"Tỵ", "Hợi"}),
}

THAP_THAN_XAU = {"Thất Sát", "Thương Quan", "Kiếp Tài"}

# ============================================================
# HÀM TÍNH TOÁN CỐT LÕI
# ============================================================

def tinh_thap_than(nhat_chu_can, can_khac):
    nh_hanh, kh_hanh = NGU_HANH_CAN[nhat_chu_can], NGU_HANH_CAN[can_khac]
    cung_ad = (AM_DUONG_CAN[nhat_chu_can] == AM_DUONG_CAN[can_khac])
    if kh_hanh == nh_hanh: return "Kiếp Tài" if cung_ad else "Tỷ Kiên"
    if TUONG_SINH.get(kh_hanh) == nh_hanh: return "Thiên Ấn" if cung_ad else "Chính Ấn"
    if TUONG_SINH.get(nh_hanh) == kh_hanh: return "Thực Thần" if cung_ad else "Thương Quan"
    if TUONG_KHAC.get(nh_hanh) == kh_hanh: return "Thiên Tài" if cung_ad else "Chính Tài"
    if TUONG_KHAC.get(kh_hanh) == nh_hanh: return "Thất Sát" if cung_ad else "Chính Quan"
    return "?"

def get_tiet_khi_hien_tai(ngay: date):
    # Đơn giản hóa tiết khí để bot chạy ổn định
    TIET_KHI_LIST = [(1,6,"Tiểu Hàn"),(2,4,"Lập Xuân"),(3,6,"Kinh Trập"),(4,5,"Thanh Minh"),(5,6,"Lập Hạ"),(6,6,"Mang Chủng"),(7,7,"Tiểu Thử"),(8,7,"Lập Thu"),(9,8,"Bạch Lộ"),(10,8,"Hàn Lộ"),(11,7,"Lập Đông"),(12,7,"Đại Tuyết")]
    tiet_ten, chi_thang = "Đông Chí", "Tý"
    for m, d, name in reversed(TIET_KHI_LIST):
        if ngay >= date(ngay.year, m, d):
            tiet_ten = name
            break
    # Mapping chi tháng theo tiết
    MAP_CHI = {"Lập Xuân":"Dần","Kinh Trập":"Mão","Thanh Minh":"Thìn","Lập Hạ":"Tỵ","Mang Chủng":"Ngọ","Tiểu Thử":"Mùi","Lập Thu":"Thân","Bạch Lộ":"Dậu","Hàn Lộ":"Tuất","Lập Đông":"Hợi","Đại Tuyết":"Tý","Tiểu Hàn":"Sửu"}
    return tiet_ten, MAP_CHI.get(tiet_ten, "Dần")

def build_tu_tru(nam, thang_chi, ngay, gio):
    # Công thức tính Can Chi cơ bản
    c_nam = THIEN_CAN[(nam-4)%10]; chi_n = DIA_CHI[(nam-4)%12]
    # Tính Can Ngày (Ref 1/1/1900 là Giáp Tuất)
    delta = (ngay - date(1900, 1, 1)).days
    c_ngay = THIEN_CAN[(delta + 10) % 10]; chi_ngay = DIA_CHI[(delta + 10) % 12]
    # Chi Giờ
    chi_g = DIA_CHI[((gio + 1) // 2) % 12]
    return {
        "nam": {"can": c_nam, "chi": chi_n},
        "ngay": {"can": c_ngay, "chi": chi_ngay},
        "thang": {"chi": thang_chi},
        "gio": {"chi": chi_g},
        "nhat_chu": c_ngay
    }

def phan_tich_ngay(ngay_check: date, gio: int, sinh_info: dict):
    la_so = sinh_info["la_so"]
    nhat_chu = la_so["nhat_chu"]
    tiet_ten, thang_chi = get_tiet_khi_hien_tai(ngay_check)
    tt_now = build_tu_tru(ngay_check.year, thang_chi, ngay_check, gio)
    
    diem_xau = 0
    chi_tiet = []
    is_chinh_xung = False

    # Chỉ tập trung so sánh Chi Ngày/Giờ/Tháng/Năm hiện tại với Chi Ngày/Năm bản mệnh
    check_points = [
        ("Ngày", tt_now["ngay"]["chi"]),
        ("Giờ", tt_now["gio"]["chi"]),
        ("Tháng", tt_now["thang"]["chi"]),
        ("Năm", tt_now["nam"]["chi"])
    ]
    
    target_points = [
        ("Ngày (Nhật Chủ)", la_so["ngay"]["chi"], 7), # Ưu tiên xung Nhật Chủ
        ("Năm (Gốc rễ)", la_so["nam"]["chi"], 5)
    ]

    for name_now, chi_now in check_points:
        for name_target, chi_target, weight in target_points:
            if frozenset({chi_now, chi_target}) in LUC_XUNG:
                diem_xau += weight
                is_chinh_xung = True
                chi_tiet.append(f"🔥 **{name_now}** xung **{name_target}** ({chi_now} ⬌ {chi_target})")

    # Thập thần can ngày
    tt_can = tinh_thap_than(nhat_chu, tt_now["ngay"]["can"])
    if tt_can in THAP_THAN_XAU:
        diem_xau += 3
        chi_tiet.append(f"⚠️ Can ngày gặp {tt_can}")

    # Xếp hạng
    if diem_xau >= 10: muc = "🔴 CỰC NẶNG"
    elif diem_xau >= 7: muc = "🟠 RẤT NẶNG"
    elif diem_xau >= 4: muc = "🟡 TRUNG BÌNH"
    else: muc = "✅ BÌNH THƯỜNG"

    return {"diem_xau": diem_xau, "muc_do": muc, "chi_tiet": chi_tiet, "is_chinh_xung": is_chinh_xung}

def lay_ngay_dai_ky_trong_thang(nam, thang, sinh_info):
    ngay_xau = []
    curr = date(nam, thang, 1)
    while curr.month == thang:
        res = phan_tich_ngay(curr, 12, sinh_info)
        # BỘ LỌC: Chỉ lấy ngày có Chính Xung hoặc điểm > 7
        if res["is_chinh_xung"] or res["diem_xau"] >= 7:
            ngay_xau.append({"ngay": curr, "res": res})
        curr += timedelta(days=1)
    return ngay_xau

# ============================================================
# DATABASE & TELEGRAM HANDLERS (Giữ nguyên cấu trúc cũ của mày)
# ============================================================
DB_PATH = "daiky.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, data TEXT)")
    conn.commit(); conn.close()

async def cmd_ngay_dai_ky(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    conn = sqlite3.connect(DB_PATH); row = conn.execute("SELECT data FROM users WHERE user_id=?", (user_id,)).fetchone(); conn.close()
    if not row:
        await update.message.reply_text("❌ Mày chưa nhập ngày sinh. Dùng /nhapngaysinh"); return
    
    sinh_info = json.loads(row[0])
    today = date.today()
    thang = int(context.args[0]) if context.args else today.month
    
    await update.message.reply_text(f"⏳ Đang lọc Chính Xung tháng {thang}...")
    ngay_list = lay_ngay_dai_ky_trong_thang(today.year, thang, sinh_info)
    
    if not ngay_list:
        await update.message.reply_text(f"✅ Tháng {thang} không có ngày Chính Xung nào. Yên tâm!"); return

    msg = [f"📅 *DANH SÁCH ĐẠI KỴ THÁNG {thang}* (Đã lọc xung nhẹ)\n━━━━━━━━━━━━━━━━━━"]
    for item in ngay_list:
        ng = item["ngay"]; r = item["res"]
        marker = " ⚡" if r["diem_xau"] >= 10 else ""
        msg.append(f"*{ng.strftime('%d/%m/%Y')}* - {r['muc_do']}{marker}")
        for d in r["chi_tiet"]: msg.append(f"  {d}")
        msg.append("")
    
    msg.append("━━━━━━━━━━━━━━━━━━\n💡 *Ghi chú:* Chỉ hiển thị các ngày có Lục Xung (Chính Xung) ảnh hưởng trực tiếp đến bản mệnh.")
    await update.message.reply_text("\n".join(msg), parse_mode="Markdown")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌟 *BOT ĐẠI KỴ - PHIÊN BẢN CHÍNH XUNG*\n\nLệnh: /ngaydaiky để xem danh sách đã lọc.")

# (Thêm các handler nhập ngày sinh như file cũ của mày vào đây)
# ... [Phần handler nhapngaysinh giữ nguyên logic cũ] ...

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ngaydaiky", cmd_ngay_dai_ky))
    # Đăng ký các handler khác của mày ở đây...
    logger.info("Bot đang chạy logic Chính Xung...")
    app.run_polling()

if __name__ == "__main__":
    main()
