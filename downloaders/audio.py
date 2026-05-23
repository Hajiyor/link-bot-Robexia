"""
Audio Download Engines - Spotify, SoundCloud, Apple Music
"""

import asyncio
import logging
import subprocess
from pathlib import Path
import yt_dlp

from configs.settings import settings

logger = logging.getLogger(__name__)


class SpotifyDownloader:
    """Spotify via spotdl — searches YouTube Music, handles tracks/albums/playlists."""

    def __init__(self):
        self.storage = Path(settings.STORAGE_PATH)

    async def download(self, url: str, task_id: str) -> list[str]:
        output_path = self.storage / "downloads" / task_id
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"[Spotify] Downloading via spotdl: {url}")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._do_download, url, str(output_path))

        files = list(output_path.iterdir())
        if not files:
            raise FileNotFoundError("No files downloaded from Spotify")
        return [str(f) for f in files]

    def _do_download(self, url: str, output_dir: str):
        import sys
        cmd = [
            sys.executable, "-m", "spotdl",
            url,
            "--output", f"{output_dir}/{{title}}",
            "--format", "mp3",
            "--bitrate", "320k",
        ]
        if settings.HTTP_PROXY:
            cmd += ["--proxy", settings.HTTP_PROXY]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"spotdl failed: {result.stderr or result.stdout}")


class SoundCloudDownloader:
    def __init__(self):
        self.storage = Path(settings.STORAGE_PATH)

    async def download(self, url: str, task_id: str) -> list[str]:
        """Download from SoundCloud via yt-dlp."""
        output_path = self.storage / "downloads" / task_id
        output_path.mkdir(parents=True, exist_ok=True)

        opts = {
            "format": "bestaudio/best",
            "outtmpl": str(output_path / "%(title)s.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
            "quiet": True,
            "noplaylist": True,
        }
        if settings.HTTP_PROXY:
            opts["proxy"] = settings.HTTP_PROXY

        logger.info(f"[SoundCloud] Downloading: {url}")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._do_download, url, opts)

        files = list(output_path.iterdir())
        if not files:
            raise FileNotFoundError("No files downloaded from SoundCloud")
        return [str(f) for f in files]

    def _do_download(self, url: str, opts: dict):
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])


class AppleMusicDownloader:
    """Apple Music via yt-dlp (limited support)"""

    def __init__(self):
        self.storage = Path(settings.STORAGE_PATH)

    async def download(self, url: str, task_id: str) -> list[str]:
        output_path = self.storage / "downloads" / task_id
        output_path.mkdir(parents=True, exist_ok=True)

        opts = {
            "format": "bestaudio/best",
            "outtmpl": str(output_path / "%(title)s.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }],
            "quiet": True,
        }

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: yt_dlp.YoutubeDL(opts).__enter__().download([url])
        )

        return [str(f) for f in output_path.iterdir()]
