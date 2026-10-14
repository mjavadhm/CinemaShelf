"""Application service and transaction orchestration for the library module."""
from sqlalchemy.orm import Session


class LibraryService:
    """Service layer coordinating library domain rules and transactions."""

    def __init__(self, session: Session) -> None:
        self.session = session
