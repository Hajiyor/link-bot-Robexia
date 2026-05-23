"""
Settings — reads from .env file or environment variables.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _parse_ids(raw: str) -> list[int]:
    raw = raw.strip().strip("[]")
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


class _Settings:
    BOT_TOKEN: str = os.environ["BOT_TOKEN"]
    ADMIN_IDS: list[int] = _parse_ids(os.getenv("ADMIN_IDS", ""))

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/bot.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "storage")

    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "4096"))
    TEMP_FILE_TTL: int = int(os.getenv("TEMP_FILE_TTL", "3600"))
    MAX_CONCURRENT_DOWNLOADS: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "5"))
    DOWNLOAD_TIMEOUT: int = int(os.getenv("DOWNLOAD_TIMEOUT", "600"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    HTTP_PROXY: str | None = os.getenv("HTTP_PROXY") or None
    SOCKS_PROXY: str | None = os.getenv("SOCKS_PROXY") or None

    # Required for files > 50 MB — get from https://my.telegram.org
    TELEGRAM_API_ID: int | None = int(os.getenv("TELEGRAM_API_ID", "0")) or None
    TELEGRAM_API_HASH: str | None = os.getenv("TELEGRAM_API_HASH") or None

    RATE_LIMIT_MESSAGES: int = int(os.getenv("RATE_LIMIT_MESSAGES", "20"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "data/bot.log")


settings = _Settings()
