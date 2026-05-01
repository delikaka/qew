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
# CONFIG & LOGGING
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# DỮ LIỆU NỀN TẢNG
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

# ------------------------------------------------------------
# HÀM LOGIC CỐT LÕI
# ------------------------------------------------------------

def tinh_thap_than(nhat_chu, can_check):
    if nhat_chu not in NGU_HANH or can_check not in NGU_HANH: return "N/A"
    nh_chu, nh_check = NGU_HANH[nhat_chu], NGU_HANH[can_check]
    cung_ad = (AM_DUONG_CAN[nhat_chu] == AM_DUONG_CAN[can_check])
    if nh_check == nh_chu: return "Kiếp Tài" if not cung_ad else "Tỷ Kiên"
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

def build_tu_tru(nam, tc, ngay, gio):
    cn = THIEN_CAN[(nam-4)%10]; chin = DIA_CHI[(nam-4)%12]
    d_diff = (ngay - date(1900,1,1)).days
    cng = THIEN_CAN[(d_diff + 10) % 10]; ching = DIA_CHI[(d_diff + 10) % 12]
    idx_gio = (gio + 1) // 2
    start_can_gio = ((d_diff + 10) % 5) * 2
    cg = THIEN_CAN[(start_can_gio + idx_gio) % 10]; chig = DIA_CHI[idx_gio % 12]
    return {"nam":{"can":cn,"chi":chin},"ngay":{"can":cng,"chi":ching},"thang":{"chi":tc},"gio":{"can":cg,"chi":chig},"nhat_chu":cng}

def xet_vuong_nhuoc(ls):
    """Xác định Thân Vượng hay Nhược dựa trên lệnh tháng"""
    nc_nh = NGU_HANH[ls["nhat_chu"]]
    thang_chi = ls["thang"]["chi"]
    # Đắc lệnh: Nhật chủ cùng hành hoặc được sinh bởi hành của tháng
    if NGU_HANH[thang_chi] == nc_nh or TUONG_SINH[NGU_HANH[thang_chi]] == nc_nh:
        return "Vượng"
    return "Nhược"

# ------------------------------------------------------------
# ENGINE PHÂN TÍCH ĐA TẦNG (UPGRADED)
# ------------------------------------------------------------

def phan_tich_chuyên_sâu(ngay_check: date, gio: int, sinh_info: dict):
    ls = sinh_info["la_so"]
    nhat_chu_can = ls["nhat_chu"]
    nc_vuong_nhuoc = xet_vuong_nhuoc(ls)
    
    _, month_chi = get_tiet_khi(ngay_check)
    tt_now = build_tu_tru(ngay_check.year, month_chi, ngay_check, gio)
    
    thap_than = tinh_thap_than(nhat_chu_can, tt_now["ngay"]["can"])
    diem_hung = 0.0
    chi_tiet = []
    
    # Check Xung khắc cơ bản
    if frozenset({tt_now["ngay"]["chi"], ls["ngay"]["chi"]}) in LUC_XUNG:
        diem_hung += 8
        chi_tiet.append(f"🔥 Xung Nhật Chủ ({tt_now['ngay']['chi']}-{ls['ngay']['chi']})")
    if thap_than == "Thất Sát":
        diem_hung += 5
        chi_tiet.append("⚔️ Phạm Thất Sát (Áp lực/Tai ương)")

    # --- 1. RÈN LUYỆN THỂ CHẤT ---
    the_chat = {"status": "🟢 Tốt", "msg": "Có thể tập cường độ cao."}
    if thap_than == "Thất Sát" or diem_hung >= 8:
        the_chat = {"status": "🔴 Nguy hiểm", "msg": "Dễ chấn thương, nên nghỉ ngơi."}
    elif nc_vuong_nhuoc == "Nhược" and thap_than in ["Thực Thần", "Thương Quan"]:
        the_chat = {"status": "🟡 Yếu", "msg": "Năng lượng thấp, chỉ nên tập nhẹ."}

    # --- 2. NGHIÊN CỨU / HỌC TẬP ---
    tri_tue = {"status": "🟢 Tốt", "msg": "Đầu óc minh mẫn."}
    if thap_than in ["Thiên Ấn", "Chính Ấn"]:
        tri_tue = {"status": "🌟 Đại cát", "msg": "Tập trung cực cao, giải bài khó tốt."}
    elif thap_than == "Kiếp Tài" or diem_hung >= 5:
        tri_tue = {"status": "🔴 Kém", "msg": "Dễ xao nhãng, nhiều tạp niệm."}

    # --- 3. GIAO DỊCH / TÀI CHÍNH ---
    tai_chinh = {"status": "🟢 Ổn định", "msg": "Giao dịch bình thường."}
    if thap_than == "Chính Tài" or thap_than == "Thiên Tài":
        tai_chinh = {"status": "💰 Thuận lợi", "msg": "Dễ có lộc hoặc chốt deal nhanh."}
    elif thap_than == "Kiếp Tài":
        tai_chinh = {"status": "🔴 Kỵ", "msg": "Dễ mất tiền, không nên ký kết lớn."}

    # --- 4. XÂY DỰNG / ĐỘNG THỔ ---
    xay_dung = {"status": "🟢 Thuận", "msg": "Không phạm xung lớn."}
    if frozenset({tt_now["ngay"]["chi"], ls["nam"]["chi"]}) in LUC_XUNG:
        xay_dung = {"status": "🔴 Đại kỵ", "msg": "Xung trụ Năm (Đất đai/Tổ tiên)."}

    # --- 5. DI CHUYỂN / ĐI XA ---
    di_chuyen = {"status": "🟢 Bình an", "msg": "Lộ trình thông suốt."}
    if diem_hung >= 10:
        di_chuyen = {"status": "🔴 Lưu ý", "msg": "Dễ gặp trục trặc, va chạm."}

    return {
        "diem": diem_hung,
        "the_chat": the_chat,
        "tri_tue": tri_tue,
        "tai_chinh": tai_chinh,
        "xay_dung": xay_dung,
        "di_chuyen": di_chuyen,
        "chi_tiet": chi_tiet
    }

