"""Application service and transaction orchestration for the sources module."""
from sqlalchemy.orm import Session


class SourcesService:
    """Service layer coordinating sources domain rules and transactions."""

    def __init__(self, session: Session) -> None:
        self.session = session
