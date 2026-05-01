# 🌟 BOT TỨ TRỤ ĐẠI KỴ — HƯỚNG DẪN CÀI ĐẶT

## Tính năng
- ✅ Tứ Trụ đầy đủ: Năm + Tháng + Ngày + Giờ (Can Chi)
- ✅ Thập Thần: Thất Sát, Thương Quan, Kiếp Tài (xấu) / Chính Ấn, Chính Quan... (tốt)
- ✅ Tử Vi: La Hầu, Kế Đô, Thái Tuế, Bạch Hổ, Quan Phù
- ✅ Tiết Khí 24 tiết — Vượng/Suy Nhật Chủ (Vượng > Tướng > Hưu > Tù > Tử)
- ✅ Lục Xung, Lục Hại, Tam Hình
- ✅ **Đồng Phase 4 Khung** (Giờ+Ngày+Tháng+Năm cùng xấu = cực nguy)
- ✅ Cảnh báo inline trong list tháng (còn X ngày)

---

## BƯỚC 1: Tạo Bot Telegram

1. Mở Telegram → tìm **@BotFather**
2. Gõ `/newbot`
3. Đặt tên bot (vd: `Tứ Trụ Đại Kỵ Bot`)
4. Đặt username (vd: `TuTruDaiKyBot`)
5. **Copy Token** — trông như: `1234567890:ABCdef...`

---

## BƯỚC 2: Cài đặt Python

```bash
# Yêu cầu Python 3.10+
python --version

# Tạo môi trường ảo (khuyến nghị)
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# Cài thư viện
pip install -r requirements.txt
```

---

## BƯỚC 3: Điền Token vào bot.py

Mở file `bot.py`, tìm dòng:
```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
```
Thay bằng token thật của mày, ví dụ:
```python
BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ"
```

---

## BƯỚC 4: Chạy bot

```bash
python bot.py
```

Thấy log `Bot đang chạy...` là OK.

---

## BƯỚC 5: Dùng bot

Mở Telegram → chat với bot của mày:

| Lệnh | Mô tả |
|------|-------|
| `/start` | Menu chính |
| `/nhapngaysinh` | Nhập ngày/tháng/năm/giờ sinh |
| `/bamenh` | Xem lá số Tứ Trụ đầy đủ |
| `/homnay` | Phân tích hôm nay theo giờ thực |
| `/ngaydaiky` | Ngày đại kỵ tháng này |
| `/ngaydaiky 8` | Ngày đại kỵ tháng 8 |
| `/ngaydaikynam 2025` | Tổng quan cả năm |
| `/canhbao` | Cảnh báo ngày xấu trong tháng còn lại |
| `/help` | Hướng dẫn chi tiết hệ thống tính điểm |

---

## LOGIC TÍNH ĐIỂM

### Thang điểm
| Mức | Điểm | Ý nghĩa |
|-----|------|---------|
| 🔴 Cực kỳ nặng | ≥ 15 | Tuyệt đối tránh quyết định lớn |
| 🟠 Rất nặng | 9–14 | Thận trọng tối đa |
| 🟡 Trung bình | 5–8 | Cẩn thận |
| 🟢 Nhẹ | 2–4 | Chú ý nhỏ |
| ✅ Bình thường | 0–1 | OK |

### Nguồn điểm xấu
- Thập Thần xấu (Thất Sát / Thương Quan / Kiếp Tài): **+2đ/trụ**
- Lục Xung / Lục Hại / Tam Hình địa chi vs bản mệnh: **+3đ/cặp**
- Sao xấu Tử Vi (La Hầu, Kế Đô, Thái Tuế, Bạch Hổ): **+2đ**
- Nhật Chủ Tử (cực suy): **+3đ**
- Nhật Chủ Tù (suy): **+2đ**
- Nhật Chủ Vượng: **-1đ** (giảm hung khí)

### Đồng Phase
- **4 khung** (Giờ + Ngày + Tháng + Năm đều xấu): **+10đ** 🚨🚨
- **3 khung**: **+5đ** ⚠️⚠️

---

## CHẠY 24/7 TRÊN SERVER (tùy chọn)

```bash
# Dùng screen (Linux)
screen -S daiky_bot
python bot.py
# Ctrl+A+D để thoát khỏi screen, bot vẫn chạy

# Hoặc dùng systemd service
# Hoặc deploy lên Railway/Render/VPS
```

---

## CẤU TRÚC FILE
```
daiky_bot/
├── bot.py          ← Code chính
├── requirements.txt
├── README.md
└── user_data.json  ← Tự tạo khi có người dùng đầu tiên
```
