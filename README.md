# LinkPink Bot 🎀

A Telegram bot that downloads media from YouTube, Instagram, Twitter/X, Spotify, SoundCloud, GitHub, Google Play, magnet links, and direct URLs — then sends the file back to the user.

## Features

- **YouTube** — video (up to 4K) and audio (MP3 320kbps)
- **Instagram** — posts, reels, stories
- **Twitter/X** — videos and images
- **Spotify** — tracks, albums, playlists (via spotdl → YouTube Music)
- **SoundCloud** — tracks and playlists
- **Apple Music** — tracks (via yt-dlp)
- **GitHub** — releases and repository archives
- **Google Play** — APK download via APKPure
- **Torrent** — `.torrent` files and `magnet:` links (4 GB limit, real-time progress)
- **Direct links** — any direct download URL
- **Cookie support** — Netscape cookies for age-restricted / login-gated content
- **Large file upload** — files up to 4 GB via Pyrogram MTProto
- **Cancel button** — cancel any active download/upload
- **Psiphon proxy fallback** — automatic retry through Psiphon if direct download fails

## Quick Start

```bash
git clone https://github.com/your-username/linkpink-bot
cd linkpink-bot
bash setup.sh
```

The setup script will ask for your bot token and admin ID, install all dependencies, and start the bot.

## Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env — set BOT_TOKEN and ADMIN_IDS at minimum

# 4. Run
python main.py
```

## System Requirements

- Python 3.10+
- `ffmpeg` — video/audio processing
- `aria2c` — multi-connection downloads and torrent support
- `wget` — primary download tool

Install on Ubuntu/Debian:
```bash
sudo apt install ffmpeg aria2c wget
```

## Configuration

Copy `.env.example` to `.env` and fill in the values:

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | From @BotFather |
| `ADMIN_IDS` | ✅ | Your numeric Telegram user ID |
| `TELEGRAM_API_ID` | For >50 MB files | From https://my.telegram.org |
| `TELEGRAM_API_HASH` | For >50 MB files | From https://my.telegram.org |
| `REDIS_URL` | Optional | Enables FSM persistence and faster rate limiting |
| `HTTP_PROXY` | Optional | e.g. `http://host:port` |

## Commands

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/help` | Usage guide |
| `/stats` | Message statistics |
| `/setcookie` | Upload cookies.txt for protected content |
| `/delcookie` | Delete saved cookies |
| `/checkcookie` | Show active cookie info |

## Open Source Credits

This bot is built on top of these excellent open source projects:

| Project | License | Used for |
|---|---|---|
| [aiogram](https://github.com/aiogram/aiogram) | MIT | Telegram Bot API framework |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Unlicense | YouTube, Instagram, Twitter, SoundCloud downloads |
| [spotdl](https://github.com/spotDL/spotify-downloader) | MIT | Spotify track/playlist downloads via YouTube Music |
| [gallery-dl](https://github.com/mikf/gallery-dl) | GPL-2.0 | Fallback for image gallery sites |
| [Pyrogram](https://github.com/pyrogram/pyrogram) | LGPL-3.0 | MTProto client for large file (>50 MB) uploads |
| [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy) | MIT | Async database ORM |
| [httpx](https://github.com/encode/httpx) | BSD | Async HTTP client |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | BSD | `.env` file loading |
| [aria2](https://github.com/aria2/aria2) | GPL-2.0 | Multi-connection downloader and torrent engine (system tool) |
| [FFmpeg](https://ffmpeg.org) | LGPL/GPL | Video/audio processing (system tool) |
| [Psiphon](https://github.com/Psiphon-Labs/psiphon-tunnel-core) | GPL-3.0 | Censorship-circumvention proxy fallback |

## License

MIT
