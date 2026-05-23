"""
Stats Reporter — in-memory message tracking.
"""

import asyncio
import logging
import time

import httpx

from configs.settings import settings

logger = logging.getLogger(__name__)

_msg_history: list[float] = []


def track_message():
    _msg_history.append(time.time())


def get_stats() -> dict:
    now = time.time()
    history = [t for t in _msg_history if now - t < 3600]
    return {
        "messages_per_min": sum(1 for t in history if now - t < 60),
        "messages_per_hour": len(history),
    }


async def _ping_telegram() -> float:
    try:
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=5) as client:
            await client.get(f"https://api.telegram.org/bot{settings.BOT_TOKEN}/getMe")
        return round((time.monotonic() - t0) * 1000, 1)
    except Exception:
        return -1.0


async def stats_reporter():
    while True:
        try:
            now = time.time()
            global _msg_history
            _msg_history = [t for t in _msg_history if now - t < 3600]
        except Exception as e:
            logger.warning(f"[Stats] Error: {e}")
        await asyncio.sleep(60)
