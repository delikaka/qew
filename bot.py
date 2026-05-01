#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Telegram - Tứ Trụ Đại Kỵ (Bản Toán Học Tối Ưu)
Logic: Chau Khac Khoa - AI Collaboration
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
# DỮ LIỆU TỨ TRỤ & TRỌNG SỐ TOÁN HỌC
# ============================================================
THIEN_CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
DIA_CHI   = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]

NGU_HANH_CAN = {"Giáp": "Mộc", "Ất": "Mộc", "Bính": "Hỏa", "Đinh": "Hỏa", "Mậu": "Thổ", "Kỷ": "Thổ", "Canh": "Kim", "Tân": "Kim", "Nhâm": "Thủy", "Quý": "Thủy"}
AM_DUONG_CAN = {"Giáp": "Dương", "Ất": "Âm", "Bính": "Dương", "Đinh": "Âm", "Mậu": "Dương", "Kỷ": "Âm", "Canh": "Dương", "Tân": "Âm", "Nhâm": "Dương", "Quý": "Âm"}
TUONG_SINH = {"Mộc": "Hỏa", "Hỏa": "Thổ", "Thổ": "Kim", "Kim": "Thủy", "Thủy": "Mộc"}
TUONG_KHAC = {"Mộc": "Thổ", "Thổ": "Thủy", "Thủy": "Hỏa", "Hỏa": "Kim", "Kim": "Mộc"}

LUC_XUNG = {frozenset({"Tý", "Ngọ"}), frozenset({"Sửu", "Mùi"}), frozenset({"Dần", "Thân"}), frozenset({"Mão", "Dậu"}), frozenset({"Thìn", "Tuất"}), frozenset({"Tỵ", "Hợi"})}
THAP_THAN_XAU = {"Thất Sát", "Thương Quan", "Kiếp Tài"}

# ============================================================
# HÀM LOGIC CỐT LÕI
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

def get_tiet_khi(ngay: date):
    TK = [(1,6,"Tiểu Hàn"),(2,4,"Lập Xuân"),(3,6,"Kinh Trập"),(4,5,"Thanh Minh"),(5,6,"Lập Hạ"),(6,6,"Mang Chủng"),(7,7,"Tiểu Thử"),(8,7,"Lập Thu"),(9,8,"Bạch Lộ"),(10,8,"Hàn Lộ"),(11,7,"Lập Đông"),(12,7,"Đại Tuyết")]
    t, c = "Đông Chí", "Tý"
    for m, d, name in reversed(TK):
        if ngay >= date(ngay.year, m, d): t = name; break
    MAP = {"Lập Xuân":"Dần","Kinh Trập":"Mão","Thanh Minh":"Thìn","Lập Hạ":"Tỵ","Mang Chủng":"Ngọ","Tiểu Thử":"Mùi","Lập Thu":"Thân","Bạch Lộ":"Dậu","Hàn Lộ":"Tuất","Lập Đông":"Hợi","Đại Tuyết":"Tý","Tiểu Hàn":"Sửu"}
    return t, MAP.get(t, "Dần")

