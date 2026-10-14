"""Persistence queries for the sources module (no internal commits)."""
from sqlalchemy.orm import Session


class SourcesRepository:
    """Repository for sources persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
