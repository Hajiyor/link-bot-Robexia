"""
Bot Message Handlers
"""

import asyncio
import time
import uuid
import shutil
import logging
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from services.stats_reporter import track_message
from services.link_detector import detect_link, extract_urls, SourceType
from bot.keyboards import format_selection_keyboard, quality_keyboard

logger = logging.getLogger(__name__)
router = Router()

_active_tasks: dict[str, asyncio.Task] = {}

# In-memory URL store (hash → (data, expire_time))
_url_store: dict[str, tuple[dict, float]] = {}
_URL_TTL = 3600


def _store_url(url_hash: str, url: str, source: str, media_type: str):
    _url_store[url_hash] = (
        {"url": url, "source": source, "media_type": media_type},
        time.time() + _URL_TTL,
    )


def _load_url(url_hash: str) -> dict | None:
    entry = _url_store.get(url_hash)
    if entry and entry[1] > time.time():
        return entry[0]
    return None


def _cancel_kb(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ لغو", callback_data=f"dl_cancel:{task_id}")
    ]])


def _bar(pct: float, width: int = 18) -> str:
    filled = int(width * pct / 100)
    return "█" * filled + "░" * (width - filled)


# ── /start ────────────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(msg: Message):
    track_message()
    await msg.answer(
        "🤖 <b>ربات دانلود و مدیریت فایل</b>\n\n"
        "لینک مورد نظر را ارسال کنید:\n\n"
        "📹 YouTube | 📸 Instagram | 🐦 Twitter/X\n"
        "🎵 Spotify | ☁️ SoundCloud | 🍎 Apple Music\n"
        "🐙 GitHub | 🌐 لینک مستقیم | 🧲 Torrent/Magnet\n\n"
        "دستورات: /help | /stats | /setcookie",
    )


@router.message(Command("help"))
async def cmd_help(msg: Message):
    await msg.answer(
        "📖 <b>راهنما</b>\n\n"
        "• لینک را مستقیماً ارسال کنید\n"
        "• کیفیت و فرمت دانلود را انتخاب کنید\n"
        "• فایل دانلود‌شده را دریافت کنید\n\n"
        "<b>قالب‌های پشتیبانی:</b>\n"
        "MP4 | MP3 | ZIP | APK | و بیشتر\n\n"
        "<b>دستورات:</b>\n"
        "/start — شروع\n"
        "/stats — آمار\n"
        "/setcookie — تنظیم کوکی برای دانلود محتوای محافظت‌شده\n"
        "/delcookie — حذف کوکی\n"
        "/checkcookie — بررسی کوکی فعال",
    )


# ── Main URL handler ───────────────────────────────────────────────────────────

@router.message(F.text)
async def handle_url(msg: Message):
    track_message()
    urls = extract_urls(msg.text or "")

    if not urls:
        if msg.text and msg.text.startswith("magnet:"):
            urls = [msg.text.strip()]
        else:
            return

    url = urls[0]
    detected = detect_link(url)

    if detected.source == SourceType.UNKNOWN:
        await msg.answer("❌ لینک شناسایی نشد. لطفاً یک لینک معتبر ارسال کنید.")
        return

    from bot.keyboards import _url_hash
    h = _url_hash(url)
    _store_url(h, url, detected.source.value, detected.media_type)

    source_labels = {
        SourceType.YOUTUBE:     "🎬 YouTube",
        SourceType.INSTAGRAM:   "📸 Instagram",
        SourceType.TWITTER:     "🐦 Twitter/X",
        SourceType.SPOTIFY:     "🎵 Spotify",
        SourceType.SOUNDCLOUD:  "☁️ SoundCloud",
        SourceType.APPLE_MUSIC: "🍎 Apple Music",
        SourceType.GOOGLE_PLAY: "▶️ Google Play",
        SourceType.GITHUB:      "🐙 GitHub",
        SourceType.TORRENT:     "🧲 Torrent",
        SourceType.DIRECT:      "🌐 لینک مستقیم",
    }

    label = source_labels.get(detected.source, "🔗 لینک")
    await msg.answer(
        f"✅ {label} شناسایی شد\n\n"
        f"<code>{url[:80]}{'...' if len(url) > 80 else ''}</code>\n\n"
        "فرمت دانلود را انتخاب کنید:",
        reply_markup=format_selection_keyboard(url, detected.source, detected.media_type),
    )


# ── Torrent file handler ───────────────────────────────────────────────────────

