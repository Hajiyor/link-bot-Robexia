#!/usr/bin/env python3
"""
LinkPink Bot — entry point
"""

import asyncio
import logging
import sys
from pathlib import Path

from configs.settings import settings

# ── Logging ──────────────────────────────────────────────────────────────────
Path(settings.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(settings.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

Path("data").mkdir(exist_ok=True)
Path(settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)


async def main():
    logger.info("🚀 Starting LinkPink Bot...")

    from database.connection import init_db
    await init_db()
    logger.info("✅ Database initialized")

    from services.stats_reporter import stats_reporter
    asyncio.create_task(stats_reporter())

    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    if settings.REDIS_URL:
        from aiogram.fsm.storage.redis import RedisStorage
        storage = RedisStorage.from_url(settings.REDIS_URL)
        logger.info("✅ Using Redis FSM storage")
    else:
        from aiogram.fsm.storage.memory import MemoryStorage
        storage = MemoryStorage()
        logger.info("✅ Using in-memory FSM storage (no Redis)")

    dp = Dispatcher(storage=storage)

    from bot.middlewares.throttle import ThrottlingMiddleware
    from bot.middlewares.logging import LoggingMiddleware
    from bot.handlers import register_all_handlers

    dp.message.middleware(ThrottlingMiddleware())
    dp.message.middleware(LoggingMiddleware())
    register_all_handlers(dp)

    logger.info("🤖 Bot is running...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
