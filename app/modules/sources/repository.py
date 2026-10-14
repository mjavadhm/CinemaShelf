"""Persistence queries for the sources module (no internal commits)."""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.sources.models import DownloadTask, DownloadTaskStatus, SourceRelease


class SourcesRepository:
    """Repository for sources and download persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # --- Source Releases ---

    def add_release(self, release: SourceRelease) -> SourceRelease:
        """Add and flush a new source release."""
        self.session.add(release)
        self.session.flush()
        return release

    def get_release_by_id(self, release_id: int) -> SourceRelease | None:
        """Fetch release candidate by its primary key."""
        return self.session.get(SourceRelease, release_id)

    def get_release_by_url(self, download_url: str) -> SourceRelease | None:
        """Fetch release candidate by its exact download URL."""
        stmt = select(SourceRelease).where(SourceRelease.download_url == download_url)
        return self.session.scalar(stmt)

    def list_releases_for_work(
        self, work_id: int, episode_id: int | None = None
    ) -> Sequence[SourceRelease]:
        """Fetch all discovered releases for a work or specific episode."""
        stmt = select(SourceRelease).where(SourceRelease.work_id == work_id)
        if episode_id is not None:
            stmt = stmt.where(SourceRelease.episode_id == episode_id)
        stmt = stmt.order_by(SourceRelease.discovered_at.desc())
        return self.session.scalars(stmt).all()

    def delete_releases_for_work(self, work_id: int) -> None:
        """Remove all existing releases for a work (e.g. before re-scraping)."""
        existing = self.list_releases_for_work(work_id)
        for r in existing:
            self.session.delete(r)
        self.session.flush()

    # --- Download Tasks ---

    def create_task(self, task: DownloadTask) -> DownloadTask:
        """Add and flush a new download task."""
        self.session.add(task)
        self.session.flush()
        return task

    def get_task_by_id(self, task_id: int) -> DownloadTask | None:
        """Fetch download task by its primary key."""
        return self.session.get(DownloadTask, task_id)

    def get_task_by_gid(self, aria2_gid: str) -> DownloadTask | None:
        """Fetch download task by its unique Aria2 GID."""
        stmt = select(DownloadTask).where(DownloadTask.aria2_gid == aria2_gid)
        return self.session.scalar(stmt)

    def list_tasks(
        self,
        status: DownloadTaskStatus | None = None,
        library_item_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[DownloadTask]:
        """List download tasks with optional filtering and pagination."""
        stmt = select(DownloadTask)
        if status is not None:
            stmt = stmt.where(DownloadTask.status == status)
        if library_item_id is not None:
            stmt = stmt.where(DownloadTask.library_item_id == library_item_id)
        stmt = stmt.order_by(DownloadTask.created_at.desc()).offset(offset).limit(limit)
        return self.session.scalars(stmt).all()

    def list_active_tasks(self) -> Sequence[DownloadTask]:
        """List all non-terminal download tasks (QUEUED, ACTIVE, PAUSED)."""
        active_statuses = (
            DownloadTaskStatus.QUEUED,
            DownloadTaskStatus.ACTIVE,
            DownloadTaskStatus.PAUSED,
        )
        stmt = (
            select(DownloadTask)
            .where(DownloadTask.status.in_(active_statuses))
            .order_by(DownloadTask.created_at.asc())
        )
        return self.session.scalars(stmt).all()

    def count_active_downloads(self) -> int:
        """Count currently running (ACTIVE) downloads."""
        stmt = select(func.count(DownloadTask.id)).where(
            DownloadTask.status == DownloadTaskStatus.ACTIVE
        )
        return self.session.scalar(stmt) or 0

    def delete_task(self, task: DownloadTask) -> None:
        """Delete download task record."""
        self.session.delete(task)
        self.session.flush()
