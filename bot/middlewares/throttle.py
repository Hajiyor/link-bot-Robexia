"""
Throttling Middleware — rate-limits per user.
Uses Redis when configured, falls back to in-memory dict.
"""

import time
import logging
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from configs.settings import settings

logger = logging.getLogger(__name__)

_memory: dict[int, list[float]] = {}


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self):
        self._use_redis = bool(settings.REDIS_URL)
        if self._use_redis:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id if event.from_user else 0

        if self._use_redis:
            key = f"throttle:{user_id}"
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, settings.RATE_LIMIT_WINDOW)
        else:
            now = time.time()
            window_start = now - settings.RATE_LIMIT_WINDOW
            ts = _memory.get(user_id, [])
            ts = [t for t in ts if t > window_start]
            ts.append(now)
            _memory[user_id] = ts
            count = len(ts)

        if count > settings.RATE_LIMIT_MESSAGES:
            try:
                await event.answer("⚠️ سرعت ارسال پیام بیش از حد مجاز. لطفاً کمی صبر کنید.")
            except Exception:
                pass
            return

        return await handler(event, data)
