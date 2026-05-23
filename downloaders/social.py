"""
Instagram & Twitter/X Download Engine - Powered by gallery-dl & yt-dlp
"""

import asyncio
import logging
import os
from pathlib import Path
import yt_dlp
import gallery_dl

from configs.settings import settings

logger = logging.getLogger(__name__)


class InstagramDownloader:
    def __init__(self):
        self.storage = Path(settings.STORAGE_PATH)

    async def download(self, url: str, task_id: str, cookies_file: str = None) -> list[str]:
        """Download Instagram post/reel/story."""
        output_path = self.storage / "downloads" / task_id
        output_path.mkdir(parents=True, exist_ok=True)

        opts = {
            "outtmpl": str(output_path / "%(id)s.%(ext)s"),
            "quiet": True,
        }

        if cookies_file and os.path.exists(cookies_file):
            opts["cookiefile"] = cookies_file

        if settings.HTTP_PROXY:
            opts["proxy"] = settings.HTTP_PROXY

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._do_download, url, opts)

        files = list(output_path.iterdir())
        if not files:
            raise FileNotFoundError("No files downloaded from Instagram")

        return [str(f) for f in files]

    def _do_download(self, url: str, opts: dict):
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])


class TwitterDownloader:
    def __init__(self):
        self.storage = Path(settings.STORAGE_PATH)

    async def download(self, url: str, task_id: str, cookies_file: str = None) -> list[str]:
        """Download Twitter/X video or images."""
        output_path = self.storage / "downloads" / task_id
        output_path.mkdir(parents=True, exist_ok=True)

        opts = {
            "outtmpl": str(output_path / "%(id)s.%(ext)s"),
            "format": "best",
            "quiet": True,
        }

        if cookies_file and os.path.exists(cookies_file):
            opts["cookiefile"] = cookies_file

        if settings.HTTP_PROXY:
            opts["proxy"] = settings.HTTP_PROXY

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._do_download, url, opts)

        files = list(output_path.iterdir())
        return [str(f) for f in files]

    def _do_download(self, url: str, opts: dict):
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
