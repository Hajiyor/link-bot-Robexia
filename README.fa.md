# 🤖 LinkPink Bot — راهنمای نصب آسان

ربات تلگرام برای دانلود از یوتیوب، اینستاگرام، توییتر، اسپاتیفای، تورنت و لینک‌های مستقیم.

---

## ⚡ نصب یک‌دستوری (پیشنهادی)

```bash
git clone https://github.com/Hajiyor/link-bot-Robexia
cd link-bot-Robexia
bash install.sh
```

اسکریپت به‌صورت خودکار:
- تمام ابزارهای سیستم را نصب می‌کند (`ffmpeg`, `aria2`, `wget`)
- محیط Python مجازی می‌سازد
- پکیج‌ها را نصب می‌کند
- تنظیمات را از شما می‌پرسد و فایل `.env` می‌سازد
- اسکریپت‌های کمکی `start.sh` / `stop.sh` / `logs.sh` می‌سازد

---

## 📋 پیش‌نیازها

| چیزی که نیاز دارید | از کجا بگیرید |
|---|---|
| **توکن بات** | از [@BotFather](https://t.me/BotFather) |
| **آیدی عددی تلگرام** | از [@userinfobot](https://t.me/userinfobot) |
| _(اختیاری)_ API ID/Hash | از [my.telegram.org](https://my.telegram.org) — فقط برای فایل‌های بالای 50MB |

---

## 🖥️ سیستم‌عاملهای پشتیبانی‌شده

- ✅ Ubuntu 20.04+
- ✅ Debian 11+
- ✅ CentOS / Rocky / AlmaLinux 8+
- ✅ Arch / Manjaro
- ✅ Python 3.10+

---

## 🚀 اجرا

```bash
# اجرای عادی
bash start.sh

# اجرا در پس‌زمینه (با ری‌استارت خودکار در صورت کرش)
bash start_bg.sh &

# مشاهده لاگ زنده
bash logs.sh

# توقف بات
bash stop.sh
```

---

## ⚙️ تنظیمات

فایل `.env` را ویرایش کنید:

```bash
nano .env
```

| متغیر | اجباری | توضیح |
|---|---|---|
| `BOT_TOKEN` | ✅ | توکن از @BotFather |
| `ADMIN_IDS` | ✅ | آیدی عددی تلگرام شما |
| `TELEGRAM_API_ID` | فقط برای >50MB | از my.telegram.org |
| `TELEGRAM_API_HASH` | فقط برای >50MB | از my.telegram.org |
| `HTTP_PROXY` | اختیاری | مثال: `http://127.0.0.1:8080` |
| `REDIS_URL` | اختیاری | برای پایداری بیشتر FSM |

---

## 🔧 نصب دستی (اگر اسکریپت کار نکرد)

```bash
# 1. نصب ابزارهای سیستم
sudo apt install ffmpeg aria2 wget python3 python3-pip python3-venv

# 2. ساخت محیط مجازی
python3 -m venv venv
source venv/bin/activate

# 3. نصب پکیج‌ها
pip install -r requirements.txt

# 4. ساخت فایل تنظیمات
cp .env.example .env   # یا دستی بسازید
nano .env

# 5. اجرا
python main.py
```

---

## ❓ مشکلات رایج

**خطا: `BOT_TOKEN not found`**
→ مطمئن شوید فایل `.env` ساخته شده و توکن در آن درست است.

**خطا: `ffmpeg not found`**
→ دستور زیر را اجرا کنید: `sudo apt install ffmpeg`

**فایل‌های بالای 50MB آپلود نمی‌شوند**
→ `TELEGRAM_API_ID` و `TELEGRAM_API_HASH` را از [my.telegram.org](https://my.telegram.org) بگیرید و در `.env` بگذارید.

**بات کرش می‌کند**
→ لاگ را بررسی کنید: `bash logs.sh` یا `cat data/bot.log`

---

## 📦 امکانات

- 🎬 یوتیوب — ویدیو تا 4K و صدا MP3 320kbps
- 📸 اینستاگرام — پست، ریلز، استوری
- 🐦 توییتر/X — ویدیو و تصویر
- 🎵 اسپاتیفای — آهنگ، آلبوم، پلی‌لیست
- 🎶 SoundCloud — آهنگ و پلی‌لیست
- 🧲 تورنت — فایل `.torrent` و لینک magnet (حداکثر 4GB)
- 🔗 لینک مستقیم — هر URL دانلودی
- 🚫 دکمه لغو — توقف دانلود در هر لحظه

---

## 📄 لایسنس

MIT
