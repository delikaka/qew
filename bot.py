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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# DỮ LIỆU HUYỀN HỌC HỆ THỐNG
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
LUC_XUNG = {frozenset({"Tý", "Ngọ"}), frozenset({"Sửu", "Mùi"}), frozenset({"Dần", "Thân"}), frozenset({"Mão", "Dậu"}), frozenset({"Thìn", "Tuất"}), frozenset({"Tỵ", "Hợi"})}

TRUC_12 = ["Kiến", "Trừ", "Mãn", "Bình", "Định", "Chấp", "Phá", "Nguy", "Thành", "Thu", "Khai", "Bế"]
TU_28 = ["Giác", "Cang", "Đê", "Phòng", "Tâm", "Vĩ", "Cơ", "Đẩu", "Ngưu", "Nữ", "Hư", "Nguy", "Thất", "Bích", "Khuê", "Lâu", "Vị", "Mão", "Tất", "Chủy", "Sâm", "Tỉnh", "Quỷ", "Liễu", "Tinh", "Trương", "Dực", "Chẩn"]

# ------------------------------------------------------------
# HÀM TOÁN HỌC & LOGIC
# ------------------------------------------------------------

def get_jdn(d, m, y):
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + (a // 4)
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524

def tinh_thap_than(nhat_chu, can_check):
    nh_chu, nh_check = NGU_HANH[nhat_chu], NGU_HANH[can_check]
    cung_ad = (AM_DUONG_CAN[nhat_chu] == AM_DUONG_CAN[can_check])
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
        if ngay >= date(ngay.year, m, d): t = name; break
    MAP = {"Lập Xuân":"Dần","Kinh Trập":"Mão","Thanh Minh":"Thìn","Lập Hạ":"Tỵ","Mang Chủng":"Ngọ","Tiểu Thử":"Mùi","Lập Thu":"Thân","Bạch Lộ":"Dậu","Hàn Lộ":"Tuất","Lập Đông":"Hợi","Đại Tuyết":"Tý","Tiểu Hàn":"Sửu"}
    return t, MAP.get(t, "Tý")

def build_tu_tru(nam, tc, ngay, gio):
    jdn = get_jdn(ngay.day, ngay.month, ngay.year)
    cn = THIEN_CAN[(nam-4)%10]; chin = DIA_CHI[(nam-4)%12]
    cng = THIEN_CAN[(jdn + 9) % 10]; ching = DIA_CHI[(jdn + 1) % 12]
    idx_gio = (gio + 1) // 2
    start_can_gio = ((jdn + 9) % 5) * 2
    cg = THIEN_CAN[(start_can_gio + idx_gio) % 10]; chig = DIA_CHI[idx_gio % 12]
    return {"nam":{"can":cn,"chi":chin},"ngay":{"can":cng,"chi":ching},"thang":{"chi":tc},"gio":{"can":cg,"chi":chig},"nhat_chu":cng}

def phan_tich_chuyen_sau(ngay_check: date, gio: int, sinh_info: dict):
    ls = sinh_info["la_so"]
    nc_can = ls["nhat_chu"]
    _, month_chi = get_tiet_khi(ngay_check)
    tt_now = build_tu_tru(ngay_check.year, month_chi, ngay_check, gio)
    jdn = get_jdn(ngay_check.day, ngay_check.month, ngay_check.year)
    
    # Tính Trực và Tú
    truc = TRUC_12[(DIA_CHI.index(tt_now["ngay"]["chi"]) - DIA_CHI.index(month_chi)) % 12]
    tu = TU_28[(jdn + 16) % 28] # Offset chuẩn thiên văn
    
    # Tính Thần Sát
    than_sat = []
    dich_ma_map = {"Thân":"Dần","Tý":"Dần","Thìn":"Dần","Dần":"Thân","Ngọ":"Thân","Tuất":"Thân","Tỵ":"Hợi","Dậu":"Hợi","Sửu":"Hợi","Hợi":"Tỵ","Mão":"Tỵ","Mùi":"Tỵ"}
    if dich_ma_map.get(ls["nam"]["chi"]) == tt_now["ngay"]["chi"]: than_sat.append("🐎 Dịch Mã")
    
    thap_than = tinh_thap_than(nc_can, tt_now["ngay"]["can"])
    diem_hung = 0.0
    if frozenset({tt_now["ngay"]["chi"], ls["ngay"]["chi"]}) in LUC_XUNG: diem_hung += 8
    if thap_than == "Thất Sát": diem_hung += 5

    # Phân loại công việc
    res = {
        "truc": truc, "tu": tu, "than_sat": than_sat, "diem": diem_hung,
        "the_chat": "🟢 Tốt" if diem_hung < 7 else "🔴 Nguy cơ chấn thương",
        "tri_tue": "🌟 Đại cát" if thap_than in ["Thiên Ấn", "Chính Ấn"] else "🟢 Bình thường",
        "tai_chinh": "💰 Thuận lợi" if "Tài" in thap_than else "🔴 Rủi ro" if "Kiếp" in thap_than else "🟢 Ổn định",
        "xay_dung": "🔴 Kỵ" if truc in ["Phá", "Bế", "Chấp"] or frozenset({tt_now["ngay"]["chi"], ls["nam"]["chi"]}) in LUC_XUNG else "✅ Thuận",
        "di_chuyen": "🚗 Cẩn thận" if diem_hung >= 8 else "🟢 Bình an"
    }
    return res

# ============================================================
# BOT HANDLERS
# ============================================================
DB_PATH = "daiky_final.db"
def init_db():
    conn = sqlite3.connect(DB_PATH); conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, data TEXT)"); conn.commit(); conn.close()
