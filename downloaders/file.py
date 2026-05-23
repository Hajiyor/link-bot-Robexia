"""
GitHub & Direct Link Downloader
Order: wget → aria2c → yt-dlp → gallery-dl
       retry via Psiphon SOCKS5 if all fail
"""

import asyncio
import logging
import os
import re
import urllib.parse
import httpx
from pathlib import Path

from configs.settings import settings

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def _safe_url(url: str) -> str:
    """Encode brackets and other chars that break shell tools but keep %XX intact."""
    return url.replace("[", "%5B").replace("]", "%5D")


def _parse_netscape_cookies(cookie_path: str) -> dict:
    cookies = {}
    try:
        with open(cookie_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    name = parts[5]
                    value = parts[6]
                    # Only keep ASCII-safe cookies (HTTP headers must be ASCII)
                    try:
                        name.encode("ascii")
                        value.encode("ascii")
                        cookies[name] = value
                    except UnicodeEncodeError:
                        pass
    except Exception:
        pass
    return cookies


def _filename_from_url(url: str) -> str:
    name = url.split("?")[0].rstrip("/").split("/")[-1]
    return urllib.parse.unquote(name) or "download"


class DirectDownloader:
    def __init__(self):
        self.storage = Path(settings.STORAGE_PATH)

    async def download(
        self,
        url: str,
        task_id: str,
        progress_callback=None,
        filename: str = None,
        cookie_path: str = None,
    ) -> str:
        output_path = self.storage / "downloads" / task_id
        output_path.mkdir(parents=True, exist_ok=True)

        result = await self._try_all(url, output_path, cookie_path, filename, proxy=None)
        if result:
            return result

        # All direct failed → try Psiphon SOCKS5
        logger.info("[Direct] Direct failed, starting Psiphon proxy...")
        from services.psiphon_proxy import ensure_running, SOCKS_PROXY
        psiphon_ok = await ensure_running()
        if psiphon_ok:
            logger.info("[Direct] Retrying via Psiphon %s", SOCKS_PROXY)
            result = await self._try_all(url, output_path, cookie_path, filename, proxy=SOCKS_PROXY)
            if result:
                return result

        raise RuntimeError(f"All download methods failed for {url[:80]}")

    async def _try_all(
        self,
        url: str,
        output_path: Path,
        cookie_path: str | None,
        filename: str | None,
        proxy: str | None,
    ) -> str | None:

        # 1. wget — works on this server directly, handles all URL formats
        try:
            result = await self._wget(url, output_path, cookie_path, filename, proxy)
            if result:
                return result
        except Exception as e:
            logger.warning(f"[Direct] wget failed (proxy={proxy}): {e}")

        # 2. aria2c — multi-connection fallback
        try:
            return await self._aria2c(url, output_path, filename, cookie_path, proxy)
        except Exception as e:
            logger.warning(f"[Direct] aria2c failed (proxy={proxy}): {e}")

        # 3. yt-dlp generic
        try:
            result = await self._ytdlp(url, output_path, cookie_path, proxy)
            if result:
                return result
        except Exception as e:
            logger.warning(f"[Direct] yt-dlp failed (proxy={proxy}): {e}")

        # 4. gallery-dl
        try:
            result = await self._gallery_dl(url, output_path, cookie_path, proxy)
            if result:
                return result
        except Exception as e:
            logger.warning(f"[Direct] gallery-dl failed (proxy={proxy}): {e}")

        return None

    async def _wget(
        self,
        url: str,
        output_path: Path,
        cookie_path: str = None,
        filename: str = None,
        proxy: str = None,
    ) -> str | None:
        safe = _safe_url(url)
        cmd = [
            "wget",
            safe,
            "-P", str(output_path),
            "--no-check-certificate",
            "--content-disposition",
            "-q",
            f"--user-agent={_UA}",
        ]
        if filename:
            cmd += ["-O", str(output_path / filename)]
        if cookie_path and os.path.exists(cookie_path):
            cmd += ["--load-cookies", cookie_path]

        env = os.environ.copy()
        _proxy = proxy or settings.HTTP_PROXY or None
        if _proxy:
            # wget uses env vars for proxy
            env["https_proxy"] = _proxy
            env["http_proxy"] = _proxy
            env["HTTPS_PROXY"] = _proxy
            env["HTTP_PROXY"] = _proxy

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)

        if proc.returncode not in (0, 8):  # 0=ok, 8=server error but file may exist
            err = stderr.decode(errors="ignore").strip()
            raise RuntimeError(f"wget exit {proc.returncode}: {err[-200:]}")

        files = [f for f in output_path.iterdir() if f.is_file()]
        return str(max(files, key=lambda f: f.stat().st_size)) if files else None

    async def _ytdlp(self, url: str, output_path: Path, cookie_path: str = None, proxy: str = None) -> str | None:
        import yt_dlp
        safe = _safe_url(url)
        _proxy = proxy or settings.HTTP_PROXY or None
        opts = {
            "outtmpl": str(output_path / "%(title)s.%(ext)s"),
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "quiet": True,
            "noplaylist": True,
            "http_headers": {"User-Agent": _UA},
        }
        if cookie_path and os.path.exists(cookie_path):
            opts["cookiefile"] = cookie_path
        if _proxy:
            opts["proxy"] = _proxy

        existing = {f for f in output_path.iterdir() if f.is_file()} if output_path.exists() else set()

        def _run():
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([safe])

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _run)
        files = [f for f in output_path.iterdir() if f.is_file() and f not in existing]
        if not files:
            files = [f for f in output_path.iterdir() if f.is_file()]
        return str(max(files, key=lambda f: f.stat().st_size)) if files else None

    async def _gallery_dl(self, url: str, output_path: Path, cookie_path: str = None, proxy: str = None) -> str | None:
        import sys
        gdl = Path(sys.executable).parent / "gallery-dl"
        gdl_cmd = str(gdl) if gdl.exists() else "gallery-dl"
        logger.info(f"[Direct] Trying gallery-dl: {url[:80]}")
        safe = _safe_url(url)
        cmd = [
            gdl_cmd,
            "--dest", str(output_path),
            "--no-mtime",
            "--user-agent", _UA,
            safe,
        ]
        if cookie_path and os.path.exists(cookie_path):
            cmd += ["--cookies", cookie_path]
        _proxy = proxy or settings.HTTP_PROXY or None
        if _proxy:
            cmd += ["--proxy", _proxy]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err = stderr.decode(errors="ignore").strip()
            logger.warning(f"[Direct] gallery-dl exit {proc.returncode}: {err[:200]}")
        files = [f for f in output_path.rglob("*") if f.is_file()]
        return str(max(files, key=lambda f: f.stat().st_size)) if files else None

    async def _aria2c(
        self,
        url: str,
        output_path: Path,
        filename: str = None,
        cookie_path: str = None,
        proxy: str = None,
    ) -> str:
        safe = _safe_url(url)
        parts = url.split("?")[0].split("/")
        referer = "/".join(parts[:-1]) + "/" if len(parts) > 3 else "/".join(parts[:3]) + "/"
        cmd = [
            "aria2c", safe,
            "--dir", str(output_path),
            "--max-connection-per-server=4",
            "--split=4",
            "--min-split-size=1M",
            "--continue=true",
            "--auto-file-renaming=false",
            "--quiet=true",
            "--allow-overwrite=true",
            f"--user-agent={_UA}",
            f"--referer={referer}",
        ]
        if filename:
            cmd += ["--out", filename]
        if cookie_path and os.path.exists(cookie_path):
            cmd += [f"--load-cookies={cookie_path}"]
        _proxy = proxy or settings.HTTP_PROXY or None
        if _proxy:
            proxy_for_aria = _proxy.replace("socks5h://", "socks5://")
            cmd += [f"--all-proxy={proxy_for_aria}"]
            if "socks5" in _proxy:
                cmd += ["--proxy-method=tunnel", "--all-proxy-type=socks5"]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            err = stderr.decode(errors="ignore").strip() or stdout.decode(errors="ignore").strip()
            raise RuntimeError(f"aria2c failed (code {proc.returncode}): {err[:300]}")

        files = [f for f in output_path.iterdir() if f.is_file()]
        if not files:
            raise FileNotFoundError("No files downloaded")
        return str(max(files, key=lambda f: f.stat().st_size))

    async def get_file_info(self, url: str) -> dict:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            r = await client.head(url, timeout=15)
            content_length = r.headers.get("content-length")
            content_disp = r.headers.get("content-disposition", "")
            content_type = r.headers.get("content-type", "")

            filename = None
            if "filename=" in content_disp:
                match = re.search(r'filename="?([^";\n]+)"?', content_disp)
                if match:
                    filename = match.group(1).strip()
            if not filename:
                filename = url.split("/")[-1].split("?")[0] or "download"

            return {
                "filename": filename,
                "size": int(content_length) if content_length else None,
                "content_type": content_type,
            }