@router.message(F.document.file_name.lower().endswith(".torrent"))
async def handle_torrent_file(msg: Message):
    track_message()
    bot = msg.bot
    doc = msg.document
    task_id = str(uuid.uuid4())
    status_msg = await msg.answer("⏳ <b>در حال دریافت فایل تورنت...</b>")

    import tempfile
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".torrent", delete=False) as tmp:
            tmp_path = tmp.name

        tg_file = await bot.get_file(doc.file_id)
        await bot.download_file(tg_file.file_path, destination=tmp_path)

        await bot.edit_message_text(
            chat_id=msg.chat.id,
            message_id=status_msg.message_id,
            text="🧲 <b>فایل تورنت دریافت شد. در حال شروع دانلود...</b>",
            reply_markup=None,
        )

        t = asyncio.create_task(_run_download_and_send(
            bot=bot,
            chat_id=msg.chat.id,
            status_msg_id=status_msg.message_id,
            url=tmp_path,
            source=SourceType.TORRENT.value,
            fmt="file",
            quality="best",
            task_id=task_id,
        ))
        t.add_done_callback(lambda _: Path(tmp_path).unlink(missing_ok=True))
        _active_tasks[task_id] = t

    except Exception as e:
        logger.error(f"[TorrentFile] Failed: {e}", exc_info=True)
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
        try:
            await bot.edit_message_text(
                chat_id=msg.chat.id,
                message_id=status_msg.message_id,
                text=f"❌ خطا در دریافت فایل:\n<code>{str(e)[:200]}</code>",
            )
        except Exception:
            pass


# ── Callbacks ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fmt:"))
async def callback_format(call: CallbackQuery):
    _, fmt, url_hash = call.data.split(":", 2)
    if fmt == "video":
        await call.message.edit_text(
            "🎬 کیفیت ویدیو را انتخاب کنید:",
            reply_markup=quality_keyboard(url_hash),
        )
    else:
        await _start_download(call, url_hash, fmt, "best")


@router.callback_query(F.data.startswith("qual:"))
async def callback_quality(call: CallbackQuery):
    _, quality, url_hash = call.data.split(":", 2)
    await _start_download(call, url_hash, "video", quality)


@router.callback_query(F.data == "cancel")
async def callback_cancel(call: CallbackQuery):
    await call.message.edit_text("❌ لغو شد.", reply_markup=None)


@router.callback_query(F.data.startswith("dl_cancel:"))
async def callback_dl_cancel(call: CallbackQuery):
    task_id = call.data.split(":", 1)[1]
    task = _active_tasks.get(task_id)
    if task and not task.done():
        task.cancel()
        await call.answer("در حال لغو...")
    else:
        await call.answer("دانلود قبلاً تمام یا لغو شده است.", show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass


async def _start_download(call: CallbackQuery, url_hash: str, fmt: str, quality: str):
    data = _load_url(url_hash)
    if not data:
        await call.message.edit_text("❌ لینک منقضی شده. لطفاً دوباره ارسال کنید.")
        return

    task_id = str(uuid.uuid4())
    status_msg = await call.message.edit_text("⏳ شروع دانلود...")

    from bot.handlers.cookies import get_user_cookie_path, has_user_cookies
    cookie_path = str(get_user_cookie_path(call.from_user.id)) if has_user_cookies(call.from_user.id) else None

    t = asyncio.create_task(
        _run_download_and_send(
            bot=call.bot,
            chat_id=call.message.chat.id,
            status_msg_id=status_msg.message_id,
            url=data["url"],
            source=data["source"],
            fmt=fmt,
            quality=quality,
            task_id=task_id,
            cookie_path=cookie_path,
        )
    )
    _active_tasks[task_id] = t


# ── Download + Send pipeline ───────────────────────────────────────────────────

async def _run_download_and_send(
    bot: Bot,
    chat_id: int,
    status_msg_id: int,
    url: str,
    source: str,
    fmt: str,
    quality: str,
    task_id: str,
    cookie_path: str = None,
):
    from uploaders.telegram import TelegramUploader

    uploader = TelegramUploader(bot)
    loop = asyncio.get_event_loop()
    last_edit = [0.0]
    _show_cancel = [True]

    async def safe_edit(text: str):
        now = time.monotonic()
        if now - last_edit[0] < 2.5:
            return
        last_edit[0] = now
        kb = _cancel_kb(task_id) if _show_cancel[0] else None
        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=status_msg_id,
                text=text, parse_mode="HTML", reply_markup=kb,
            )
        except Exception:
            pass

    def dl_hook(d):
        if d["status"] != "downloading":
            return
        total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
        downloaded = d.get("downloaded_bytes", 0)
        speed = d.get("speed") or 0
        if not total:
            return
        pct = downloaded / total * 100
        speed_str = f"{speed/1024/1024:.1f} MB/s" if speed else ""
        text = (
            f"⬇️ <b>در حال دانلود...</b>\n"
            f"{_bar(pct)} {pct:.0f}%\n"
            f"{downloaded/1024/1024:.1f} / {total/1024/1024:.1f} MB"
            + (f"  •  {speed_str}" if speed_str else "")
        )
        asyncio.run_coroutine_threadsafe(safe_edit(text), loop)

    async def torrent_hook(text: str):
        await safe_edit(text)

    async def _upload_file(file_path: str):
        import os
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / 1024 / 1024
        last_edit[0] = 0

        ul_last = [0, time.monotonic()]

        async def upload_progress(current: int, total: int):
            now = time.monotonic()
            dt = now - ul_last[1]
            speed = (current - ul_last[0]) / dt if dt > 0 and ul_last[0] >= 0 else 0
            ul_last[0] = current
            ul_last[1] = now
            pct = current / total * 100
            speed_str = f"{speed/1024/1024:.1f} MB/s" if speed > 0 else ""
            text = (
                f"📤 <b>در حال آپلود...</b>\n"
                f"{_bar(pct)} {pct:.0f}%\n"
                f"{current/1024/1024:.1f} / {total/1024/1024:.1f} MB"
                + (f"  •  {speed_str}" if speed_str else "")
            )
            await safe_edit(text)

        await safe_edit(f"📤 <b>در حال آپلود...</b>\n{_bar(0)} 0%\n0 / {size_mb:.1f} MB")
        await uploader.send_file(
            chat_id=chat_id,
            file_path=file_path,
            caption="✅ دانلود شد",
            progress_callback=upload_progress,
        )

    try:
        file_paths = await _download(url, source, fmt, quality, task_id, dl_hook, cookie_path, torrent_hook)

        if isinstance(file_paths, str):
            file_paths = [file_paths]

        for i, fp in enumerate(file_paths):
            if i > 0:
                last_edit[0] = 0
            await _upload_file(fp)

        _show_cancel[0] = False
        _active_tasks.pop(task_id, None)
        await bot.delete_message(chat_id=chat_id, message_id=status_msg_id)
        try:
            shutil.rmtree(Path(file_paths[0]).parent, ignore_errors=True)
        except Exception:
            pass

    except asyncio.CancelledError:
        _active_tasks.pop(task_id, None)
        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=status_msg_id,
                text="❌ دانلود لغو شد.", reply_markup=None,
            )
        except Exception:
            pass

    except Exception as exc:
        _active_tasks.pop(task_id, None)
        logger.error(f"[Task {task_id}] Failed: {exc}", exc_info=True)
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg_id,
                text=f"❌ خطا در دانلود:\n<code>{str(exc)[:300]}</code>",
                parse_mode="HTML",
                reply_markup=None,
            )
        except Exception:
            pass


