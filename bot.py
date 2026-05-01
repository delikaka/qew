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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# TOÁN HỌC TỨ TRỤ
# ============================================================
THIEN_CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
DIA_CHI   = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]

NGU_HANH_CAN = {"Giáp": "Mộc", "Ất": "Mộc", "Bính": "Hỏa", "Đinh": "Hỏa", "Mậu": "Thổ", "Kỷ": "Thổ", "Canh": "Kim", "Tân": "Kim", "Nhâm": "Thủy", "Quý": "Thủy"}
AM_DUONG_CAN = {"Giáp": "Dương", "Ất": "Âm", "Bính": "Dương", "Đinh": "Âm", "Mậu": "Dương", "Kỷ": "Âm", "Canh": "Dương", "Tân": "Âm", "Nhâm": "Dương", "Quý": "Âm"}
TUONG_SINH = {"Mộc": "Hỏa", "Hỏa": "Thổ", "Thổ": "Kim", "Kim": "Thủy", "Thủy": "Mộc"}
TUONG_KHAC = {"Mộc": "Thổ", "Thổ": "Thủy", "Thủy": "Hỏa", "Hỏa": "Kim", "Kim": "Mộc"}

LUC_XUNG = {frozenset({"Tý", "Ngọ"}), frozenset({"Sửu", "Mùi"}), frozenset({"Dần", "Thân"}), frozenset({"Mão", "Dậu"}), frozenset({"Thìn", "Tuất"}), frozenset({"Tỵ", "Hợi"})}
THAP_THAN_XAU = {"Thất Sát", "Thương Quan", "Kiếp Tài"}

def tinh_thap_than(nhat_chu, can_check):
    nh_chu, nh_check = NGU_HANH_CAN[nhat_chu], NGU_HANH_CAN[can_check]
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
        if ngay >= date(ngay.year, m, d): t = name; break
    MAP = {"Lập Xuân":"Dần","Kinh Trập":"Mão","Thanh Minh":"Thìn","Lập Hạ":"Tỵ","Mang Chủng":"Ngọ","Tiểu Thử":"Mùi","Lập Thu":"Thân","Bạch Lộ":"Dậu","Hàn Lộ":"Tuất","Lập Đông":"Hợi","Đại Tuyết":"Tý","Tiểu Hàn":"Sửu"}
    return t, MAP.get(t, "Dần")

def build_tu_tru(nam, tc, ngay, gio):
    # Can Chi Năm
    cn = THIEN_CAN[(nam-4)%10]; chin = DIA_CHI[(nam-4)%12]
    # Can Chi Ngày (Gốc 01/01/1900 là Giáp Tuất)
    d_diff = (ngay - date(1900,1,1)).days
    cng = THIEN_CAN[(d_diff + 10) % 10]; ching = DIA_CHI[(d_diff + 10) % 12]
    # Can Giờ (Logic: Giáp Kỷ khởi Giáp Tý)
    idx_ngay = (d_diff + 10) % 10
    start_can_gio = (idx_ngay % 5) * 2
    idx_gio = (gio + 1) // 2
    cg = THIEN_CAN[(start_can_gio + idx_gio) % 10]
    chig = DIA_CHI[idx_gio % 12]
    return {"nam":{"can":cn,"chi":chin},"ngay":{"can":cng,"chi":ching},"thang":{"chi":tc},"gio":{"can":cg,"chi":chig},"nhat_chu":cng}

def phan_tich_ngay(ngay_check: date, gio: int, sinh_info: dict):
    ls = sinh_info["la_so"]
    nhat_chu = ls["nhat_chu"]
    _, t_chi = get_tiet_khi(ngay_check)
    tt_now = build_tu_tru(ngay_check.year, t_chi, ngay_check, gio)
    
    diem_hung = 0.0
    chi_tiet = []
    xung_count = 0
    
    # Ma trận trọng số (Weight Matrix)
    # Tọa độ: (Tên Trụ, Chi Trụ, Hệ số Ưu tiên)
    check_list = [("Ngày", tt_now["ngay"]["chi"], 1.5), ("Giờ", tt_now["gio"]["chi"], 0.8), ("Tháng", tt_now["thang"]["chi"], 1.0), ("Năm", tt_now["nam"]["chi"], 1.2)]
    targets = [("Nhật Chủ", ls["ngay"]["chi"], 8), ("Trụ Năm", ls["nam"]["chi"], 5)]

    for n_now, c_now, p_coeff in check_list:
        for n_tar, c_tar, weight in targets:
            if frozenset({c_now, c_tar}) in LUC_XUNG:
                score = weight * p_coeff
                diem_hung += score; xung_count += 1
                chi_tiet.append(f"🔥 {n_now} xung {n_tar} ({c_now}-{c_tar})")

    # Thập Thần Can Ngày
    tt_can = tinh_thap_than(nhat_chu, tt_now["ngay"]["can"])
    if tt_can in THAP_THAN_XAU:
        diem_hung += 4; chi_tiet.append(f"⚠️ Can Ngày gặp {tt_can}")

    # Bonus Đồng Phase (Toán học xác suất nguy hiểm)
    if xung_count >= 2: diem_hung += 5

    if diem_hung >= 15: muc = "🔴 CỰC NẶNG"
    elif diem_hung >= 10: muc = "🟠 RẤT NẶNG"
    elif diem_hung >= 5: muc = "🟡 TRUNG BÌNH"
    else: muc = "✅ BÌNH THƯỜNG"

    return {"diem": round(diem_hung, 1), "muc": muc, "detail": chi_tiet, "is_xung": (xung_count > 0)}

# ============================================================
# BOT COMMANDS & DB
# ============================================================
DB_PATH = "daiky.db"
def init_db():
    conn = sqlite3.connect(DB_PATH); conn.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, data TEXT)"); conn.commit(); conn.close()

async def cmd_canh_bao(u: Update, c: ContextTypes.DEFAULT_TYPE):
    user_id = str(u.effective_user.id)
    conn = sqlite3.connect(DB_PATH); r = conn.execute("SELECT data FROM users WHERE user_id=?", (user_id,)).fetchone(); conn.close()
    if not r: await u.message.reply_text("❌ Dùng /nhapngaysinh trước."); return
    
    info = json.loads(r[0]); today = date.today(); warns = []
    await u.message.reply_text("⏳ Đang tính toán Ma trận Hung Index 30 ngày tới...")
    
    for i in range(1, 31):
        d = today + timedelta(days=i); res = phan_tich_ngay(d, 12, info)
        if res["diem"] >= 10:
            warns.append(f"📅 *{d.strftime('%d/%m')}* ({res['diem']}đ): {res['muc']}\n   ↳ {', '.join(res['detail'])}")
    
    header = "⚠️ *CẢNH BÁO TRỌNG ĐIỂM (30 NGÀY)*\n━━━━━━━━━━━━━━\n"
    await u.message.reply_text(header + "\n\n".join(warns) if warns else header + "✅ Không có ngày biến động mạnh.", parse_mode="Markdown")

# (Các hàm /nhapngaysinh, /homnay, /ngaydaiky... giữ logic phan_tich_ngay như trên)
# ... [Lược bỏ phần lặp lại của Turn trước để tiết kiệm không gian] ...

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    # Thêm các handler ở đây tương tự file trước
    app.add_handler(CommandHandler("canhbao", cmd_canh_bao))
    # ...
    app.run_polling()

if __name__ == "__main__": main()
