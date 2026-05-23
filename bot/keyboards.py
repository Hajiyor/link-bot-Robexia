"""
Inline Keyboards
"""

import hashlib
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:16]


def format_selection_keyboard(url: str, source, media_type: str) -> InlineKeyboardMarkup:
    h = _url_hash(url)
    builder = InlineKeyboardBuilder()

    if media_type in ("video",):
        builder.button(text="🎬 ویدیو (MP4)", callback_data=f"fmt:video:{h}")
        builder.button(text="🎵 صدا (MP3)", callback_data=f"fmt:audio:{h}")
    elif media_type == "audio":
        builder.button(text="🎵 MP3", callback_data=f"fmt:audio:{h}")
        builder.button(text="🎶 FLAC", callback_data=f"fmt:flac:{h}")
    else:
        builder.button(text="📁 دانلود", callback_data=f"fmt:file:{h}")
        builder.button(text="🗜 دانلود + ZIP", callback_data=f"fmt:zip:{h}")

    builder.button(text="❌ لغو", callback_data="cancel")
    builder.adjust(2, 1)
    return builder.as_markup()


def quality_keyboard(url_hash: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    qualities = [
        ("🔵 4K (2160p)", "2160p"),
        ("🟣 1440p", "1440p"),
        ("🟢 1080p Full HD", "1080p"),
        ("🟡 720p HD", "720p"),
        ("🟠 480p", "480p"),
        ("🔴 360p", "360p"),
        ("⚡ بهترین", "best"),
    ]
    for label, q in qualities:
        builder.button(text=label, callback_data=f"qual:{q}:{url_hash}")

    builder.button(text="◀️ برگشت", callback_data=f"back:{url_hash}")
    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()


def compression_keyboard(task_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗜 ZIP", callback_data=f"compress:zip:{task_id}")
    builder.button(text="📦 RAR", callback_data=f"compress:rar:{task_id}")
    builder.button(text="🔵 7Z", callback_data=f"compress:7z:{task_id}")
    builder.button(text="⏭ بدون فشرده‌سازی", callback_data=f"compress:none:{task_id}")
    builder.adjust(3, 1)
    return builder.as_markup()


def upload_target_keyboard(task_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📱 تلگرام", callback_data=f"upload:telegram:{task_id}")
    builder.button(text="💬 روبیکا", callback_data=f"upload:rubika:{task_id}")
    builder.button(text="🟢 بله", callback_data=f"upload:bale:{task_id}")
    builder.button(text="🔗 لینک مستقیم", callback_data=f"upload:link:{task_id}")
    builder.adjust(2, 2)
    return builder.as_markup()
