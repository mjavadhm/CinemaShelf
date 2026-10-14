"""Idempotent execution handlers for background jobs (scan, sync, download)."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.adapters.aria2.client import Aria2Port
from app.adapters.zarfilm.client import detect_x265, parse_resolution
from app.core.logging import get_logger
from app.modules.library.models import LibraryItemStatus
from app.modules.library.schemas import MediaFileCreate
from app.modules.library.service import LibraryService
from app.modules.sources.models import DownloadTaskStatus
from app.modules.sources.repository import SourcesRepository
from app.modules.sources.service import SourcesService

logger = get_logger(__name__)


def is_within_schedule(
    start_hour: int,
    end_hour: int,
    current_hour: int | None = None,
) -> bool:
    """Return True if the current hour falls within the scheduled window.

    Supports overnight ranges (e.g., 23:00 to 07:00).
    """
    if current_hour is None:
        current_hour = datetime.now().hour

    if start_hour < end_hour:
        return start_hour <= current_hour < end_hour
    return current_hour >= start_hour or current_hour < end_hour


def sync_active_downloads(session: Session, aria2: Aria2Port) -> int:
    """Poll Aria2 for active tasks, update progress metrics, and register completed files."""
    repo = SourcesRepository(session)
    library_service = LibraryService(session)
    active_tasks = repo.list_active_tasks()
    completed_count = 0

    for task in active_tasks:
        if not task.aria2_gid:
            continue

        try:
            status_info = aria2.tell_status(task.aria2_gid)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to get Aria2 status for GID %s: %s", task.aria2_gid, exc
            )
            continue

        # Update progress counters
        task.downloaded_bytes = status_info.completed_length
        task.total_bytes = status_info.total_length
        task.download_speed_bps = status_info.download_speed
        if status_info.total_length > 0:
            task.progress_percent = round(
                (status_info.completed_length / status_info.total_length) * 100, 2
            )

        if status_info.status == "complete":
            task.status = DownloadTaskStatus.COMPLETED
            task.progress_percent = 100.0
            task.completed_at = datetime.now(UTC)

            # Determine downloaded file location
            file_path_str: str | None = status_info.file_path
            if not file_path_str and status_info.files:
                first_file = status_info.files[0]
                file_path_str = (
                    first_file.get("path")
                    if isinstance(first_file, dict)
                    else getattr(first_file, "path", None)
                )
            if not file_path_str and task.file_name:
                file_path_str = str(Path(task.destination_dir) / task.file_name)

            if file_path_str and Path(file_path_str).is_file():
                p = Path(file_path_str)
                file_size = p.stat().st_size
                res = (
                    task.release.resolution if task.release else None
                ) or parse_resolution(p.name)
                codec = "x265" if detect_x265(p.name) else None
                softsub = bool(task.release.has_persian_sub if task.release else False)

                try:
                    library_service.attach_media_file(
                        item_id=task.library_item_id,
                        file_data=MediaFileCreate(
                            episode_id=task.episode_id,
                            file_path=str(p.resolve()),
                            file_name=p.name,
                            file_size_bytes=file_size,
                            resolution=res,
                            video_codec=codec,
                            has_soft_sub=softsub,
                        ),
                    )
                    logger.info(
                        "Registered completed download as MediaFile: %s",
                        file_path_str,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Could not auto-attach media file for task %d: %s",
                        task.id,
                        exc,
                    )
            else:
                # Mark item available even if file on disk was not verified directly
                if (
                    task.library_item
                    and task.library_item.status != LibraryItemStatus.AVAILABLE
                ):
                    task.library_item.status = LibraryItemStatus.AVAILABLE

            completed_count += 1

        elif status_info.status == "error":
            task.status = DownloadTaskStatus.ERROR
            task.error_message = status_info.error_message or "Aria2 download error"
            logger.error("DownloadTask %d failed: %s", task.id, task.error_message)

        elif status_info.status == "paused":
            task.status = DownloadTaskStatus.PAUSED

        elif status_info.status == "active":
            task.status = DownloadTaskStatus.ACTIVE

    session.commit()
    return completed_count


def process_queued_downloads_jit(
    session: Session,
    sources_service: SourcesService,
    max_concurrent: int = 2,
) -> int:
    """Promote QUEUED download tasks to ACTIVE if slots are available."""
    active_count = sources_service.repository.count_active_downloads()
    available_slots = max(0, max_concurrent - active_count)
    if available_slots <= 0:
        return 0

    queued_tasks = sources_service.repository.list_tasks(
        status=DownloadTaskStatus.QUEUED,
        limit=available_slots,
    )
    activated = 0
    for task in queued_tasks:
        try:
            sources_service.resume_download(task.id)
            activated += 1
            logger.info(
                "JIT activated queued task %d (Work: %d)", task.id, task.library_item_id
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to activate queued task %d: %s", task.id, exc)

    return activated