def get_data(uid):
    conn = sqlite3.connect(DB_PATH); r = conn.execute("SELECT data FROM users WHERE user_id=?", (str(uid),)).fetchone(); conn.close()
    return json.loads(r[0]) if r else None

NHAP_N, NHAP_T, NHAP_D, NHAP_G = range(4)

async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("🌟 *BOT ĐẠI KỴ 4.0*\n/nhapngaysinh - Cài đặt\n/homnay - Xem ngày\n/ngaydaiky - Xem tháng\n/canhbao - Quét hạn", parse_mode="Markdown")

async def cmd_hom_nay(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: await u.message.reply_text("Gõ /nhapngaysinh trước!"); return
    r = phan_tich_chuyen_sau(date.today(), datetime.now().hour, info)
    msg = f"📅 *HÔM NAY:* Trực {r['truc']} | Tú {r['tu']}\n✨ *Thần sát:* {', '.join(r['than_sat']) if r['than_sat'] else 'Không'}\n"
    msg += f"━━━━━━━━━━━━━━\n🏃 Thể chất: {r['the_chat']}\n🧠 Trí tuệ: {r['tri_tue']}\n💰 Tài chính: {r['tai_chinh']}\n🏗️ Xây dựng: {r['xay_dung']}\n🚗 Di chuyển: {r['di_chuyen']}"
    await u.message.reply_text(msg, parse_mode="Markdown")

async def cmd_ngay_dai_ky(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: await u.message.reply_text("Gõ /nhapngaysinh trước!"); return
    m = int(c.args[0]) if c.args and c.args[0].isdigit() else date.today().month
    y = date.today().year
    msg = [f"📅 *THÁNG {m}/{y}*"]
    curr = date(y, m, 1)
    while curr.month == m:
        r = phan_tich_chuyen_sau(curr, 12, info)
        if r['diem'] >= 7 or r['xay_dung'] == "🔴 Kỵ":
            msg.append(f"• {curr.strftime('%d/%m')}: Trực {r['truc']} - Hung {r['diem']}đ")
        curr += timedelta(days=1)
    await u.message.reply_text("\n".join(msg), parse_mode="Markdown")

async def cmd_canh_bao(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    today = date.today(); warns = []
    for i in range(1, 31):
        d = today + timedelta(days=i)
        r = phan_tich_chuyen_sau(d, 12, info)
        if r['diem'] >= 10: warns.append(f"⚠️ {d.strftime('%d/%m')}: Hạn nặng ({r['diem']}đ)")
    await u.message.reply_text("🚨 *CẢNH BÁO 30 NGÀY:*\n" + ("\n".join(warns) if warns else "An lành."), parse_mode="Markdown")

async def nhap_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("Năm sinh (1995):"); return NHAP_N
async def nhap_n(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data["n"] = int(u.message.text); await u.message.reply_text("Tháng (1-12):"); return NHAP_T
async def nhap_t(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data["t"] = int(u.message.text); await u.message.reply_text("Ngày (1-31):"); return NHAP_D
async def nhap_d(u: Update, c: ContextTypes.DEFAULT_TYPE):
    c.user_data["d"] = int(u.message.text); await u.message.reply_text("Giờ (0-23):"); return NHAP_G
async def nhap_g(u: Update, c: ContextTypes.DEFAULT_TYPE):
    n, t, d, g = c.user_data["n"], c.user_data["t"], c.user_data["d"], int(u.message.text)
    ngay_sinh = date(n, t, d)
    _, tc = get_tiet_khi(ngay_sinh)
    ls = build_tu_tru(n, tc, ngay_sinh, g)
    data = {"n":n,"t":t,"d":d,"g":g,"la_so":ls}
    conn = sqlite3.connect(DB_PATH); conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (str(u.effective_user.id), json.dumps(data))); conn.commit(); conn.close()
    await u.message.reply_text("✅ Đã lưu!"); return ConversationHandler.END

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("nhapngaysinh", nhap_start)],
        states={NHAP_N: [MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_n)],
                NHAP_T: [MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_t)],
                NHAP_D: [MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_d)],
                NHAP_G: [MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_g)]},
        fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)])
    app.add_handler(conv)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("homnay", cmd_hom_nay))
    app.add_handler(CommandHandler("ngaydaiky", cmd_ngay_dai_ky))
    app.add_handler(CommandHandler("canhbao", cmd_canh_bao))
    app.run_polling()

if __name__ == "__main__": main()
