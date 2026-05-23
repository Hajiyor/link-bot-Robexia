"""
Torrent Download Engine - aria2c with JSON-RPC control
Features: 4GB size limit, 60s stall detection, real-time progress
"""

import asyncio
import base64
import json
import logging
import random
import re
import string
import time
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from configs.settings import settings

logger = logging.getLogger(__name__)

MAX_TG_SIZE   = 4 * 1024 ** 3  # 4 GiB
STALL_TIMEOUT = 60              # seconds with no progress + no connections → cancel
META_TIMEOUT  = 60              # seconds to resolve magnet metadata
POLL_INTERVAL = 2               # seconds between RPC polls


def _rpc(port: int, secret: str, method: str, params=None):
    payload = json.dumps({
        "jsonrpc": "2.0", "id": "lp",
        "method": f"aria2.{method}",
        "params": [f"token:{secret}"] + (params or []),
    }).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/jsonrpc",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def _bar(pct: float, width: int = 10) -> str:
    filled = int(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _fmt_size(b: int) -> str:
    if b >= 1024 ** 3:
        return f"{b/1024**3:.2f} GB"
    if b >= 1024 ** 2:
        return f"{b/1024**2:.1f} MB"
    return f"{b/1024:.0f} KB"


def _fmt_speed(bps: int) -> str:
    if bps >= 1024 ** 2:
        return f"{bps/1024**2:.1f} MB/s"
    if bps >= 1024:
        return f"{bps/1024:.0f} KB/s"
    return f"{bps} B/s"


def _fmt_eta(seconds: float) -> str:
    if seconds <= 0:
        return "—"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m}m"
    if m:
        return f"{m}m{s}s"
    return f"{s}s"


class TorrentDownloader:
    def __init__(self):
        self.storage = Path(settings.STORAGE_PATH)

    async def download(
        self,
        magnet_or_path: str,
        task_id: str,
        progress_callback: Optional[Callable] = None,
    ) -> list[str]:
        output_path = self.storage / "downloads" / task_id
        output_path.mkdir(parents=True, exist_ok=True)

        port   = random.randint(16800, 16899)
        secret = "".join(random.choices(string.ascii_letters + string.digits, k=16))

        cmd = [
            "aria2c",
            "--enable-rpc=true",
            f"--rpc-listen-port={port}",
            f"--rpc-secret={secret}",
            "--dir", str(output_path),
            "--seed-ratio=0",
            "--seed-time=0",
            "--bt-stop-timeout=60",
            "--max-connection-per-server=10",
            "--split=5",
            "--follow-torrent=true",
            "--daemon=false",
            "--quiet=true",
            "--allow-overwrite=true",
        ]
        if settings.HTTP_PROXY:
            cmd += [f"--all-proxy={settings.HTTP_PROXY}"]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        gid = None
        try:
            # Wait for RPC to come online
            for _ in range(20):
                await asyncio.sleep(0.5)
                try:
                    _rpc(port, secret, "getVersion")
                    break
                except Exception:
                    continue
            else:
                raise RuntimeError("aria2c RPC راه‌اندازی نشد")

            # Add download
            is_magnet = magnet_or_path.startswith("magnet:")
            if is_magnet or magnet_or_path.startswith("http"):
                res = _rpc(port, secret, "addUri", [[magnet_or_path]])
            else:
                with open(magnet_or_path, "rb") as f:
                    data = base64.b64encode(f.read()).decode()
                res = _rpc(port, secret, "addTorrent", [data])
            gid = res["result"]

            stall_since     = time.monotonic()
            last_downloaded = -1
            meta_deadline   = time.monotonic() + META_TIMEOUT

            if progress_callback:
                await progress_callback("🧲 <b>در حال دریافت اطلاعات تورنت...</b>")

            while True:
                await asyncio.sleep(POLL_INTERVAL)

                try:
                    status = _rpc(port, secret, "tellStatus", [gid])["result"]
                except Exception:
                    # aria2c may have switched GID after following torrent
                    try:
                        active = _rpc(port, secret, "tellActive")["result"]
                        if active:
                            gid    = active[0]["gid"]
                            status = active[0]
                        else:
                            stopped = _rpc(port, secret, "tellStopped", [0, 1])["result"]
                            status  = stopped[0] if stopped else {}
                    except Exception:
                        break

                state       = status.get("status", "")
                total       = int(status.get("totalLength", 0))
                downloaded  = int(status.get("completedLength", 0))
                speed       = int(status.get("downloadSpeed", 0))
                connections = int(status.get("connections", 0))

                # 4 GB guard
                if total > MAX_TG_SIZE:
                    raise ValueError(
                        f"⛔ حجم فایل ({_fmt_size(total)}) بیشتر از حد مجاز تلگرام (4 GB) است.\n"
                        "دانلود لغو شد."
                    )

                # Stall detection
                if downloaded > last_downloaded:
                    last_downloaded = downloaded
                    stall_since     = time.monotonic()
                elif connections == 0 and total > 0:
                    if time.monotonic() - stall_since > STALL_TIMEOUT:
                        raise TimeoutError(
                            "⏱ تورنت فعال نیست — سیدی پیدا نشد.\n"
                            "دانلود پس از ۶۰ ثانیه لغو شد."
                        )

                # Magnet metadata timeout
                if is_magnet and total == 0 and time.monotonic() > meta_deadline:
                    raise TimeoutError(
                        "⏱ اطلاعات تورنت دریافت نشد (۶۰ ثانیه).\n"
                        "لینک مگنت معتبر نیست یا سیدی وجود ندارد."
                    )

                if state == "complete":
                    if progress_callback:
                        await progress_callback(
                            f"✅ <b>دانلود تورنت کامل شد</b>\n"
                            f"{_bar(100)} 100%  •  {_fmt_size(total)}"
                        )
                    break

                if state == "error":
                    raise RuntimeError(f"خطای تورنت: {status.get('errorMessage', 'unknown')}")

                # Progress update
                if progress_callback and total > 0:
                    pct = downloaded / total * 100
                    eta = (total - downloaded) / speed if speed > 0 else 0
                    await progress_callback(
                        f"🧲 <b>در حال دانلود تورنت...</b>\n"
                        f"{_bar(pct)} {pct:.0f}%\n"
                        f"{_fmt_size(downloaded)} / {_fmt_size(total)}"
                        f"  •  {_fmt_speed(speed)}\n"
                        f"⏱ ETA: {_fmt_eta(eta)}  •  🔗 {connections} اتصال"
                    )
                elif progress_callback:
                    await progress_callback("🧲 <b>در حال دریافت اطلاعات تورنت...</b>")

            files = [
                str(f) for f in output_path.rglob("*")
                if f.is_file() and f.suffix != ".aria2"
            ]
            if not files:
                raise FileNotFoundError("هیچ فایلی دانلود نشد")

            logger.info(f"[Torrent] {len(files)} file(s) for task {task_id}")
            return files

        finally:
            try:
                _rpc(port, secret, "shutdown")
            except Exception:
                pass
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except Exception:
                pass

    @staticmethod
    def is_magnet(url: str) -> bool:
        return url.startswith("magnet:")

    @staticmethod
    def extract_info_hash(magnet: str) -> str:
        match = re.search(r"btih:([a-fA-F0-9]{40})", magnet)
        return match.group(1).lower() if match else ""
