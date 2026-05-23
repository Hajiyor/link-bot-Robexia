"""
Cookie management handler
User sends cookies.txt (Netscape format) via /setcookie
Bot stores it and uses in protected downloads
"""

import logging
import os
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, Document

from configs.settings import settings

logger = logging.getLogger(__name__)
router = Router()

COOKIES_DIR = Path("data/cookies")
COOKIES_DIR.mkdir(parents=True, exist_ok=True)


def get_user_cookie_path(user_id: int) -> Path:
    return COOKIES_DIR / f"{user_id}.txt"


def has_user_cookies(user_id: int) -> bool:
    p = get_user_cookie_path(user_id)
    return p.exists() and p.stat().st_size > 0


@router.message(Command("setcookie"))
async def cmd_setcookie(msg: Message):
    await msg.answer(
        "🍪 <b>ارسال فایل کوکی</b>\n\n"
        "برای دانلود از سایت‌های محافظت‌شده (مثل Cloudflare)، کوکی مرورگرت رو ارسال کن:\n\n"
        "<b>روش استخراج کوکی:</b>\n"
        "1️⃣ افزونه <b>Get cookies.txt LOCALLY</b> نصب کن (Chrome/Firefox)\n"
        "2️⃣ در سایت مورد نظر وارد بشو\n"
        "3️⃣ افزونه رو باز کن → Export کن → فایل .txt رو اینجا بفرست\n\n"
        "<i>فایل باید Netscape format باشه (همونی که yt-dlp میفهمه)</i>",
    )


@router.message(F.document.file_name.lower().endswith(".txt"))
async def handle_cookie_file(msg: Message):
    doc: Document = msg.document

    # Only process if user recently used /setcookie or file looks like cookies
    path = get_user_cookie_path(msg.from_user.id)

    try:
        file = await msg.bot.get_file(doc.file_id)
        await msg.bot.download_file(file.file_path, destination=str(path))

        # Quick validate: Netscape cookie format check
        content = path.read_text(errors="ignore")
        if "# Netscape HTTP Cookie File" not in content and "\t" not in content:
            path.unlink(missing_ok=True)
            await msg.answer(
                "❌ فایل معتبر نیست.\n"
                "باید فرمت Netscape باشه (خروجی افزونه Get cookies.txt)."
            )
            return

        # Count domains
        domains = set()
        for line in content.splitlines():
            if line and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) >= 7:
                    domains.add(parts[0].lstrip("."))

        await msg.answer(
            f"✅ کوکی ذخیره شد!\n\n"
            f"🌐 {len(domains)} دامنه: {', '.join(list(domains)[:5])}\n\n"
            "الان دوباره لینکت رو بفرست — ربات از این کوکی استفاده می‌کنه."
        )
        logger.info(f"[Cookie] User {msg.from_user.id} set cookies for domains: {domains}")

    except Exception as e:
        logger.error(f"[Cookie] Failed to save: {e}")
        await msg.answer(f"❌ خطا در ذخیره کوکی: {e}")


@router.message(Command("delcookie"))
async def cmd_delcookie(msg: Message):
    path = get_user_cookie_path(msg.from_user.id)
    if path.exists():
        path.unlink()
        await msg.answer("🗑 کوکی‌های شما حذف شد.")
    else:
        await msg.answer("❌ کوکی‌ای ذخیره نشده.")


@router.message(Command("checkcookie"))
async def cmd_checkcookie(msg: Message):
    path = get_user_cookie_path(msg.from_user.id)
    if has_user_cookies(msg.from_user.id):
        content = path.read_text(errors="ignore")
        domains = set()
        for line in content.splitlines():
            if line and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) >= 7:
                    domains.add(parts[0].lstrip("."))
        size_kb = path.stat().st_size / 1024
        await msg.answer(
            f"✅ کوکی فعال\n"
            f"📦 حجم: {size_kb:.1f} KB\n"
            f"🌐 دامنه‌ها: {', '.join(list(domains)[:8])}"
        )
    else:
        await msg.answer("❌ کوکی‌ای ذخیره نشده. از /setcookie استفاده کن.")
