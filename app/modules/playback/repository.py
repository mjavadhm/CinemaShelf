"""Persistence queries for the playback module (no internal commits)."""

from sqlalchemy.orm import Session


class PlaybackRepository:
    """Repository for playback persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