# ============================================================
# DB & BOT HANDLERS
# ============================================================
DB_PATH = "daiky_v3.db"
def init_db():
    conn = sqlite3.connect(DB_PATH); conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, data TEXT)"); conn.commit(); conn.close()
def get_data(uid):
    conn = sqlite3.connect(DB_PATH); r = conn.execute("SELECT data FROM users WHERE user_id=?", (str(uid),)).fetchone(); conn.close()
    return json.loads(r[0]) if r else None

NHAP_N, NHAP_T, NHAP_D, NHAP_G = range(4)

async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    txt = "🌟 *BOT HUYỀN HỌC 3.5 - TRỢ LÝ HIỆU SUẤT*\n\n"
    txt += "📜 *DANH SÁCH LỆNH:*\n"
    txt += "• /nhapngaysinh - Cài đặt lá số\n"
    txt += "• /homnay - Xem chi tiết khí vận hiện tại\n"
    txt += "• /canhbao - Quét 30 ngày tới (Chỉ báo hạn nặng)\n"
    await u.message.reply_text(txt, parse_mode="Markdown")

async def cmd_hom_nay(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: await u.message.reply_text("Nhập ngày sinh đi đã mày! /nhapngaysinh"); return
    
    res = phan_tich_chuyên_sâu(date.today(), datetime.now().hour, info)
    
    msg = f"☀️ *KHÍ VẬN HÔM NAY ({date.today().strftime('%d/%m/%Y')})*\n"
    msg += "━━━━━━━━━━━━━━\n"
    msg += f"🏃 **Thể chất:** {res['the_chat']['status']} - {res['the_chat']['msg']}\n"
    msg += f"🧠 **Trí tuệ:** {res['tri_tue']['status']} - {res['tri_tue']['msg']}\n"
    msg += f"💰 **Tài chính:** {res['tai_chinh']['status']} - {res['tai_chinh']['msg']}\n"
    msg += f"🏗️ **Xây dựng:** {res['xay_dung']['status']} - {res['xay_dung']['msg']}\n"
    msg += f"🚗 **Di chuyển:** {res['di_chuyen']['status']} - {res['di_chuyen']['msg']}\n"
    
    if res['chi_tiet']:
        msg += "\n⚠️ *Lưu ý:* " + ", ".join(res['chi_tiet'])
        
    await u.message.reply_text(msg, parse_mode="Markdown")

# (Các hàm nhập liệu nhap_start, nhap_n, nhap_t... giữ nguyên logic như bản trước nhưng lưu vào daiky_v3.db)
# Để tiết kiệm không gian, tao chỉ tập trung vào phần hiển thị mới.
# --------------------------------------------------------------------------------------

async def nhap_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("Nhập NĂM SINH (vd: 1990):"); return NHAP_N

async def nhap_n(u: Update, c: ContextTypes.DEFAULT_TYPE):
    try:
        c.user_data["n"] = int(u.message.text)
        await u.message.reply_text("Nhập THÁNG SINH (1-12):"); return NHAP_T
    except: return NHAP_N

async def nhap_t(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data["t"] = int(u.message.text); await u.message.reply_text("Nhập NGÀY SINH (1-31):"); return NHAP_D

async def nhap_d(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data["d"] = int(u.message.text); await u.message.reply_text("Nhập GIỜ SINH (0-23):"); return NHAP_G

async def nhap_g(u: Update, c: ContextTypes.DEFAULT_TYPE):
    n, t, d, g = c.user_data["n"], c.user_data["t"], c.user_data["d"], int(u.message.text)
    ngay_sinh = date(n, t, d)
    _, tc = get_tiet_khi(ngay_sinh)
    ls = build_tu_tru(n, tc, ngay_sinh, g)
    data = {"n":n,"t":t,"d":d,"g":g,"la_so":ls}
    conn = sqlite3.connect(DB_PATH); conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (str(u.effective_user.id), json.dumps(data))); conn.commit(); conn.close()
    await u.message.reply_text("✅ Đã lưu! Gõ /homnay để xem kết quả."); return ConversationHandler.END

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("nhapngaysinh", nhap_start)],
        states={
            NHAP_N: [MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_n)],
            NHAP_T: [MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_t)],
            NHAP_D: [MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_d)],
            NHAP_G: [MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_g)],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("homnay", cmd_hom_nay))
    app.run_polling()

if __name__ == "__main__": main()