class GooglePlayDownloader:
    """Download APK from Google Play via APKPure."""

    def __init__(self):
        self.storage = Path(settings.STORAGE_PATH)
        self.direct = DirectDownloader()

    async def download(self, url: str, task_id: str) -> str:
        package_id = self._extract_package_id(url)
        if not package_id:
            raise ValueError(f"Cannot extract package ID from: {url}")

        logger.info(f"[GooglePlay] Downloading APK for package: {package_id}")
        apk_url = f"https://d.apkpure.com/b/APK/{package_id}?version=latest"
        return await self.direct.download(apk_url, task_id, filename=f"{package_id}.apk")

    def _extract_package_id(self, url: str) -> str | None:
        match = re.search(r"[?&]id=([\w.]+)", url)
        return match.group(1) if match else None


class GitHubDownloader:
    def __init__(self):
        self.storage = Path(settings.STORAGE_PATH)
        self.direct = DirectDownloader()

    async def get_latest_release(self, repo_url: str) -> dict:
        match = re.search(r"github\.com/([\w-]+/[\w.-]+)", repo_url)
        if not match:
            raise ValueError("Invalid GitHub URL")

        repo = match.group(1).rstrip(".git")
        api_url = f"https://api.github.com/repos/{repo}/releases/latest"

        async with httpx.AsyncClient() as client:
            r = await client.get(api_url, timeout=10)
            r.raise_for_status()
            data = r.json()

        return {
            "tag": data.get("tag_name"),
            "name": data.get("name"),
            "body": data.get("body", "")[:500],
            "assets": [
                {
                    "name": a["name"],
                    "url": a["browser_download_url"],
                    "size": a["size"],
                }
                for a in data.get("assets", [])
            ],
            "zipball": data.get("zipball_url"),
            "tarball": data.get("tarball_url"),
        }

    async def download_release(self, download_url: str, task_id: str) -> str:
        return await self.direct.download(download_url, task_id)

    async def download_repo_zip(self, repo_url: str, task_id: str, branch: str = "main") -> str:
        if "/releases/download/" in repo_url or repo_url.endswith(
            (".zip", ".tar.gz", ".exe", ".dmg", ".AppImage", ".deb", ".rpm")
        ):
            return await self.direct.download(repo_url, task_id)

        match = re.search(r"github\.com/([\w-]+/[\w.-]+)", repo_url)
        if not match:
            raise ValueError("Invalid GitHub URL")

        repo = match.group(1).rstrip(".git")

        for br in (branch, "main", "master"):
            try:
                zip_url = f"https://github.com/{repo}/archive/refs/heads/{br}.zip"
                return await self.direct.download(
                    zip_url, task_id, filename=f"{repo.replace('/', '_')}_{br}.zip"
                )
            except Exception:
                continue

        raise RuntimeError(f"Could not download GitHub repo: {repo_url}")
