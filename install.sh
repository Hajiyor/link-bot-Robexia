#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
#  LinkPink Bot — Easy Install
#  Usage: bash install.sh
#  Tested on: Ubuntu 20.04+, Debian 11+, CentOS 8+
# ═══════════════════════════════════════════════════════════════════════════════

set -e
trap 'echo -e "\n${RED}[!] خطا در نصب. برای کمک Issue باز کنید.${NC}" >&2' ERR

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "  ${GREEN}✔${NC}  $*"; }
info() { echo -e "  ${CYAN}→${NC}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "  ${RED}✖${NC}  $*"; exit 1; }
step() { echo -e "\n${BOLD}${CYAN}[$1/7]${NC} ${BOLD}$2${NC}"; }

clear
echo -e "${CYAN}"
cat << 'BANNER'
  ██╗     ██╗███╗   ██╗██╗  ██╗    ██████╗  ██████╗ ████████╗
  ██║     ██║████╗  ██║██║ ██╔╝    ██╔══██╗██╔═══██╗╚══██╔══╝
  ██║     ██║██╔██╗ ██║█████╔╝     ██████╔╝██║   ██║   ██║   
  ██║     ██║██║╚██╗██║██╔═██╗     ██╔══██╗██║   ██║   ██║   
  ███████╗██║██║ ╚████║██║  ██╗    ██████╔╝╚██████╔╝   ██║   
  ╚══════╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═════╝  ╚═════╝    ╚═╝   
BANNER
echo -e "${NC}"
echo -e "  ${BOLD}نصب آسان — LinkPink Telegram Bot${NC}"
echo -e "  ─────────────────────────────────────────"
echo ""

# ── 1. Detect OS & Package Manager ────────────────────────────────────────────
step 1 "بررسی سیستم‌عامل"

OS="unknown"; PKG=""
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
fi

case "$OS" in
    ubuntu|debian|linuxmint|pop)   PKG="apt-get"; ok "شناسایی شد: $OS (apt)" ;;
    centos|rhel|fedora|rocky|alma) PKG="yum";     ok "شناسایی شد: $OS (yum)" ;;
    arch|manjaro)                  PKG="pacman";  ok "شناسایی شد: $OS (pacman)" ;;
    *)
        warn "توزیع شناخته‌شده نیست ($OS). تلاش با apt..."
        PKG="apt-get"
        ;;
esac

# ── 2. Install system dependencies ────────────────────────────────────────────
step 2 "نصب ابزارهای سیستم (ffmpeg, aria2, wget, python3)"

install_pkg() {
    case "$PKG" in
        apt-get)
            sudo apt-get update -qq
            sudo apt-get install -y -qq "$@"
            ;;
        yum)
            sudo yum install -y -q "$@" 2>/dev/null || \
            sudo yum install -y "$@"
            ;;
        pacman)
            sudo pacman -Sy --noconfirm "$@"
            ;;
    esac
}

MISSING=()
for tool in python3 ffmpeg aria2c wget curl; do
    if command -v "$tool" &>/dev/null; then
        ok "$tool موجود است"
    else
        MISSING+=("$tool")
        warn "$tool یافت نشد — نصب می‌شود..."
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    # Map tool names to package names
    PKGS=()
    for t in "${MISSING[@]}"; do
        case "$t" in
            aria2c) PKGS+=("aria2") ;;
            python3) PKGS+=("python3" "python3-pip" "python3-venv") ;;
            *) PKGS+=("$t") ;;
        esac
    done

    if sudo -n true 2>/dev/null; then
        install_pkg "${PKGS[@]}"
        ok "ابزارهای سیستم نصب شدند"
    else
        echo ""
        warn "برای نصب ابزارهای زیر نیاز به رمز sudo دارید:"
        echo "     ${PKGS[*]}"
        echo ""
        read -rp "  آیا ادامه دهم؟ (رمز sudo لازم است) [Y/n] " _do_sudo
        [[ "$_do_sudo" =~ ^[Nn]$ ]] && err "لطفاً ابزارها را دستی نصب کنید و دوباره اجرا کنید."
        install_pkg "${PKGS[@]}"
        ok "ابزارهای سیستم نصب شدند"
    fi
fi

# ── 3. Check Python version ───────────────────────────────────────────────────
step 3 "بررسی نسخه Python"

