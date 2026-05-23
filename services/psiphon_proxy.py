"""
Psiphon proxy manager.
HTTP:   127.0.0.1:8081
SOCKS5: 127.0.0.1:1081
"""

import asyncio
import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_PSIPHON_BIN = Path(__file__).parent.parent / "data" / "psiphon" / "psiphon-tunnel-core"
_PSIPHON_CFG = Path(__file__).parent.parent / "data" / "psiphon" / "psiphon.config"
_PSIPHON_DIR = _PSIPHON_BIN.parent

HTTP_PROXY  = "http://127.0.0.1:8081"
SOCKS_PROXY = "socks5h://127.0.0.1:1081"   # socks5h = remote DNS (avoids IPv6 issues)

_process: asyncio.subprocess.Process | None = None
_ready = False


async def _port_open(port: int) -> bool:
    import socket
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=1)
        s.close()
        return True
    except OSError:
        return False


async def start() -> bool:
    global _process, _ready

    if _ready and _process and _process.returncode is None:
        return True

    # Check if psiphon is already running from a previous call
    if await _port_open(1081) and await _port_open(8081):
        logger.info("[Psiphon] Already running on ports 1081/8081")
        _ready = True
        return True

    if not _PSIPHON_BIN.exists():
        logger.error("[Psiphon] Binary not found at %s", _PSIPHON_BIN)
        return False

    logger.info("[Psiphon] Starting tunnel-core...")
    _process = await asyncio.create_subprocess_exec(
        str(_PSIPHON_BIN),
        "-config", str(_PSIPHON_CFG),
        cwd=str(_PSIPHON_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    # Wait up to 60s for Tunnels notice with count >= 1
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if _process.returncode is not None:
            logger.error("[Psiphon] Process died")
            return False
        try:
            line = await asyncio.wait_for(_process.stdout.readline(), timeout=10)
        except asyncio.TimeoutError:
            continue
        text = line.decode(errors="ignore").strip()
        if not text:
            continue
        logger.debug("[Psiphon] %s", text[:200])
        try:
            notice = json.loads(text)
            if notice.get("noticeType") == "Tunnels":
                count = notice.get("data", {}).get("count", 0)
                if count >= 1:
                    _ready = True
                    logger.info("[Psiphon] Tunnel established (%d active), proxy ready", count)
                    # Give it 1 more second to stabilize
                    await asyncio.sleep(1)
                    return True
        except (json.JSONDecodeError, AttributeError):
            # Psiphon older versions use plain text
            if "tunnels" in text.lower() and any(c.isdigit() and c != "0" for c in text):
                _ready = True
                await asyncio.sleep(1)
                return True

    # Timeout — verify proxy is actually routing
    if _process and _process.returncode is None:
        if await _verify_proxy():
            _ready = True
            logger.info("[Psiphon] Proxy verified via test request")
            return True

    logger.error("[Psiphon] Failed to establish tunnel within 60s")
    return False


async def _verify_proxy() -> bool:
    """Test that proxy is actually routing traffic."""
    try:
        import httpx
        async with httpx.AsyncClient(proxy=HTTP_PROXY, timeout=10) as client:
            r = await client.get("http://api.ipify.org")
            return r.status_code == 200
    except Exception:
        return False


async def stop():
    global _process, _ready
    if _process and _process.returncode is None:
        _process.terminate()
        try:
            await asyncio.wait_for(_process.wait(), timeout=5)
        except asyncio.TimeoutError:
            _process.kill()
    _process = None
    _ready = False


def is_running() -> bool:
    return _ready and _process is not None and _process.returncode is None


async def ensure_running() -> bool:
    if is_running():
        return True
    return await start()