async def _ytdlp_generic(url: str, task_id: str, fmt: str, cookie_path: str = None) -> str:
    import yt_dlp
    import os
    from configs.settings import settings as _s
    output_path = Path(_s.STORAGE_PATH) / "downloads" / task_id
    output_path.mkdir(parents=True, exist_ok=True)
    is_audio = fmt in ("audio", "mp3", "flac")
    opts: dict = {
        "outtmpl": str(output_path / "%(title)s.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
    }
    if cookie_path and os.path.exists(cookie_path):
        opts["cookiefile"] = cookie_path
    if is_audio:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "320"}]
    else:
        opts["format"] = "bestvideo+bestaudio/best"
        opts["merge_output_format"] = "mp4"

    def _run():
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run)
    files = [f for f in output_path.iterdir() if f.is_file()]
    if not files:
        raise FileNotFoundError(f"yt-dlp produced no files for {url}")
    return str(files[0])


async def _download(
    url: str, source: str, fmt: str, quality: str, task_id: str,
    progress_hook=None, cookie_path: str = None, torrent_hook=None
) -> str | list:
    from downloaders.youtube import YouTubeDownloader
    from downloaders.social import InstagramDownloader, TwitterDownloader
    from downloaders.audio import SoundCloudDownloader, SpotifyDownloader
    from downloaders.file import DirectDownloader, GitHubDownloader, GooglePlayDownloader
    from downloaders.torrent import TorrentDownloader

    s = SourceType(source)

    def first(result):
        if isinstance(result, list):
            if not result:
                raise FileNotFoundError("Downloader returned empty list")
            return result[0]
        return result

    if s == SourceType.YOUTUBE:
        return await YouTubeDownloader().download(url, task_id, fmt, quality, progress_hook, cookie_path)
    elif s == SourceType.INSTAGRAM:
        return first(await InstagramDownloader().download(url, task_id, cookie_path))
    elif s == SourceType.TWITTER:
        return first(await TwitterDownloader().download(url, task_id, cookie_path))
    elif s == SourceType.SOUNDCLOUD:
        return first(await SoundCloudDownloader().download(url, task_id))
    elif s == SourceType.SPOTIFY:
        return first(await SpotifyDownloader().download(url, task_id))
    elif s == SourceType.DIRECT:
        return await DirectDownloader().download(url, task_id, cookie_path=cookie_path)
    elif s == SourceType.GITHUB:
        return await GitHubDownloader().download_repo_zip(url, task_id)
    elif s == SourceType.TORRENT:
        return await TorrentDownloader().download(url, task_id, torrent_hook)
    elif s == SourceType.GOOGLE_PLAY:
        return await GooglePlayDownloader().download(url, task_id)
    elif s == SourceType.APPLE_MUSIC:
        return await _ytdlp_generic(url, task_id, fmt, cookie_path)
    else:
        raise NotImplementedError(f"دانلود از {source} پشتیبانی نمی‌شود")