PY_BIN=""
for bin in python3.12 python3.11 python3.10 python3; do
    if command -v "$bin" &>/dev/null; then
        ver=$("$bin" -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')" 2>/dev/null)
        if [ -n "$ver" ] && [ "$ver" -ge 310 ] 2>/dev/null; then
            PY_BIN="$bin"
            PY_VER=$("$bin" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
            ok "Python $PY_VER ($bin)"
            break
        fi
    fi
done

[ -z "$PY_BIN" ] && err "Python 3.10+ یافت نشد. لطفاً از https://python.org نصب کنید."

# ── 4. Collect config interactively ──────────────────────────────────────────
step 4 "تنظیمات بات"

echo ""
echo -e "  ${BOLD}اطلاعات زیر را وارد کنید:${NC}"
echo -e "  (برای پرش از گزینه‌های اختیاری Enter بزنید)"
echo ""

# BOT_TOKEN
while true; do
    read -rp "  🤖 توکن بات (از @BotFather): " BOT_TOKEN
    [[ -n "$BOT_TOKEN" ]] && break
    warn "توکن نمی‌تواند خالی باشد."
done

# ADMIN_ID
while true; do
    echo -e "  ${YELLOW}راهنما:${NC} آیدی عددی خود را از @userinfobot بگیرید"
    read -rp "  👤 آیدی عددی تلگرام شما (Admin): " ADMIN_ID
    [[ "$ADMIN_ID" =~ ^[0-9]+$ ]] && break
    warn "باید فقط عدد باشد. مثال: 123456789"
done

echo ""
echo -e "  ${YELLOW}برای آپلود فایل‌های بالای 50 مگابایت، API Telegram لازم است.${NC}"
echo -e "  از https://my.telegram.org دریافت کنید  (اختیاری)"
read -rp "  🔑 Telegram API ID   [اختیاری — Enter برای رد]: " API_ID
read -rp "  🔑 Telegram API Hash [اختیاری — Enter برای رد]: " API_HASH

echo ""
read -rp "  🌐 پراکسی HTTP (اختیاری — مثال: http://127.0.0.1:8080): " HTTP_PROXY

# ── 5. Create virtualenv & install Python packages ────────────────────────────
step 5 "نصب پکیج‌های Python"

info "ساخت محیط مجازی..."
$PY_BIN -m venv venv
ok "محیط مجازی ساخته شد (venv/)"

info "ارتقاء pip..."
venv/bin/pip install --upgrade pip -q

info "نصب پکیج‌ها (چند دقیقه طول می‌کشد)..."
venv/bin/pip install -r requirements.txt -q \
    --disable-pip-version-check \
    --no-warn-script-location
ok "تمام پکیج‌ها نصب شدند"

# ── 6. Write .env & create directories ────────────────────────────────────────
step 6 "ایجاد فایل تنظیمات"

# Backup existing .env
[ -f .env ] && cp .env ".env.backup.$(date +%s)" && warn "فایل .env قدیمی را پشتیبان گرفتم"

cat > .env << EOF
# ── ضروری ─────────────────────────────────────────────────────────────────────
BOT_TOKEN=${BOT_TOKEN}
ADMIN_IDS=${ADMIN_ID}

# ── تلگرام MTProto (برای فایل‌های بزرگ‌تر از 50MB) ────────────────────────────
TELEGRAM_API_ID=${API_ID}
TELEGRAM_API_HASH=${API_HASH}

# ── پراکسی ────────────────────────────────────────────────────────────────────
HTTP_PROXY=${HTTP_PROXY}

# ── دیتابیس و ذخیره‌سازی ──────────────────────────────────────────────────────
DATABASE_URL=sqlite+aiosqlite:///data/bot.db
STORAGE_PATH=storage

# ── محدودیت‌ها ─────────────────────────────────────────────────────────────────
MAX_FILE_SIZE_MB=4096
MAX_CONCURRENT_DOWNLOADS=5
DOWNLOAD_TIMEOUT=600
MAX_RETRIES=3
RATE_LIMIT_MESSAGES=20
RATE_LIMIT_WINDOW=60

# ── لاگ ───────────────────────────────────────────────────────────────────────
LOG_LEVEL=INFO
LOG_FILE=data/bot.log
EOF
ok "فایل .env ساخته شد"

mkdir -p data storage/downloads data/cookies
ok "پوشه‌های لازم ساخته شدند"

# ── 7. Create helper scripts ──────────────────────────────────────────────────
step 7 "ساخت ابزارهای کمکی"

# start.sh
cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "🤖 در حال اجرای بات..."
python main.py
EOF
chmod +x start.sh
ok "start.sh ساخته شد"

# start_bg.sh (background with auto-restart)
cat > start_bg.sh << 'BGEOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 شروع بات در پس‌زمینه..."

while true; do
    venv/bin/python main.py
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ]; then
        echo "بات متوقف شد (کد 0). راه‌اندازی مجدد نمی‌شود."
        break
    fi
    echo "⚠ بات کرش کرد (کد $EXIT_CODE). 5 ثانیه صبر... راه‌اندازی مجدد"
    sleep 5
done
BGEOF
chmod +x start_bg.sh
ok "start_bg.sh ساخته شد (حالت پس‌زمینه با ری‌استارت خودکار)"

# stop.sh
cat > stop.sh << 'EOF'
#!/bin/bash
PID=$(pgrep -f "python main.py" 2>/dev/null || true)
if [ -n "$PID" ]; then
    kill "$PID"
    echo "✔ بات متوقف شد (PID: $PID)"
else
    echo "بات در حال اجرا نیست."
fi
EOF
chmod +x stop.sh
ok "stop.sh ساخته شد"

# logs.sh
cat > logs.sh << 'EOF'
#!/bin/bash
tail -f data/bot.log
EOF
chmod +x logs.sh
ok "logs.sh ساخته شد"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          🎉  نصب با موفقیت انجام شد!                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}دستورات مفید:${NC}"
echo ""
echo -e "  ${CYAN}bash start.sh${NC}         — اجرای بات (حالت عادی)"
echo -e "  ${CYAN}bash start_bg.sh &${NC}    — اجرا در پس‌زمینه با ری‌استارت خودکار"
echo -e "  ${CYAN}bash stop.sh${NC}          — توقف بات"
echo -e "  ${CYAN}bash logs.sh${NC}          — نمایش لاگ زنده"
echo -e "  ${CYAN}nano .env${NC}             — ویرایش تنظیمات"
echo ""

read -rp "  همین الان بات را اجرا کنم؟ [Y/n] " _start
if [[ ! "$_start" =~ ^[Nn]$ ]]; then
    echo ""
    info "در حال اجرا..."
    echo ""
    bash start.sh
fi
