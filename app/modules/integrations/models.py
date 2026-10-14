"""SQLAlchemy ORM models owned by the integrations module."""

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.metadata.models import MediaWork


class IntegrationProvider(str, enum.Enum):
    """External services integrated for sync or scraping."""

    LETTERBOXD = "LETTERBOXD"
    TMDB = "TMDB"
    OMDB = "OMDB"


class SyncRunStatus(str, enum.Enum):
    """Execution status of an integration sync run."""

    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class IntegrationSyncRun(Base, TimestampMixin):
    """Audit log of sync executions with external services."""

    __tablename__ = "integration_sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider: Mapped[IntegrationProvider] = mapped_column(
        Enum(IntegrationProvider, name="integration_provider_enum"),
        index=True,
        nullable=False,
    )
    sync_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[SyncRunStatus] = mapped_column(
        Enum(SyncRunStatus, name="sync_run_status_enum"),
        index=True,
        nullable=False,
        default=SyncRunStatus.RUNNING,
    )
    items_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ExternalItemMapping(Base, TimestampMixin):
    """Idempotent mapping between external identifiers and internal MediaWork."""

    __tablename__ = "external_item_mappings"
    __table_args__ = (
        UniqueConstraint(
            "provider", "external_key", name="uq_external_mappings_provider_key"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider: Mapped[IntegrationProvider] = mapped_column(
        Enum(IntegrationProvider, name="integration_provider_enum"),
        index=True,
        nullable=False,
    )
    external_key: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    work_id: Mapped[int] = mapped_column(
        ForeignKey("media_works.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    last_synced_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    work: Mapped["MediaWork"] = relationship(
        "MediaWork", back_populates="external_mappings"
    )
