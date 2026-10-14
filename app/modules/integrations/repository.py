"""Persistence queries for the integrations module (strictly no internal commits)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.integrations.models import (
    ExternalItemMapping,
    IntegrationProvider,
    IntegrationSyncRun,
    SyncRunStatus,
)
from app.modules.metadata.models import MediaWork


class IntegrationsRepository:
    """Repository managing audit runs and external system mappings."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_sync_run(
        self,
        provider: IntegrationProvider,
        sync_type: str,
    ) -> IntegrationSyncRun:
        """Create and persist a new pending/running synchronization record."""
        sync_run = IntegrationSyncRun(
            provider=provider,
            sync_type=sync_type,
            status=SyncRunStatus.RUNNING,
            items_processed=0,
            items_created=0,
            items_updated=0,
            items_failed=0,
            started_at=datetime.now(UTC),
        )
        self.session.add(sync_run)
        self.session.flush()
        return sync_run

    def finish_sync_run(
        self,
        run_id: int,
        status: SyncRunStatus,
        items_processed: int,
        items_created: int,
        items_updated: int,
        items_failed: int,
        error_details: dict[str, Any] | None = None,
    ) -> IntegrationSyncRun | None:
        """Update metrics and mark a sync run as finished."""
        sync_run = self.get_sync_run(run_id)
        if not sync_run:
            return None

        sync_run.status = status
        sync_run.items_processed = items_processed
        sync_run.items_created = items_created
        sync_run.items_updated = items_updated
        sync_run.items_failed = items_failed
        sync_run.error_details = error_details
        sync_run.finished_at = datetime.now(UTC)
        self.session.flush()
        return sync_run

    def get_sync_run(self, run_id: int) -> IntegrationSyncRun | None:
        """Retrieve a sync run by its unique identifier."""
        return self.session.get(IntegrationSyncRun, run_id)

    def list_sync_runs(
        self,
        provider: IntegrationProvider | None = None,
        status: SyncRunStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[IntegrationSyncRun]:
        """Query synchronization audit records with optional filters."""
        stmt = select(IntegrationSyncRun)
        if provider is not None:
            stmt = stmt.where(IntegrationSyncRun.provider == provider)
        if status is not None:
            stmt = stmt.where(IntegrationSyncRun.status == status)

        stmt = (
            stmt.order_by(IntegrationSyncRun.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def get_external_mapping(
        self,
        provider: IntegrationProvider,
        external_key: str,
    ) -> ExternalItemMapping | None:
        """Find an existing mapping by provider and external URI/key."""
        stmt = select(ExternalItemMapping).where(
            ExternalItemMapping.provider == provider,
            ExternalItemMapping.external_key == external_key,
        )
        return self.session.scalars(stmt).first()

    def save_external_mapping(
        self,
        mapping: ExternalItemMapping,
    ) -> ExternalItemMapping:
        """Persist or merge an external identifier mapping."""
        self.session.add(mapping)
        self.session.flush()
        return mapping

    def list_mappings(
        self,
        provider: IntegrationProvider | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ExternalItemMapping]:
        """List stored external mappings ordered by most recently synced."""
        stmt = select(ExternalItemMapping)
        if provider is not None:
            stmt = stmt.where(ExternalItemMapping.provider == provider)
        stmt = (
            stmt.order_by(ExternalItemMapping.last_synced_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def find_work_by_title_year(
        self,
        title: str,
        year: int | None = None,
    ) -> MediaWork | None:
        """Search local MediaWork catalog matching title and optional release year."""
        cleaned_title = title.strip().lower()
        stmt = select(MediaWork).where(
            (func.lower(MediaWork.title) == cleaned_title)
            | (func.lower(MediaWork.original_title) == cleaned_title)
        )
        if year is not None:
            stmt = stmt.where(MediaWork.release_year == year)

        return self.session.scalars(stmt).first()
