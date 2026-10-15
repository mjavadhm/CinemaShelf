"""Application service and transaction orchestration for the sources module."""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.adapters.aria2.client import Aria2Client, Aria2GlobalStats, Aria2Port
from app.adapters.zarfilm.client import ZarfilmBrowserClient, ZarfilmPort
from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError, ProviderUnavailableError
from app.modules.library.models import LibraryItemStatus
from app.modules.library.repository import LibraryRepository
from app.modules.metadata.repository import MetadataRepository
from app.modules.sources.models import (
    DownloadTask,
    DownloadTaskStatus,
    ReleaseProvider,
    SourceRelease,
)
from app.modules.sources.repository import SourcesRepository
from app.modules.sources.schemas import DownloadTaskCreate

logger = logging.getLogger(__name__)


class SourcesService:
    """Service layer coordinating sources, releases, and Aria2 download tasks."""

    def __init__(
        self,
        session: Session,
        aria2_client: Aria2Port | None = None,
        zarfilm_client: ZarfilmPort | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.repository = SourcesRepository(session)
        self.library_repo = LibraryRepository(session)
        self.metadata_repo = MetadataRepository(session)
        self.settings = settings or get_settings()
        self.aria2: Aria2Port = aria2_client or Aria2Client(settings=self.settings)
        self.zarfilm: ZarfilmPort = zarfilm_client or ZarfilmBrowserClient(
            settings=self.settings
        )

    # --- Discovery & Releases ---

    def discover_and_save_releases(
        self, work_id: int
    ) -> tuple[str | None, list[SourceRelease]]:
        """Scrape Zarfilm for download options matching work and persist them."""
        work = self.metadata_repo.get_work_by_id(work_id)
        if work is None:
            raise ApplicationError(
                code="work_not_found",
                message=f"MediaWork {work_id} not found",
                status_code=404,
            )

        llm_verifier = None
        try:
            from app.modules.llm.service import LLMService

            llm_service = LLMService(self.session)
            llm_verifier = llm_service.verify_or_select_movie
        except Exception as exc:  # noqa: BLE001
            logger.debug("LLM verifier unavailable, skipping: %s", exc)

        try:
            page_url, candidates = self.zarfilm.search_and_extract(
                title=work.title,
                year=work.release_year,
                llm_verifier=llm_verifier,
            )
        except Exception as exc:
            logger.error("Error during Zarfilm scrape for work %d: %s", work_id, exc)
            raise ProviderUnavailableError(f"Zarfilm scraper error: {exc}") from exc

        # Replace existing releases for clean update
        self.repository.delete_releases_for_work(work_id)

        saved_releases: list[SourceRelease] = []
        for c in candidates:
            release = SourceRelease(
                work_id=work_id,
                provider=ReleaseProvider.ZARFILM,
                source_page_url=page_url,
                download_url=c.download_url,
                quality_label=c.quality_label,
                resolution=c.resolution,
                encoder=c.encoder,
                size_text=c.size_text,
                size_bytes=c.size_bytes,
                is_dubbed=c.is_dubbed,
                has_persian_sub=c.has_persian_sub,
            )
            self.repository.add_release(release)
            saved_releases.append(release)

        self.session.commit()
        return page_url, saved_releases

    def list_releases_for_work(
        self, work_id: int, episode_id: int | None = None
    ) -> Sequence[SourceRelease]:
        """Fetch all discovered releases for a given work."""
        return self.repository.list_releases_for_work(work_id, episode_id)

    def get_release(self, release_id: int) -> SourceRelease:
        """Fetch release candidate by ID or raise 404."""
        release = self.repository.get_release_by_id(release_id)
        if release is None:
            raise ApplicationError(
                code="release_not_found",
                message=f"SourceRelease {release_id} not found",
                status_code=404,
            )
        return release

    # --- Download Task Management ---

    def create_download_task(
        self,
        request: DownloadTaskCreate,
        start_immediately: bool = True,
    ) -> DownloadTask:
        """Create and optionally start a download task via Aria2."""
        library_item = self.library_repo.get_item_by_id(request.library_item_id)
        if library_item is None:
            raise ApplicationError(
                code="item_not_found",
                message=f"LibraryItem {request.library_item_id} not found",
                status_code=404,
            )

        download_url: str
        if request.release_id is not None:
            release = self.get_release(request.release_id)
            download_url = release.download_url
        elif request.download_url:
            download_url = request.download_url
        else:
            raise ApplicationError(
                code="invalid_request",
                message="Either release_id or download_url must be provided",
                status_code=400,
            )

        dest_dir = request.destination_dir or str(self.settings.download_dir)
        Path(dest_dir).mkdir(parents=True, exist_ok=True)

        task = DownloadTask(
            library_item_id=request.library_item_id,
            episode_id=request.episode_id,
            release_id=request.release_id,
            aria2_gid=None,
            download_url=download_url,
            destination_dir=dest_dir,
            file_name=request.file_name,
            status=DownloadTaskStatus.QUEUED,
        )
        self.repository.create_task(task)

        if start_immediately:
            if not self.aria2.is_daemon_running():
                self.aria2.start_local_daemon()
            try:
                aria2_gid = self.aria2.add_uri(
                    url=download_url,
                    destination_dir=dest_dir,
                    file_name=request.file_name,
                )
                task.aria2_gid = aria2_gid
                task.status = DownloadTaskStatus.ACTIVE
                task.started_at = datetime.now(UTC)
            except Exception as exc:
                logger.error("Failed to enqueue URI into Aria2: %s", exc)
                task.status = DownloadTaskStatus.FAILED
                task.error_message = str(exc)
                self.session.commit()
                raise ProviderUnavailableError(
                    f"Aria2 RPC error while adding task: {exc}"
                ) from exc

        # Update library item status
        if library_item.status in (
            LibraryItemStatus.WANTED,
            LibraryItemStatus.ARCHIVED,
        ):
            library_item.status = LibraryItemStatus.DOWNLOADING

        self.session.commit()
        return task

    def get_task(self, task_id: int) -> DownloadTask:
        """Fetch download task by ID or raise 404."""
        task = self.repository.get_task_by_id(task_id)
        if task is None:
            raise ApplicationError(
                code="task_not_found",
                message=f"DownloadTask {task_id} not found",
                status_code=404,
            )
        return task

    def list_tasks(
        self,
        status: DownloadTaskStatus | None = None,
        library_item_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[DownloadTask]:
        """List download tasks."""
        return self.repository.list_tasks(
            status=status,
            library_item_id=library_item_id,
            limit=limit,
            offset=offset,
        )

    def pause_download(self, task_id: int) -> DownloadTask:
        """Pause an active Aria2 download."""
        task = self.get_task(task_id)
        if task.aria2_gid:
            success = self.aria2.pause(task.aria2_gid)
            if not success:
                raise ProviderUnavailableError(
                    f"Aria2 failed to pause download GID {task.aria2_gid}"
                )
        task.status = DownloadTaskStatus.PAUSED
        self.session.commit()
        return task

    def resume_download(self, task_id: int) -> DownloadTask:
        """Resume a paused download or start a queued task."""
        task = self.get_task(task_id)
        if task.aria2_gid:
            success = self.aria2.unpause(task.aria2_gid)
            if not success:
                raise ProviderUnavailableError(
                    f"Aria2 failed to resume download GID {task.aria2_gid}"
                )
            task.status = DownloadTaskStatus.ACTIVE
        elif task.status == DownloadTaskStatus.QUEUED:
            # Start dispatching to Aria2
            if not self.aria2.is_daemon_running():
                self.aria2.start_local_daemon()
            try:
                gid = self.aria2.add_uri(
                    url=task.download_url,
                    destination_dir=task.destination_dir,
                    file_name=task.file_name,
                )
                task.aria2_gid = gid
                task.status = DownloadTaskStatus.ACTIVE
                task.started_at = datetime.now(UTC)
            except Exception as exc:
                task.status = DownloadTaskStatus.FAILED
                task.error_message = str(exc)
                self.session.commit()
                raise ProviderUnavailableError(
                    f"Aria2 error starting queued task: {exc}"
                ) from exc

        self.session.commit()
        return task

    def cancel_download(self, task_id: int) -> DownloadTask:
        """Cancel and remove a download task."""
        task = self.get_task(task_id)
        if task.aria2_gid:
            self.aria2.remove(task.aria2_gid)
        task.status = DownloadTaskStatus.REMOVED
        self.session.commit()
        return task

    def get_aria2_stats(self) -> Aria2GlobalStats:
        """Fetch global speed and job statistics from Aria2."""
        try:
            return self.aria2.get_global_stat()
        except Exception as exc:
            raise ProviderUnavailableError(f"Aria2 unreachable: {exc}") from exc

    def set_speed_limit(self, max_download_limit_kb: int) -> None:
        """Change maximum global download rate in KB/s."""
        limit_bytes = max_download_limit_kb * 1024
        try:
            self.aria2.change_global_option(
                {"max-overall-download-limit": str(limit_bytes)}
            )
        except Exception as exc:
            raise ProviderUnavailableError(
                f"Failed to change Aria2 speed limit: {exc}"
            ) from exc
