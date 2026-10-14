"""Persistence queries for the downloads module (no internal commits)."""

from sqlalchemy.orm import Session


class DownloadsRepository:
    """Repository for downloads persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
