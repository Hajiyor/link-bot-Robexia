"""
Telegram Uploader - Supports large files via Pyrogram (MTProto)
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional, Callable

from aiogram import Bot
from aiogram.types import FSInputFile

from configs.settings import settings

logger = logging.getLogger(__name__)

MAX_AIOGRAM_SIZE  = 50  * 1024 * 1024        # 50 MB
MAX_PYROGRAM_SIZE =  4  * 1024 * 1024 * 1024 # 4 GB

_pyro_client = None

_VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ts", ".flv"}
_AUDIO_EXTS = {".mp3", ".flac", ".wav", ".ogg", ".aac", ".m4a", ".opus"}


async def get_pyro_client():
    global _pyro_client
    if _pyro_client is None or not _pyro_client.is_connected:
        from pyrogram import Client
        _pyro_client = Client(
            name="filebot_bot",
            api_id=settings.TELEGRAM_API_ID,
            api_hash=settings.TELEGRAM_API_HASH,
            bot_token=settings.BOT_TOKEN,
            no_updates=True,
            workdir="data",
        )
        await _pyro_client.start()
        logger.info("[Pyrogram] Client started")
    return _pyro_client


async def get_video_metadata(file_path: str) -> dict:
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-show_format", file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout)
        duration = int(float(data.get("format", {}).get("duration", 0)))
        width = height = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                width = stream.get("width")
                height = stream.get("height")
                break
        return {"duration": duration, "width": width, "height": height}
    except Exception as e:
        logger.warning(f"[ffprobe] metadata failed: {e}")
        return {"duration": 0, "width": None, "height": None}


async def extract_thumbnail(file_path: str, duration: int) -> str | None:
    """Extract a frame at ~10% of duration as JPEG thumbnail (320px wide)."""
    seek = max(3, duration // 10) if duration > 30 else 3
    thumb = file_path + ".thumb.jpg"
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-ss", str(seek),
            "-i", file_path,
            "-vframes", "1",
            "-vf", "scale=320:-2",
            "-q:v", "5",
            thumb,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.communicate(), timeout=30)
        p = Path(thumb)
        if p.exists() and p.stat().st_size > 0:
            return thumb
    except Exception as e:
        logger.warning(f"[thumb] extract failed: {e}")
    return None


async def prepare_video(file_path: str) -> str:
    """
    Ensure video is ready for Telegram streaming:
    - MKV/other → remux to MP4 (stream copy, no re-encode)
    - MP4 → apply faststart (moov atom to beginning)
    Returns path to prepared file (may be different from input).
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext not in _VIDEO_EXTS:
        return file_path

    out_path = path.with_suffix(".stream.mp4")

    if ext == ".mp4":
        # Apply faststart: move moov atom to beginning
        logger.info(f"[ffmpeg] Applying faststart to {path.name}")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", file_path,
            "-c", "copy",
            "-movflags", "+faststart",
            str(out_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        if proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 1024:
            path.unlink(missing_ok=True)
            logger.info(f"[ffmpeg] faststart done → {out_path.name}")
            return str(out_path)
        else:
            out_path.unlink(missing_ok=True)
            err = stderr.decode(errors="ignore")[-200:]
            logger.warning(f"[ffmpeg] faststart failed: {err}")
            return file_path

    else:
        # MKV/AVI/etc → remux to MP4 with faststart (no re-encoding)
        logger.info(f"[ffmpeg] Remuxing {path.name} → MP4")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", file_path,
            "-c", "copy",
            "-movflags", "+faststart",
            str(out_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        if proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 1024:
            path.unlink(missing_ok=True)
            logger.info(f"[ffmpeg] remux done → {out_path.name}")
            return str(out_path)
        else:
            out_path.unlink(missing_ok=True)
            err = stderr.decode(errors="ignore")[-300:]
            logger.warning(f"[ffmpeg] remux failed (keeping original): {err}")
            return file_path


class TelegramUploader:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_file(
        self,
        chat_id: int,
        file_path: str,
        caption: str = "",
        thumbnail_path: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> bool:
        ext = Path(file_path).suffix.lower()
        is_video = ext in _VIDEO_EXTS
        is_audio = ext in _AUDIO_EXTS

        # Prepare video: faststart / remux for streaming
        if is_video:
            file_path = await prepare_video(file_path)
            ext = Path(file_path).suffix.lower()

        size = os.path.getsize(file_path)

        # Extract thumbnail if not provided
        if is_video and not thumbnail_path:
            meta = await get_video_metadata(file_path)
            thumbnail_path = await extract_thumbnail(file_path, meta.get("duration", 0))

        try:
            if size <= MAX_AIOGRAM_SIZE:
                await self._send_aiogram(
                    chat_id, file_path, caption, thumbnail_path,
                    is_video, is_audio, reply_to_message_id,
                )
            elif settings.TELEGRAM_API_ID and settings.TELEGRAM_API_HASH:
                await self._send_pyrogram(
                    chat_id, file_path, caption, thumbnail_path,
                    is_video, is_audio, progress_callback,
                )
            else:
                raise ValueError("File >50 MB and Pyrogram not configured")
            return True
        except Exception as e:
            logger.error(f"[TG Upload] Failed: {e}")
            raise
        finally:
            # Clean up thumbnail
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    os.unlink(thumbnail_path)
                except Exception:
                    pass

    async def _send_aiogram(self, chat_id, file_path, caption, thumbnail,
                             is_video, is_audio, reply_id):
        f = FSInputFile(file_path)
        thumb = FSInputFile(thumbnail) if thumbnail and os.path.exists(thumbnail) else None
        kwargs = dict(
            chat_id=chat_id,
            caption=caption[:1024] if caption else "",
            reply_to_message_id=reply_id,
        )

        if is_video:
            meta = await get_video_metadata(file_path)
            await self.bot.send_video(
                video=f, thumbnail=thumb,
                duration=meta["duration"],
                width=meta["width"],
                height=meta["height"],
                supports_streaming=True,
                **kwargs,
            )
        elif is_audio:
            await self.bot.send_audio(audio=f, thumbnail=thumb, **kwargs)
        else:
            await self.bot.send_document(document=f, thumbnail=thumb, **kwargs)

    async def _send_pyrogram(self, chat_id, file_path, caption, thumbnail,
                              is_video, is_audio, progress_callback):
        client = await get_pyro_client()
        kwargs = dict(
            chat_id=chat_id,
            caption=caption[:4096] if caption else "",
            progress=progress_callback,
        )
        if thumbnail and os.path.exists(thumbnail):
            kwargs["thumb"] = thumbnail

        if is_video:
            meta = await get_video_metadata(file_path)
            await client.send_video(
                video=file_path,
                duration=meta["duration"],
                width=meta["width"] or 0,
                height=meta["height"] or 0,
                supports_streaming=True,
                **kwargs,
            )
        elif is_audio:
            await client.send_audio(audio=file_path, **kwargs)
        else:
            await client.send_document(document=file_path, **kwargs)
