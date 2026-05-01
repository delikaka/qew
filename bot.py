#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Telegram - Tứ Trụ Đại Kỵ (Bản Full Cập Nhật Chính Xung)
Sửa đổi cho: Chau Khac Khoa
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
# DỮ LIỆU TỨ TRỤ
# ============================================================
THIEN_CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
DIA_CHI   = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]

NGU_HANH_CAN = {"Giáp": "Mộc", "Ất": "Mộc", "Bính": "Hỏa", "Đinh": "Hỏa", "Mậu": "Thổ", "Kỷ": "Thổ", "Canh": "Kim", "Tân": "Kim", "Nhâm": "Thủy", "Quý": "Thủy"}
AM_DUONG_CAN = {"Giáp": "Dương", "Ất": "Âm", "Bính": "Dương", "Đinh": "Âm", "Mậu": "Dương", "Kỷ": "Âm", "Canh": "Dương", "Tân": "Âm", "Nhâm": "Dương", "Quý": "Âm"}
TUONG_SINH = {"Mộc": "Hỏa", "Hỏa": "Thổ", "Thổ": "Kim", "Kim": "Thủy", "Thủy": "Mộc"}
TUONG_KHAC = {"Mộc": "Thổ", "Thổ": "Thủy", "Thủy": "Hỏa", "Hỏa": "Kim", "Kim": "Mộc"}

# 6 CẶP LỤC XUNG (CHÍNH XUNG)
LUC_XUNG = {
    frozenset({"Tý", "Ngọ"}), frozenset({"Sửu", "Mùi"}),
    frozenset({"Dần", "Thân"}), frozenset({"Mão", "Dậu"}),
    frozenset({"Thìn", "Tuất"}), frozenset({"Tỵ", "Hợi"}),
}
THAP_THAN_XAU = {"Thất Sát", "Thương Quan", "Kiếp Tài"}

# ============================================================
# HÀM LOGIC TÍNH TOÁN
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
    TIET_KHI = [(1,6,"Tiểu Hàn"),(2,4,"Lập Xuân"),(3,6,"Kinh Trập"),(4,5,"Thanh Minh"),(5,6,"Lập Hạ"),(6,6,"Mang Chủng"),(7,7,"Tiểu Thử"),(8,7,"Lập Thu"),(9,8,"Bạch Lộ"),(10,8,"Hàn Lộ"),(11,7,"Lập Đông"),(12,7,"Đại Tuyết")]
    tiet_ten, chi_thang = "Đông Chí", "Tý"
    for m, d, name in reversed(TIET_KHI):
        if ngay >= date(ngay.year, m, d):
            tiet_ten = name; break
    MAP_CHI = {"Lập Xuân":"Dần","Kinh Trập":"Mão","Thanh Minh":"Thìn","Lập Hạ":"Tỵ","Mang Chủng":"Ngọ","Tiểu Thử":"Mùi","Lập Thu":"Thân","Bạch Lộ":"Dậu","Hàn Lộ":"Tuất","Lập Đông":"Hợi","Đại Tuyết":"Tý","Tiểu Hàn":"Sửu"}
    return tiet_ten, MAP_CHI.get(tiet_ten, "Dần")

