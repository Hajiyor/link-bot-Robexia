"""
Link Detector - Automatically identifies download sources from URLs
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class SourceType(str, Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    SPOTIFY = "spotify"
    SOUNDCLOUD = "soundcloud"
    APPLE_MUSIC = "apple_music"
    GOOGLE_PLAY = "google_play"
    GITHUB = "github"
    TORRENT = "torrent"
    DIRECT = "direct"
    UNKNOWN = "unknown"


@dataclass
class DetectedLink:
    url: str
    source: SourceType
    media_type: str  # video, audio, file, repo, torrent
    extra: dict = None


PATTERNS = {
    SourceType.YOUTUBE: [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
        r"(?:https?://)?youtu\.be/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=[\w-]+",
        r"(?:https?://)?music\.youtube\.com/watch\?v=[\w-]+",
    ],
    SourceType.INSTAGRAM: [
        r"(?:https?://)?(?:www\.)?instagram\.com/(?:p|reel|tv)/[\w-]+",
        r"(?:https?://)?(?:www\.)?instagram\.com/stories/[\w.]+/\d+",
    ],
    SourceType.TWITTER: [
        r"(?:https?://)?(?:www\.)?(?:twitter|x)\.com/\w+/status/\d+",
    ],
    SourceType.SPOTIFY: [
        r"(?:https?://)?open\.spotify\.com/(?:track|album|playlist|artist)/[\w]+",
    ],
    SourceType.SOUNDCLOUD: [
        r"(?:https?://)?(?:www\.)?soundcloud\.com/[\w-]+/[\w-]+",
        r"(?:https?://)?(?:www\.)?soundcloud\.com/[\w-]+/sets/[\w-]+",
    ],
    SourceType.APPLE_MUSIC: [
        r"(?:https?://)?music\.apple\.com/\w+/(?:album|playlist|song)/[\w-]+",
    ],
    SourceType.GOOGLE_PLAY: [
        r"(?:https?://)?play\.google\.com/store/apps/details\?id=[\w.]+",
        r"(?:https?://)?play\.google\.com/store/music/album\?id=[\w]+",
    ],
    SourceType.GITHUB: [
        r"(?:https?://)?github\.com/[\w-]+/[\w.-]+(?:/releases/[\w/]+)?",
        r"(?:https?://)?github\.com/[\w-]+/[\w.-]+/archive/[\w/]+\.(?:zip|tar\.gz)",
    ],
    SourceType.TORRENT: [
        r"magnet:\?xt=urn:btih:[a-fA-F0-9]{40}",
        r"(?:https?://)?.*\.torrent$",
    ],
}

DIRECT_EXTENSIONS = re.compile(
    r"\.(mp4|mkv|avi|mov|mp3|flac|wav|aac|ogg|zip|rar|7z|pdf|apk|exe|dmg|iso|tar\.gz|tar\.bz2)$",
    re.IGNORECASE,
)


def detect_link(url: str) -> DetectedLink:
    url = url.strip()

    for source, patterns in PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                media_type = _get_media_type(source, url)
                return DetectedLink(url=url, source=source, media_type=media_type)

    if DIRECT_EXTENSIONS.search(url):
        return DetectedLink(url=url, source=SourceType.DIRECT, media_type="file")

    if url.startswith("http://") or url.startswith("https://"):
        return DetectedLink(url=url, source=SourceType.DIRECT, media_type="file")

    return DetectedLink(url=url, source=SourceType.UNKNOWN, media_type="unknown")


def _get_media_type(source: SourceType, url: str) -> str:
    audio_sources = {SourceType.SPOTIFY, SourceType.SOUNDCLOUD, SourceType.APPLE_MUSIC}
    if source in audio_sources:
        return "audio"
    if source == SourceType.GITHUB:
        return "repo"
    if source == SourceType.TORRENT:
        return "torrent"
    if source == SourceType.GOOGLE_PLAY:
        return "apk"
    return "video"


def extract_urls(text: str) -> list[str]:
    """Extract all URLs from a text message."""
    pattern = r"https?://[^\s<>\"{}|\\^`]+"
    return re.findall(pattern, text)
