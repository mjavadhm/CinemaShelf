"""Alembic migration environment configuration."""
from app.core.database import Base

target_metadata = Base.metadata
