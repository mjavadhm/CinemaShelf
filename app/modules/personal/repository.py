"""Persistence queries for the personal module (no internal commits)."""

from sqlalchemy.orm import Session


class PersonalRepository:
    """Repository for personal persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
