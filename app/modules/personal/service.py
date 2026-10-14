"""Application service and transaction orchestration for the personal module."""
from sqlalchemy.orm import Session


class PersonalService:
    """Service layer coordinating personal domain rules and transactions."""

    def __init__(self, session: Session) -> None:
        self.session = session
