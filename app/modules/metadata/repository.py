"""Persistence queries for the metadata module (no internal commits)."""
from sqlalchemy.orm import Session


class MetadataRepository:
    """Repository for metadata persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
