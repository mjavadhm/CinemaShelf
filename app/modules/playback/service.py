"""Application service and transaction orchestration for the playback module."""
from sqlalchemy.orm import Session


class PlaybackService:
    """Service layer coordinating playback domain rules and transactions."""

    def __init__(self, session: Session) -> None:
        self.session = session