def build_tu_tru(nam, thang_chi, ngay, gio):
    c_nam = THIEN_CAN[(nam-4)%10]; chi_n = DIA_CHI[(nam-4)%12]
    delta = (ngay - date(1900, 1, 1)).days
    c_ngay = THIEN_CAN[(delta + 10) % 10]; chi_ngay = DIA_CHI[(delta + 10) % 12]
    chi_g = DIA_CHI[((gio + 1) // 2) % 12]
    return {"nam":{"can":c_nam,"chi":chi_n},"ngay":{"can":c_ngay,"chi":chi_ngay},"thang":{"chi":thang_chi},"gio":{"chi":chi_g},"nhat_chu":c_ngay}

def phan_tich_ngay(ngay_check: date, gio: int, sinh_info: dict):
    la_so = sinh_info["la_so"]
    nhat_chu = la_so["nhat_chu"]
    tiet_ten, thang_chi = get_tiet_khi_hien_tai(ngay_check)
    tt_now = build_tu_tru(ngay_check.year, thang_chi, ngay_check, gio)
    
    diem_xau = 0
    chi_tiet = []
    is_chinh_xung = False
    
    # Logic Chính Xung tập trung vào Nhật Chủ & Trụ Năm
    check_points = [("Ngày", tt_now["ngay"]["chi"]), ("Giờ", tt_now["gio"]["chi"]), ("Tháng", tt_now["thang"]["chi"]), ("Năm", tt_now["nam"]["chi"])]
    target_points = [("Ngày (Mệnh)", la_so["ngay"]["chi"], 8), ("Năm (Tuổi)", la_so["nam"]["chi"], 5)]

    for n_now, c_now in check_points:
        for n_target, c_target, weight in target_points:
            if frozenset({c_now, c_target}) in LUC_XUNG:
                diem_xau += weight; is_chinh_xung = True
                chi_tiet.append(f"🔥 {n_now} xung {n_target} ({c_now} ⬌ {c_target})")

    tt_can = tinh_thap_than(nhat_chu, tt_now["ngay"]["can"])
    if tt_can in THAP_THAN_XAU: diem_xau += 3; chi_tiet.append(f"⚠️ Nhật chủ gặp {tt_can}")

    if diem_xau >= 12: muc = "🔴 CỰC NẶNG"
    elif diem_xau >= 8: muc = "🟠 RẤT NẶNG"
    elif diem_xau >= 4: muc = "🟡 TRUNG BÌNH"
    else: muc = "✅ BÌNH THƯỜNG"

    return {"diem_xau":diem_xau, "muc_do":muc, "chi_tiet":chi_tiet, "is_chinh_xung":is_chinh_xung, "tt_now":tt_now, "tiet":tiet_ten}

# ============================================================
# DATABASE & STORAGE
# ============================================================
DB_PATH = "daiky.db"
def init_db():
    conn = sqlite3.connect(DB_PATH); conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, data TEXT)"); conn.commit(); conn.close()

def get_sinh_info(user_id):
    conn = sqlite3.connect(DB_PATH); row = conn.execute("SELECT data FROM users WHERE user_id=?", (str(user_id),)).fetchone(); conn.close()
    return json.loads(row[0]) if row else None

# ============================================================
# COMMAND HANDLERS
# ============================================================
NHAP_NAM, NHAP_THANG, NHAP_NGAY, NHAP_GIO = range(4)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = get_sinh_info(update.effective_user.id)
    txt = "🌟 *BOT ĐẠI KỴ TỨ TRỤ* 🌟\n" + ("✅ Đã có thông tin" if info else "❌ Chưa có thông tin") + "\n\n"
    txt += "📋 `/nhapngaysinh` - Nhập ngày sinh\n📅 `/ngaydaiky` - Xem tháng này\n📅 `/ngaydaikynam` - Xem cả năm\n☀️ `/homnay` - Xem hôm nay\n⚠️ `/canhbao` - Cảnh báo sắp tới\n📖 `/bamenh` - Xem lá số"
    await update.message.reply_text(txt, parse_mode="Markdown")

async def start_nhap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Nhập *NĂM SINH* (vd: 2009):", parse_mode="Markdown"); return NHAP_NAM

async def nhan_nam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["n"] = int(update.message.text); await update.message.reply_text("Nhập *THÁNG* (1-12):", parse_mode="Markdown"); return NHAP_THANG

async def nhan_thang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["t"] = int(update.message.text); await update.message.reply_text("Nhập *NGÀY* (1-31):", parse_mode="Markdown"); return NHAP_NGAY

async def nhan_ngay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["d"] = int(update.message.text); await update.message.reply_text("Nhập *GIỜ* (0-23):", parse_mode="Markdown"); return NHAP_GIO

async def nhan_gio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    g = int(update.message.text); n, t, d = context.user_data["n"], context.user_data["t"], context.user_data["d"]
    _, tc = get_tiet_khi_hien_tai(date(n, t, d)); ls = build_tu_tru(n, tc, date(n, t, d), g)
    data = {"nam":n,"thang":t,"ngay":d,"gio":g,"la_so":ls}
    conn = sqlite3.connect(DB_PATH); conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (str(update.effective_user.id), json.dumps(data))); conn.commit(); conn.close()
    await update.message.reply_text("✅ Đã lưu lá số! Dùng /ngaydaiky ngay."); return ConversationHandler.END

