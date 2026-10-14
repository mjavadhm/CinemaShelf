"""Persistence queries for the integrations module (no internal commits)."""

from sqlalchemy.orm import Session


class IntegrationsRepository:
    """Repository for integrations persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session
