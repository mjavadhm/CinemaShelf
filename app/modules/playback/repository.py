"""Persistence queries for the playback module (no internal commits)."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.playback.models import PlaybackProgress


class PlaybackRepository:
    """Repository for playback and watch progress persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_progress(
        self, work_id: int, episode_id: int | None = None
    ) -> PlaybackProgress | None:
        """Fetch watch record by work and optional episode ID."""
        stmt = select(PlaybackProgress).where(PlaybackProgress.work_id == work_id)
        if episode_id is not None:
            stmt = stmt.where(PlaybackProgress.episode_id == episode_id)
        else:
            stmt = stmt.where(PlaybackProgress.episode_id.is_(None))
        return self.session.scalars(stmt).first()

    def get_progress_by_file_id(self, media_file_id: int) -> PlaybackProgress | None:
        """Fetch watch record by associated media file ID."""
        stmt = select(PlaybackProgress).where(
            PlaybackProgress.media_file_id == media_file_id
        )
        return self.session.scalars(stmt).first()

    def save_progress(self, progress: PlaybackProgress) -> PlaybackProgress:
        """Add and flush a playback progress entity."""
        self.session.add(progress)
        self.session.flush()
        return progress

    def list_watched(
        self, limit: int = 50, offset: int = 0
    ) -> Sequence[PlaybackProgress]:
        """List media works marked as completed/watched."""
        stmt = (
            select(PlaybackProgress)
            .where(PlaybackProgress.is_completed.is_(True))
            .order_by(PlaybackProgress.last_watched_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.session.scalars(stmt).all()

    def list_recently_opened(
        self, limit: int = 50, offset: int = 0
    ) -> Sequence[PlaybackProgress]:
        """List recently accessed or watched media works."""
        stmt = (
            select(PlaybackProgress)
            .order_by(PlaybackProgress.last_watched_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.session.scalars(stmt).all()

    def delete_progress(self, progress: PlaybackProgress) -> None:
        """Remove a playback progress record."""
        self.session.delete(progress)
        self.session.flush()
