"""
Database Models
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, JSON, Enum
from sqlalchemy.orm import DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class DownloadStatus(str, enum.Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    UPLOADING = "uploading"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DownloadSource(str, enum.Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    SPOTIFY = "spotify"
    SOUNDCLOUD = "soundcloud"
    APPLE_MUSIC = "apple_music"
    GOOGLE_PLAY = "google_play"
    GITHUB = "github"
    DIRECT = "direct"
    TORRENT = "torrent"


class User(Base):
    __tablename__ = "users"

    user_id       = Column(BigInteger, primary_key=True)
    username      = Column(String(64),  nullable=True)
    first_name    = Column(String(128), nullable=True)
    first_seen    = Column(DateTime, default=datetime.utcnow)
    last_seen     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    message_count = Column(Integer, default=0)
    is_banned     = Column(Boolean, default=False)
    total_downloads = Column(Integer, default=0)
    total_bytes   = Column(BigInteger, default=0)


class Download(Base):
    __tablename__ = "downloads"

    id         = Column(Integer,  primary_key=True, autoincrement=True)
    task_id    = Column(String(64),   unique=True, nullable=False)
    user_id    = Column(BigInteger,   nullable=False)
    chat_id    = Column(BigInteger,   nullable=False)
    url        = Column(String(2048), nullable=False)
    source     = Column(Enum(DownloadSource), nullable=True)
    status     = Column(Enum(DownloadStatus), default=DownloadStatus.PENDING)
    format     = Column(String(16),   default="mp4")
    quality    = Column(String(32),   default="best")
    file_size  = Column(BigInteger,   nullable=True)
    error_msg  = Column(String(512),  nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
