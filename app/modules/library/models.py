"""SQLAlchemy ORM models owned by the library module."""

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.metadata.models import MediaEpisode, MediaWork
    from app.modules.playback.models import PlaybackProgress
    from app.modules.sources.models import DownloadTask


class LibraryItemStatus(str, enum.Enum):
    """Availability status of a work in user's library."""

    WANTED = "WANTED"
    DOWNLOADING = "DOWNLOADING"
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    ARCHIVED = "ARCHIVED"


class LibraryItem(Base, TimestampMixin):
    """Library entry tracking local acquisition status for a MediaWork."""

    __tablename__ = "library_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(
        ForeignKey("media_works.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[LibraryItemStatus] = mapped_column(
        Enum(LibraryItemStatus, name="library_item_status_enum"),
        index=True,
        nullable=False,
        default=LibraryItemStatus.WANTED,
    )
    root_folder_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    work: Mapped["MediaWork"] = relationship("MediaWork", back_populates="library_item")
    media_files: Mapped[list["MediaFile"]] = relationship(
        "MediaFile",
        back_populates="library_item",
        cascade="all, delete-orphan",
    )
    download_tasks: Mapped[list["DownloadTask"]] = relationship(
        "DownloadTask",
        back_populates="library_item",
        cascade="all, delete-orphan",
    )


class MediaFile(Base, TimestampMixin):
    """Physical video file residing on a storage source."""

    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    library_item_id: Mapped[int] = mapped_column(
        ForeignKey("library_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    episode_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_episodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(
        String(1000), unique=True, index=True, nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(50), nullable=True)
    video_codec: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    audio_languages: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    subtitle_paths: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    has_soft_sub: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_missing: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    library_item: Mapped["LibraryItem"] = relationship(
        "LibraryItem", back_populates="media_files"
    )
    episode: Mapped["MediaEpisode | None"] = relationship("MediaEpisode")
    playback_progress: Mapped["PlaybackProgress | None"] = relationship(
        "PlaybackProgress",
        back_populates="media_file",
        uselist=False,
    )
