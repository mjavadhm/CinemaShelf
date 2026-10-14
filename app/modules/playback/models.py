"""SQLAlchemy ORM models owned by the playback module."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.library.models import MediaFile
    from app.modules.metadata.models import MediaEpisode, MediaWork


class PlaybackProgress(Base, TimestampMixin):
    """Resume position and playback tracking per media file and work."""

    __tablename__ = "playback_progress"

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
    media_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_files.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
    )
    position_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, nullable=False
    )
    last_watched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        index=True,
        nullable=False,
    )

    work: Mapped["MediaWork"] = relationship(
        "MediaWork", back_populates="playback_progresses"
    )
    episode: Mapped["MediaEpisode | None"] = relationship("MediaEpisode")
    media_file: Mapped["MediaFile | None"] = relationship(
        "MediaFile", back_populates="playback_progress"
    )
