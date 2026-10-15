"""SQLAlchemy ORM models owned by the library module."""

import enum
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
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


class LibraryContentType(str, enum.Enum):
    """Type of media content contained in a user library."""

    MOVIE = "MOVIE"
    SHOW = "SHOW"
    MIXED = "MIXED"


class Library(Base, TimestampMixin):
    """Named collection of media works and storage roots (e.g. Movies, 4K Archive)."""

    __tablename__ = "libraries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    content_type: Mapped[LibraryContentType] = mapped_column(
        Enum(LibraryContentType, name="library_content_type_enum"),
        default=LibraryContentType.MOVIE,
        nullable=False,
    )
    default_download_root_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    preferred_language: Mapped[str] = mapped_column(
        String(10), default="fa", nullable=False
    )

    roots: Mapped[list["LibraryRoot"]] = relationship(
        "LibraryRoot",
        back_populates="library",
        cascade="all, delete-orphan",
        foreign_keys="LibraryRoot.library_id",
    )
    memberships: Mapped[list["LibraryMembership"]] = relationship(
        "LibraryMembership",
        back_populates="library",
        cascade="all, delete-orphan",
    )
    scan_jobs: Mapped[list["ScanJob"]] = relationship(
        "ScanJob",
        back_populates="library",
        cascade="all, delete-orphan",
    )


class LibraryRoot(Base, TimestampMixin):
    """A physical filesystem directory mounted and registered under a Library."""

    __tablename__ = "library_roots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    library_id: Mapped[int] = mapped_column(
        ForeignKey("libraries.id", ondelete="CASCADE"), index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    mount_path: Mapped[str] = mapped_column(
        String(1000), unique=True, index=True, nullable=False
    )
    is_online: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True, nullable=False
    )
    is_writable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    used_bytes: Mapped[int | None] = mapped_column(BigInteger, default=0)
    total_bytes: Mapped[int | None] = mapped_column(BigInteger, default=0)
    last_scanned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    library: Mapped["Library"] = relationship("Library", back_populates="roots")
    media_files: Mapped[list["MediaFile"]] = relationship(
        "MediaFile", back_populates="root"
    )


class LibraryMembership(Base, TimestampMixin):
    """Associates a MediaWork with one or more Libraries."""

    __tablename__ = "library_memberships"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    library_id: Mapped[int] = mapped_column(
        ForeignKey("libraries.id", ondelete="CASCADE"), index=True, nullable=False
    )
    work_id: Mapped[int] = mapped_column(
        ForeignKey("media_works.id", ondelete="CASCADE"), index=True, nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    library: Mapped["Library"] = relationship("Library", back_populates="memberships")
    work: Mapped["MediaWork"] = relationship(
        "MediaWork", back_populates="library_memberships"
    )

    __table_args__ = (
        UniqueConstraint(
            "library_id", "work_id", name="uq_library_membership_lib_work"
        ),
    )


class ScanJob(Base, TimestampMixin):
    """Tracks background execution and statistics of a filesystem scan job."""

    __tablename__ = "scan_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    library_id: Mapped[int] = mapped_column(
        ForeignKey("libraries.id", ondelete="CASCADE"), index=True, nullable=False
    )
    root_id: Mapped[int | None] = mapped_column(
        ForeignKey("library_roots.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="RUNNING", nullable=False
    )  # RUNNING, COMPLETED, FAILED, CANCELLED
    files_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_unmatched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    library: Mapped["Library"] = relationship("Library", back_populates="scan_jobs")
    root: Mapped["LibraryRoot | None"] = relationship("LibraryRoot")


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

    @property
    def personal_record(self):
        """Proxy to associated work's personal record if present."""
        return getattr(self.work, "personal_record", None) if self.work else None


class MediaFile(Base, TimestampMixin):
    """Physical video file residing on a storage source."""

    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    library_item_id: Mapped[int] = mapped_column(
        ForeignKey("library_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    root_id: Mapped[int | None] = mapped_column(
        ForeignKey("library_roots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    relative_path: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, index=True
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
    root: Mapped["LibraryRoot | None"] = relationship(
        "LibraryRoot", back_populates="media_files"
    )
    episode: Mapped["MediaEpisode | None"] = relationship("MediaEpisode")
    playback_progress: Mapped["PlaybackProgress | None"] = relationship(
        "PlaybackProgress",
        back_populates="media_file",
        uselist=False,
    )

    @property
    def is_online(self) -> bool:
        """Check whether physical file exists on accessible storage and root is online."""
        import os

        if self.root is not None and not self.root.is_online:
            return False
        return os.path.exists(self.file_path)

    @property
    def computed_path(self) -> str:
        """Dynamically produce path from root mount + relative path if available."""
        if self.root is not None and self.relative_path:
            return str(Path(self.root.mount_path) / self.relative_path)
        return self.file_path
