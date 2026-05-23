"""
File Processor - Compression, Audio Extraction, Thumbnails, Metadata
"""

import asyncio
import logging
import os
import shutil
import zipfile
import tarfile
from pathlib import Path
from typing import Optional

from configs.settings import settings

logger = logging.getLogger(__name__)


class FileProcessor:
    def __init__(self):
        self.storage = Path(settings.STORAGE_PATH)

    # ── Compression ──────────────────────────────────────────────

    async def compress_zip(self, source: str | list[str], task_id: str, archive_name: str = "archive") -> str:
        output_path = self.storage / "processed" / task_id
        output_path.mkdir(parents=True, exist_ok=True)
        zip_path = output_path / f"{archive_name}.zip"

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._do_zip, source, str(zip_path))
        return str(zip_path)

    def _do_zip(self, source, zip_path):
        sources = source if isinstance(source, list) else [source]
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for src in sources:
                p = Path(src)
                if p.is_file():
                    zf.write(p, p.name)
                elif p.is_dir():
                    for f in p.rglob("*"):
                        if f.is_file():
                            zf.write(f, f.relative_to(p.parent))

    async def compress_7z(self, source: str | list[str], task_id: str, archive_name: str = "archive") -> str:
        output_path = self.storage / "processed" / task_id
        output_path.mkdir(parents=True, exist_ok=True)
        archive_path = output_path / f"{archive_name}.7z"

        sources = source if isinstance(source, list) else [source]
        cmd = ["7z", "a", "-mx=5", str(archive_path)] + sources

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"7z failed: {stderr.decode()}")

        return str(archive_path)

    async def compress_rar(self, source: str | list[str], task_id: str, archive_name: str = "archive") -> str:
        output_path = self.storage / "processed" / task_id
        output_path.mkdir(parents=True, exist_ok=True)
        archive_path = output_path / f"{archive_name}.rar"

        sources = source if isinstance(source, list) else [source]
        cmd = ["rar", "a", "-m3", str(archive_path)] + sources

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"rar failed: {stderr.decode()}")

        return str(archive_path)

    # ── Audio Extraction ─────────────────────────────────────────

    async def extract_audio(self, video_path: str, task_id: str, format: str = "mp3") -> str:
        output_path = self.storage / "processed" / task_id
        output_path.mkdir(parents=True, exist_ok=True)

        stem = Path(video_path).stem
        output_file = output_path / f"{stem}.{format}"

        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn",
            "-acodec", "libmp3lame" if format == "mp3" else "copy",
            "-ab", "320k",
            "-ar", "44100",
            "-y", str(output_file)
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg audio extract failed: {stderr.decode()[-200:]}")

        return str(output_file)

    # ── Thumbnail ────────────────────────────────────────────────

    async def make_thumbnail(self, video_path: str, task_id: str, timestamp: str = "00:00:05") -> str:
        output_path = self.storage / "processed" / task_id
        output_path.mkdir(parents=True, exist_ok=True)

        stem = Path(video_path).stem
        thumb_path = output_path / f"{stem}_thumb.jpg"

        cmd = [
            "ffmpeg", "-i", video_path,
            "-ss", timestamp,
            "-vframes", "1",
            "-q:v", "2",
            "-y", str(thumb_path)
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        return str(thumb_path) if thumb_path.exists() else None

    # ── Metadata ─────────────────────────────────────────────────

    async def add_metadata(self, file_path: str, metadata: dict) -> str:
        """Add ID3/MP4 metadata tags using ffmpeg."""
        p = Path(file_path)
        output = p.parent / f"{p.stem}_tagged{p.suffix}"

        meta_args = []
        for k, v in metadata.items():
            meta_args += ["-metadata", f"{k}={v}"]

        cmd = ["ffmpeg", "-i", file_path, "-c", "copy"] + meta_args + ["-y", str(output)]

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

        return str(output) if output.exists() else file_path

    # ── Subtitles ────────────────────────────────────────────────

    async def embed_subtitle(self, video_path: str, subtitle_path: str) -> str:
        p = Path(video_path)
        output = p.parent / f"{p.stem}_subbed.mp4"

        cmd = [
            "ffmpeg", "-i", video_path, "-i", subtitle_path,
            "-c", "copy", "-c:s", "mov_text",
            "-y", str(output)
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

        return str(output) if output.exists() else video_path

    # ── Cleanup ───────────────────────────────────────────────────

    def cleanup(self, task_id: str):
        for folder in ("downloads", "processed"):
            path = self.storage / folder / task_id
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
