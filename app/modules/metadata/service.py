"""Application service and transaction orchestration for the metadata module."""
from sqlalchemy.orm import Session


class MetadataService:
    """Service layer coordinating metadata domain rules and transactions."""

    def __init__(self, session: Session) -> None:
        self.session = session