async def cmd_hom_nay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = get_sinh_info(update.effective_user.id)
    if not info: await update.message.reply_text("❌ Nhập /nhapngaysinh trước."); return
    res = phan_tich_ngay(date.today(), datetime.now().hour, info)
    txt = f"☀️ *HÔM NAY:* {date.today().strftime('%d/%m/%Y')}\n━━━━━━━━━━\n*Mức độ:* {res['muc_do']}\n" + "\n".join(res['chi_tiet'])
    await update.message.reply_text(txt, parse_mode="Markdown")

async def cmd_ngay_dai_ky(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = get_sinh_info(update.effective_user.id)
    if not info: return
    thang = int(context.args[0]) if context.args else date.today().month
    msg = [f"📅 *ĐẠI KỴ THÁNG {thang}* (Lọc Chính Xung)\n━━━━━━━━━━"]
    curr = date(date.today().year, thang, 1)
    while curr.month == thang:
        res = phan_tich_ngay(curr, 12, info)
        if res["is_chinh_xung"] or res["diem_xau"] >= 8:
            msg.append(f"*{curr.strftime('%d/%m/%Y')}* - {res['muc_do']}")
            for c in res['chi_tiet']: msg.append(f"  {c}")
            msg.append("")
        curr += timedelta(days=1)
    await update.message.reply_text("\n".join(msg) if len(msg)>1 else "✅ Tháng này không có ngày Chính Xung.", parse_mode="Markdown")

async def cmd_ngay_dai_ky_nam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = get_sinh_info(update.effective_user.id); await update.message.reply_text("⏳ Đang tính cả năm...")
    for m in range(1, 13):
        curr = date(2026, m, 1); msg = [f"📅 *Tháng {m}*"]
        while curr.month == m:
            res = phan_tich_ngay(curr, 12, info)
            if res["is_chinh_xung"]: msg.append(f"• {curr.strftime('%d/%m')} ({DIA_CHI[(curr - date(1900,1,1)).days % 12 + 10 % 12]})")
            curr += timedelta(days=1)
        if len(msg) > 1: await update.message.reply_text("\n".join(msg), parse_mode="Markdown")

async def cmd_canh_bao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = get_sinh_info(update.effective_user.id); today = date.today(); sap_toi = []
    for i in range(1, 15):
        d = today + timedelta(days=i); r = phan_tich_ngay(d, 12, info)
        if r["is_chinh_xung"]: sap_toi.append(f"🔔 *{d.strftime('%d/%m')}*: {r['muc_do']}")
    await update.message.reply_text("⚠️ *CẢNH BÁO 14 NGÀY TỚI:*\n\n" + "\n".join(sap_toi) if sap_toi else "✅ Không có ngày Chính Xung sắp tới.", parse_mode="Markdown")

async def cmd_ba_menh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = get_sinh_info(update.effective_user.id); ls = info["la_so"]
    txt = f"📖 *LÁ SỐ BẢN MỆNH*\n━━━━━━━━━━\nNăm: {ls['nam']['can']} {ls['nam']['chi']}\nNgày: {ls['ngay']['can']} {ls['ngay']['chi']} (Nhật Chủ)\n"
    await update.message.reply_text(txt, parse_mode="Markdown")

# ============================================================
# MAIN
# ============================================================
def main():
    init_db(); app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("nhapngaysinh", start_nhap)],
        states={NHAP_NAM:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhan_nam)], NHAP_THANG:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhan_thang)], NHAP_NGAY:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhan_ngay)], NHAP_GIO:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhan_gio)]},
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)]
    )
    app.add_handler(conv); app.add_handler(CommandHandler("start", cmd_start)); app.add_handler(CommandHandler("homnay", cmd_hom_nay)); app.add_handler(CommandHandler("ngaydaiky", cmd_ngay_dai_ky)); app.add_handler(CommandHandler("ngaydaikynam", cmd_ngay_dai_ky_nam)); app.add_handler(CommandHandler("canhbao", cmd_canh_bao)); app.add_handler(CommandHandler("bamenh", cmd_ba_menh))
    app.run_polling()

if __name__ == "__main__": main()
