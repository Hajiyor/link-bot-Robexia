"""
Logging Middleware
"""

import logging
import time
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        start = time.monotonic()
        user = event.from_user
        text = (event.text or "")[:80] if hasattr(event, "text") else ""

        logger.info(
            f"[MSG] user={user.id} @{user.username or '-'} | {text!r}"
        )

        try:
            result = await handler(event, data)
            elapsed = (time.monotonic() - start) * 1000
            logger.debug(f"[MSG] handled in {elapsed:.1f}ms")
            return result
        except Exception as e:
            logger.error(f"[MSG] Error: {e}", exc_info=True)
            raise
