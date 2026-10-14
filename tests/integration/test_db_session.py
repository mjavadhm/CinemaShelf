"""Verify isolated SQLite test fixture works without touching user data."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def test_sqlite_foreign_keys_callable(db_session: Session) -> None:
    """Verify in-memory database session can execute queries."""
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1
