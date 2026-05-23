#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# LinkPink Bot — One-command setup
# Usage: bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        LinkPink Bot — Setup          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

# ── 1. Check Python ───────────────────────────────────────────────────────────
info "Checking Python..."
if ! command -v python3 &>/dev/null; then
    error "Python 3.10+ is required. Install it and re-run."
fi
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    error "Python 3.10+ required (found $PY_VERSION)"
fi
success "Python $PY_VERSION"

# ── 2. Check system tools ─────────────────────────────────────────────────────
info "Checking system tools..."
MISSING=()
for tool in ffmpeg aria2c wget; do
    if command -v "$tool" &>/dev/null; then
        success "$tool found"
    else
        MISSING+=("$tool")
        warn "$tool not found"
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    warn "Missing tools: ${MISSING[*]}"
    echo "Install with:"
    echo "  Ubuntu/Debian: sudo apt install ${MISSING[*]}"
    echo "  CentOS/RHEL:   sudo yum install ${MISSING[*]}"
    echo ""
    read -rp "Continue anyway? [y/N] " cont
    [[ "$cont" =~ ^[Yy]$ ]] || exit 1
fi

# ── 3. Collect config ─────────────────────────────────────────────────────────
echo ""
info "Configuration"
echo "─────────────────────────────────────"

while true; do
    read -rp "Telegram Bot Token (from @BotFather): " BOT_TOKEN
    [[ -n "$BOT_TOKEN" ]] && break
    warn "Token cannot be empty."
done

while true; do
    read -rp "Your Telegram User ID (numeric, from @userinfobot): " ADMIN_ID
    [[ "$ADMIN_ID" =~ ^[0-9]+$ ]] && break
    warn "Must be a numeric ID."
done

echo ""
echo "For files > 50 MB, Pyrogram (MTProto) is required."
echo "Get API credentials at https://my.telegram.org"
read -rp "Telegram API ID   (press Enter to skip): " API_ID
read -rp "Telegram API Hash (press Enter to skip): " API_HASH
echo ""
read -rp "HTTP Proxy (e.g. http://host:port, press Enter to skip): " HTTP_PROXY

# ── 4. Create virtualenv ──────────────────────────────────────────────────────
echo ""
info "Creating virtual environment..."
python3 -m venv venv
success "venv created"

# ── 5. Install dependencies ───────────────────────────────────────────────────
info "Installing Python packages (this may take a few minutes)..."
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q
success "Packages installed"

# ── 6. Write .env ─────────────────────────────────────────────────────────────
info "Writing .env..."
cat > .env << EOF
BOT_TOKEN=${BOT_TOKEN}
ADMIN_IDS=${ADMIN_ID}
TELEGRAM_API_ID=${API_ID}
TELEGRAM_API_HASH=${API_HASH}
HTTP_PROXY=${HTTP_PROXY}
DATABASE_URL=sqlite+aiosqlite:///data/bot.db
STORAGE_PATH=storage
MAX_FILE_SIZE_MB=4096
MAX_CONCURRENT_DOWNLOADS=5
DOWNLOAD_TIMEOUT=600
MAX_RETRIES=3
RATE_LIMIT_MESSAGES=20
RATE_LIMIT_WINDOW=60
LOG_LEVEL=INFO
LOG_FILE=data/bot.log
EOF
success ".env created"

# ── 7. Create directories ─────────────────────────────────────────────────────
mkdir -p data storage/downloads data/cookies
success "Directories created"

# ── 8. Start ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Setup Complete! ✅              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "Start the bot:      venv/bin/python main.py"
echo "Background mode:    nohup venv/bin/python main.py > data/bot.log 2>&1 &"
echo "View logs:          tail -f data/bot.log"
echo ""

read -rp "Start the bot now? [Y/n] " start_now
if [[ ! "$start_now" =~ ^[Nn]$ ]]; then
    info "Starting bot..."
    venv/bin/python main.py
fi
