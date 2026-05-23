"""
YouTube Download Engine - Powered by yt-dlp
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Callable
import yt_dlp

from configs.settings import settings

logger = logging.getLogger(__name__)


class YTDLPLogger:
    def debug(self, msg): pass
    def warning(self, msg): logger.warning(f"[yt-dlp] {msg}")
    def error(self, msg): logger.error(f"[yt-dlp] {msg}")


class YouTubeDownloader:
    def __init__(self):
        self.storage = Path(settings.STORAGE_PATH)

    def _build_opts(
        self,
        output_path: str,
        format_type: str = "video",
        quality: str = "best",
        progress_hook: Optional[Callable] = None,
        has_cookies: bool = False,
    ) -> dict:
        hooks = [progress_hook] if progress_hook else []

        # android_vr works without n-challenge/PO-token but skips when cookies present.
        # Use it when no cookies; fall back to web-only when cookies exist.
        if has_cookies:
            player_clients = ["web"]
        else:
            player_clients = ["android_vr", "android", "web"]

        base_opts = {
            "outtmpl": os.path.join(output_path, "%(title)s.%(ext)s"),
            "logger": YTDLPLogger(),
            "progress_hooks": hooks,
            "noplaylist": True,
            "retries": settings.MAX_RETRIES,
            "socket_timeout": 30,
            "extractor_args": {"youtube": {"player_client": player_clients}},
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        }

        if settings.HTTP_PROXY:
            base_opts["proxy"] = settings.HTTP_PROXY

        if format_type == "audio":
            base_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }],
                "postprocessor_args": ["-ar", "44100"],
            })
        elif format_type == "video":
            quality_map = {
                "2160p": "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]/best",
                "1440p": "bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1440]+bestaudio/best[height<=1440]/best",
                "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                "720p":  "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
                "480p":  "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]/best",
                "360p":  "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]/best",
                "best":  "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
            }
            base_opts["format"] = quality_map.get(quality, "bestvideo+bestaudio/best")
            base_opts["merge_output_format"] = "mp4"

        return base_opts

    async def get_info(self, url: str) -> dict:
        """Fetch video metadata without downloading."""
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extractor_args": {"youtube": {"player_client": ["android_vr", "android", "web"]}},
        }
        if settings.HTTP_PROXY:
            opts["proxy"] = settings.HTTP_PROXY

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._extract_info, url, opts)

    def _extract_info(self, url: str, opts: dict) -> dict:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def download(
        self,
        url: str,
        task_id: str,
        format_type: str = "video",
        quality: str = "best",
        progress_hook: Optional[Callable] = None,
        cookie_path: Optional[str] = None,
    ) -> str:
        """Download a video or audio and return file path."""
        output_path = self.storage / "downloads" / task_id
        output_path.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_event_loop()

        # Pass 1: android_vr — no cookies, no n-challenge, no PO token needed.
        opts = self._build_opts(str(output_path), format_type, quality, progress_hook, has_cookies=False)
        try:
            await loop.run_in_executor(None, self._do_download, url, opts)
        except Exception as e:
            logger.warning(f"[YouTube] android_vr pass failed: {e}. Retrying with web+cookies.")
            # Pass 2: web client with cookies (age-restricted / private videos)
            opts2 = self._build_opts(str(output_path), format_type, quality, progress_hook, has_cookies=True)
            if cookie_path and os.path.exists(cookie_path):
                opts2["cookiefile"] = cookie_path
            await loop.run_in_executor(None, self._do_download, url, opts2)

        files = list(output_path.iterdir())
        if not files:
            raise FileNotFoundError("Download produced no files")

        return str(files[0])

    def _do_download(self, url: str, opts: dict):
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    async def get_formats(self, url: str) -> list[dict]:
        """Get available formats for a video."""
        info = await self.get_info(url)
        formats = []
        seen = set()

        for f in info.get("formats", []):
            height = f.get("height")
            ext = f.get("ext", "")
            if height and ext == "mp4":
                label = f"{height}p"
                if label not in seen:
                    seen.add(label)
                    formats.append({
                        "format_id": f["format_id"],
                        "label": label,
                        "height": height,
                        "filesize": f.get("filesize"),
                    })

        return sorted(formats, key=lambda x: x["height"], reverse=True)
