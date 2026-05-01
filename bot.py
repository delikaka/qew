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
# CONFIG & LOGGING [Giữ nguyên cite: 1, 2]
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# TOÁN HỌC TỨ TRỤ NÂNG CAO [Giữ nguyên cite: 1, 2]
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
# HÀM TÍNH TOÁN LOGIC GỐC [Giữ nguyên cite: 1, 2]
# ------------------------------------------------------------
def tinh_thap_than(nhat_chu, can_check):
    if nhat_chu not in NGU_HANH or can_check not in NGU_HANH: return "N/A"
    nh_chu, nh_check = NGU_HANH[nhat_chu], NGU_HANH[can_check]
    cung_ad = (AM_DUONG_CAN[nhat_chu] == AM_DUONG_CAN[can_check])
    if nh_check == nh_chu: return "Kiếp Tài" if cung_ad else "Tỷ Kiên"
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
    idx_ngay = (d_diff + 10) % 10
    start_can_gio = (idx_ngay % 5) * 2
    idx_gio = (gio + 1) // 2
    cg = THIEN_CAN[(start_can_gio + idx_gio) % 10]; chig = DIA_CHI[idx_gio % 12]
    return {"nam":{"can":cn,"chi":chin},"ngay":{"can":cng,"chi":ching},"thang":{"chi":tc},"gio":{"can":cg,"chi":chig},"nhat_chu":cng}

def get_season_multiplier(month_chi, day_chi):
    day_nh = NGU_HANH.get(day_chi)
    seasons = {"Mộc":["Dần","Mão","Thìn"],"Hỏa":["Tỵ","Ngọ","Mùi"],"Kim":["Thân","Dậu","Tuất"],"Thủy":["Hợi","Tý","Sửu"]}
    vuong_element = next((k for k, v in seasons.items() if month_chi in v), None)
    return 1.3 if day_nh == vuong_element else 1.0

# ------------------------------------------------------------
# LOGIC CHUYÊN GIA BỔ SUNG [Dựa trên toán học hệ số]
# ------------------------------------------------------------
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
    
    s_trade = 5.0 + (3.5 * suc_manh if thap_than in ["Thiên Tài", "Chính Tài"] else -3.0 if thap_than == "Kiếp Tài" else 0)
    if frozenset({chi_ngay, ls["ngay"]["chi"]}) in LUC_XUNG: s_trade -= 2.5

    s_study = 5.0 + (3.0 if thap_than in ["Chính Ấn", "Thiên Ấn"] else 0) + (1.0 if NGU_HANH[chi_ngay] in ["Thủy", "Mộc"] else 0)

    s_move = 5.0 + (4.5 if chi_ngay in [get_dich_ma(ls["nam"]["chi"]), get_dich_ma(ls["ngay"]["chi"])] else 0)
    if frozenset({chi_ngay, ls["ngay"]["chi"]}) in LUC_XUNG: s_move -= 4.0
    
    return {k: round(max(0, min(10, v)), 1) for k, v in {"trading": s_trade, "study": s_study, "move": s_move}.items()}

def phan_tich_ngay_sau(ngay_check: date, gio: int, sinh_info: dict):
    ls = sinh_info["la_so"]
    nhat_chu_can = ls["nhat_chu"]
    _, month_chi = get_tiet_khi(ngay_check)
    tt_now = build_tu_tru(ngay_check.year, month_chi, ngay_check, gio)
    
    diem_hung = 0.0; chi_tiet = []
    check_list = [("Ngày", tt_now["ngay"]["chi"], 1.5), ("Năm", tt_now["nam"]["chi"], 1.2)]
    targets = [("Nhật Chủ", ls["ngay"]["chi"], 8), ("Trụ Năm", ls["nam"]["chi"], 5)]

    for n_now, c_now, p_coeff in check_list:
        for n_tar, c_tar, weight in targets:
            if frozenset({c_now, c_tar}) in LUC_XUNG:
                current_score = weight * p_coeff * get_season_multiplier(month_chi, c_now)
                is_saved = any(frozenset({c_now, other}) in LUC_HOP for _, other, _ in check_list if other != c_now)
                if is_saved: chi_tiet.append(f"🛡️ {n_now} Xung {n_tar} nhưng có Hợp giải")
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
# DB & BOT HANDLERS [Phục hồi 100% văn phong gốc]
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
            await u.message.reply_text(f"❌ Lỗi: Ngày {d}/{t}/{n} không tồn tại trên lịch (chắc là tháng 2 hoặc tháng thiếu). Gõ /nhapngaysinh để làm lại!"); return ConversationHandler.END
        _, tc = get_tiet_khi(ngay_sinh); ls = build_tu_tru(n, tc, ngay_sinh, g)
        conn = sqlite3.connect(DB_PATH); conn.execute("INSERT OR REPLACE INTO users VALUES (?,?)", (str(u.effective_user.id), json.dumps({"n":n,"t":t,"d":d,"g":g,"la_so":ls}))); conn.commit(); conn.close()
        await u.message.reply_text("✅ Xong! Cấu hình thành công. Giờ gõ /canhbao hoặc /ngaydaiky để xem hạn nhé."); return ConversationHandler.END
    except ValueError: await u.message.reply_text("Lại gõ chữ à? Hãy nhập GIỜ bằng số (0-23):"); return NHAP_G

