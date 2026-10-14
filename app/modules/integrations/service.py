"""Application service and transaction orchestration for the integrations module."""
from sqlalchemy.orm import Session


class IntegrationsService:
    """Service layer coordinating integrations domain rules and transactions."""

    def __init__(self, session: Session) -> None:
        self.session = session
