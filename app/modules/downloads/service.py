"""Application service and transaction orchestration for the downloads module."""
from sqlalchemy.orm import Session


class DownloadsService:
    """Service layer coordinating downloads domain rules and transactions."""

    def __init__(self, session: Session) -> None:
        self.session = session