def build_tu_tru(nam, tc, ngay, gio):
    cn = THIEN_CAN[(nam-4)%10]; chin = DIA_CHI[(nam-4)%12]
    d = (ngay - date(1900,1,1)).days
    cng = THIEN_CAN[(d+10)%10]; ching = DIA_CHI[(d+10)%12]
    cg = THIEN_CAN[(((gio+1)//2)+0)%10] # Simplified for can gio
    chig = DIA_CHI[((gio+1)//2)%12]
    return {"nam":{"can":cn,"chi":chin},"ngay":{"can":cng,"chi":ching},"thang":{"chi":tc},"gio":{"can":cg,"chi":chig},"nhat_chu":cng}

def phan_tich_ngay(ngay_check: date, gio: int, sinh_info: dict):
    ls = sinh_info["la_so"]
    nhat_chu = ls["nhat_chu"]
    t_name, t_chi = get_tiet_khi(ngay_check)
    tt_now = build_tu_tru(ngay_check.year, t_chi, ngay_check, gio)
    
    diem_hung = 0.0
    chi_tiet = []
    xung_count = 0
    
    # Ma trận trọng số (Toán học Tứ Trụ)
    check_points = [("Ngày", tt_now["ngay"]["chi"], 1.0), ("Giờ", tt_now["gio"]["chi"], 0.8), ("Tháng", tt_now["thang"]["chi"], 1.0), ("Năm", tt_now["nam"]["chi"], 1.2)]
    target_points = [("Nhật Chủ (Dậu)", ls["ngay"]["chi"], 8), ("Bản Mệnh (Sửu)", ls["nam"]["chi"], 6)]

    for name_now, chi_now, p_coeff in check_points:
        for name_target, chi_target, weight in target_points:
            if frozenset({chi_now, chi_target}) in LUC_XUNG:
                val = weight * p_coeff
                diem_hung += val; xung_count += 1
                chi_tiet.append(f"🔥 {name_now} xung {name_target} ({chi_now} ⬌ {chi_target}) [+ {val}]")

    # Kiểm tra Thập Thần Can Ngày
    tt_can = tinh_thap_than(nhat_chu, tt_now["ngay"]["can"])
    if tt_can in THAP_THAN_XAU:
        diem_hung += 4.0; chi_tiet.append(f"⚠️ Can Ngày gặp {tt_can} [+ 4.0]")

    # Bonus Đồng Phase
    if xung_count >= 2:
        diem_hung += 5.0; chi_tiet.append("🚨 Cảnh báo: ĐỒNG PHASE XUNG (Nhiều trụ cùng đánh) [+ 5.0]")

    if diem_hung >= 15: muc = "🔴 CỰC NẶNG"
    elif diem_hung >= 10: muc = "🟠 RẤT NẶNG"
    elif diem_hung >= 5: muc = "🟡 TRUNG BÌNH"
    else: muc = "✅ BÌNH THƯỜNG"

    return {"diem": round(diem_hung, 1), "muc": muc, "detail": chi_tiet, "is_xung": (xung_count > 0)}

# ============================================================
# COMMAND HANDLERS
# ============================================================
DB_PATH = "daiky.db"
def init_db():
    conn = sqlite3.connect(DB_PATH); conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, data TEXT)"); conn.commit(); conn.close()

def get_data(uid):
    conn = sqlite3.connect(DB_PATH); r = conn.execute("SELECT data FROM users WHERE user_id=?", (str(uid),)).fetchone(); conn.close()
    return json.loads(r[0]) if r else None

NHAP_N, NHAP_T, NHAP_D, NHAP_G = range(4)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = "🌟 *BOT ĐẠI KỴ - TOÁN HỌC TỨ TRỤ* 🌟\n\n"
    txt += "📋 `/nhapngaysinh` - Nhập thông tin\n📅 `/ngaydaiky` - Xem tháng này\n⚠️ `/canhbao` - Cảnh báo nguy hiểm\n☀️ `/homnay` - Soi hôm nay\n📖 `/bamenh` - Xem lá số"
    await update.message.reply_text(txt, parse_mode="Markdown")

async def nhap_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("Nhập NĂM SINH (vd: 1990):"); return NHAP_N
async def nhap_n(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data["n"] = int(u.message.text); await u.message.reply_text("Nhập THÁNG SINH:"); return NHAP_T
async def nhap_t(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data["t"] = int(u.message.text); await u.message.reply_text("Nhập NGÀY SINH:"); return NHAP_D
async def nhap_d(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data["d"] = int(u.message.text); await u.message.reply_text("Nhập GIỜ SINH (0-23):"); return NHAP_G
async def nhap_g(u: Update, c: ContextTypes.DEFAULT_TYPE):
    g = int(u.message.text); n,t,d = c.user_data["n"], c.user_data["t"], c.user_data["d"]
    _, tc = get_tiet_khi(date(n,t,d)); ls = build_tu_tru(n, tc, date(n,t,d), g)
    data = {"n":n,"t":t,"d":d,"g":g,"la_so":ls}
    conn = sqlite3.connect(DB_PATH); conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (str(u.effective_user.id), json.dumps(data))); conn.commit(); conn.close()
    await u.message.reply_text("✅ Đã lưu! Thử ngay `/canhbao`."); return ConversationHandler.END

async def cmd_hom_nay(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: return
    res = phan_tich_ngay(date.today(), datetime.now().hour, info)
    txt = f"☀️ *SO KHÍ HÔM NAY:* {date.today().strftime('%d/%m/%Y')}\n━━━━━━━━━━\n*Kết quả:* {res['muc']} ({res['diem']} điểm)\n" + "\n".join(res['detail'])
    await u.message.reply_text(txt, parse_mode="Markdown")

async def cmd_ngay_dai_ky(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: return
    m = int(c.args[0]) if c.args else date.today().month
    msg = [f"📅 *ĐẠI KỴ THÁNG {m}*\n━━━━━━━━━━"]
    curr = date(date.today().year, m, 1)
    while curr.month == m:
        res = phan_tich_ngay(curr, 12, info)
        if res["is_xung"] or res["diem"] >= 10:
            msg.append(f"*{curr.strftime('%d/%m')}* - {res['muc']} ({res['diem']}đ)")
        curr += timedelta(days=1)
    await u.message.reply_text("\n".join(msg), parse_mode="Markdown")

async def cmd_canh_bao(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: return
    await u.message.reply_text("⏳ Đang quét 30 ngày tới dựa trên Ma trận Tứ Trụ...")
    today = date.today(); warns = []
    for i in range(1, 31):
        d = today + timedelta(days=i); res = phan_tich_ngay(d, 12, info)
        if res["diem"] >= 10: # Chỉ báo ngày từ Rất Nặng trở lên
            warns.append(f"🔴 *{d.strftime('%d/%m/%Y')}* ({res['diem']}đ)\n   ↳ {res['muc']}\n   ↳ {res['detail'][0] if res['detail'] else ''}")
    
    txt = "⚠️ *DANH SÁCH ĐIỂM NÓNG (30 NGÀY TỚI)*\n━━━━━━━━━━━━━━━━━━\n\n"
    txt += "\n\n".join(warns) if warns else "✅ 30 ngày tới khí vận bình hòa, không có ngày đại kỵ nặng."
    await u.message.reply_text(txt, parse_mode="Markdown")

async def cmd_ba_menh(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id); ls = info["la_so"]
    txt = f"📖 *THÔNG TIN LÁ SỐ*\n━━━━━━━━━━\nTrụ Năm: {ls['nam']['can']} {ls['nam']['chi']}\nNhật Chủ: {ls['ngay']['can']} {ls['ngay']['chi']}\n"
    await u.message.reply_text(txt, parse_mode="Markdown")

async def cmd_help(u: Update, c: ContextTypes.DEFAULT_TYPE):
    txt = "💡 *HƯỚNG DẪN THANG ĐIỂM:*\n\n"
    txt += "• 🔴 > 15đ: Cực kỳ nguy hiểm (Đồng phase xung)\n"
    txt += "• 🟠 > 10đ: Rất nặng (Chính xung Nhật Chủ)\n"
    txt += "• 🟡 > 5đ: Cần lưu tâm (Xung nhẹ hoặc Thập thần xấu)\n"
    await u.message.reply_text(txt, parse_mode="Markdown")

def main():
    init_db(); app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("nhapngaysinh", nhap_start)],
        states={NHAP_N:[MessageHandler(filters.TEXT, nhap_n)], NHAP_T:[MessageHandler(filters.TEXT, nhap_t)], NHAP_D:[MessageHandler(filters.TEXT, nhap_d)], NHAP_G:[MessageHandler(filters.TEXT, nhap_g)]},
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)]
    )
    app.add_handler(conv); app.add_handler(CommandHandler("start", cmd_start)); app.add_handler(CommandHandler("homnay", cmd_hom_nay)); app.add_handler(CommandHandler("ngaydaiky", cmd_ngay_dai_ky)); app.add_handler(CommandHandler("canhbao", cmd_canh_bao)); app.add_handler(CommandHandler("bamenh", cmd_ba_menh)); app.add_handler(CommandHandler("help", cmd_help))
    app.run_polling()

if __name__ == "__main__": main()