async def cmd_canh_bao(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: await u.message.reply_text("Mày chưa nhập thông tin! Gõ /nhapngaysinh đi đã."); return
    today = date.today(); warns = []
    for i in range(1, 31):
        d = today + timedelta(days=i); res = phan_tich_ngay_sau(d, 12, info)
        if res["is_dangerous"]: warns.append(f"📅 *{d.strftime('%d/%m')}* ({res['diem']}đ): {res['muc']}\n   ↳ {', '.join(res['detail'])}")
    await u.message.reply_text("⚠️ *QUÉT 30 NGÀY TỚI*\n━━━━━━━━━━━━━━\n\n" + ("\n\n".join(warns) if warns else "✅ Mọi sự bình an, không thấy hạn nặng."), parse_mode="Markdown")

async def cmd_ngay_dai_ky(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: await u.message.reply_text("Mày chưa nhập thông tin! Gõ /nhapngaysinh đi đã."); return
    m = int(c.args[0]) if c.args and c.args[0].isdigit() else date.today().month
    y = 2026; msg = [f"📅 *NGÀY XUNG THÁNG {m}/{y}*\n━━━━━━━━━━━━━━"]; curr = date(y, m, 1); found = False
    while curr.month == m:
        res = phan_tich_ngay_sau(curr, 12, info)
        if res["is_dangerous"]: msg.append(f"• *{curr.strftime('%d/%m')}*: {res['muc']} ({res['diem']}đ)"); found = True
        curr += timedelta(days=1)
    if not found: msg.append("✅ Không có ngày xung nặng.")
    await u.message.reply_text("\n".join(msg), parse_mode="Markdown")

async def cmd_hom_nay(u: Update, c: ContextTypes.DEFAULT_TYPE):
    info = get_data(u.effective_user.id)
    if not info: await u.message.reply_text("Mày chưa nhập thông tin! Gõ /nhapngaysinh đi đã."); return
    res = phan_tich_ngay_sau(date.today(), datetime.now().hour, info); exp = phan_tich_chuyen_gia_3_mon(date.today(), info["la_so"])
    def bar(s): return "🟢" * int(s/2) + "⚪" * (5 - int(s/2))
    txt = f"☀️ *KHÍ VẬN HIỆN TẠI:*\n━━━━━━━━━━\n📊 *Chỉ số năng lượng (Thang 10):*\n💰 Trading: {exp['trading']} {bar(exp['trading'])}\n📚 Học tập: {exp['study']} {bar(exp['study'])}\n🚗 Di chuyển: {exp['move']} {bar(exp['move'])}\n\n*Kết quả:* {res['muc']} ({res['diem']}đ)\n" + "\n".join(res['detail'])
    await u.message.reply_text(txt, parse_mode="Markdown")

def main():
    if not BOT_TOKEN: return
    init_db(); app = Application.builder().token(BOT_TOKEN).build()
    conv = ConversationHandler(entry_points=[CommandHandler("nhapngaysinh", nhap_start)], states={NHAP_N:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_n)], NHAP_T:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_t)], NHAP_D:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_d)], NHAP_G:[MessageHandler(filters.TEXT & ~filters.COMMAND, nhap_g)]}, fallbacks=[CommandHandler("cancel", lambda u,c: ConversationHandler.END)])
    app.add_handler(conv); app.add_handler(CommandHandler("start", cmd_start)); app.add_handler(CommandHandler("canhbao", cmd_canh_bao)); app.add_handler(CommandHandler("ngaydaiky", cmd_ngay_dai_ky)); app.add_handler(CommandHandler("homnay", cmd_hom_nay)); app.run_polling()

if __name__ == "__main__": main()
