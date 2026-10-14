"""Persistence queries for the library module (no internal commits)."""
from sqlalchemy.orm import Session


class LibraryRepository:
    """Repository for library persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
