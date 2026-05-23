"""
Admin Handlers
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from configs.settings import settings
from services.stats_reporter import get_stats

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


@router.message(Command("stats"))
async def cmd_stats(msg: Message):
    stats = get_stats()
    await msg.answer(
        f"📊 <b>آمار ربات</b>\n\n"
        f"💬 پیام‌های ۶۰ ثانیه اخیر: {stats['messages_per_min']}\n"
        f"💬 پیام‌های ۱ ساعت اخیر: {stats['messages_per_hour']}",
    )


@router.message(Command("broadcast"), F.from_user.id.in_(settings.ADMIN_IDS))
async def cmd_broadcast(msg: Message):
    text = msg.text.removeprefix("/broadcast").strip()
    if not text:
        await msg.answer("Usage: /broadcast <message>")
        return
    await msg.answer("📢 برادکست در این نسخه پیاده‌سازی نشده.")
