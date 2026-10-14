"""SQLAlchemy ORM models owned by the sources module."""

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.library.models import LibraryItem
    from app.modules.metadata.models import MediaEpisode, MediaWork


class ReleaseProvider(str, enum.Enum):
    """External provider originating the release link."""

    ZARFILM = "ZARFILM"
    MANUAL = "MANUAL"


class DownloadTaskStatus(str, enum.Enum):
    """State transition enum for background downloads."""

    QUEUED = "QUEUED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    REMOVED = "REMOVED"


class SourceRelease(Base, TimestampMixin):
    """Discovered download links and release candidates."""

    __tablename__ = "source_releases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(
        ForeignKey("media_works.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    episode_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_episodes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    provider: Mapped[ReleaseProvider] = mapped_column(
        Enum(ReleaseProvider, name="release_provider_enum"),
        index=True,
        nullable=False,
    )
    source_page_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    download_url: Mapped[str] = mapped_column(Text, nullable=False)
    quality_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(50), nullable=True)
    encoder: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_text: Mapped[str | None] = mapped_column(String(50), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_dubbed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_persian_sub: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    work: Mapped["MediaWork"] = relationship(
        "MediaWork", back_populates="source_releases"
    )
    episode: Mapped["MediaEpisode | None"] = relationship("MediaEpisode")
    download_tasks: Mapped[list["DownloadTask"]] = relationship(
        "DownloadTask",
        back_populates="release",
    )

    @property
    def has_Persian_sub(self) -> bool:
        """Alias property matching casing in legacy/specification."""
        return self.has_persian_sub

    @has_Persian_sub.setter
    def has_Persian_sub(self, value: bool) -> None:
        self.has_persian_sub = value


class DownloadTask(Base, TimestampMixin):
    """Active or historical download process managed via Aria2."""

    __tablename__ = "download_tasks"

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
    release_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_releases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    aria2_gid: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    download_url: Mapped[str] = mapped_column(Text, nullable=False)
    destination_dir: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[DownloadTaskStatus] = mapped_column(
        Enum(DownloadTaskStatus, name="download_task_status_enum"),
        index=True,
        nullable=False,
        default=DownloadTaskStatus.QUEUED,
    )
    total_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    downloaded_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    download_speed_bps: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    library_item: Mapped["LibraryItem"] = relationship(
        "LibraryItem", back_populates="download_tasks"
    )
    episode: Mapped["MediaEpisode | None"] = relationship("MediaEpisode")
    release: Mapped["SourceRelease | None"] = relationship(
        "SourceRelease", back_populates="download_tasks"
    )
