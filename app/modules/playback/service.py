"""Application service and transaction orchestration for the playback module."""

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.adapters.player.launcher import OSOpenerPort, SystemFileOpener
from app.core.errors import ApplicationError, FileMissingError
from app.modules.library.repository import LibraryRepository
from app.modules.metadata.repository import MetadataRepository
from app.modules.playback.models import PlaybackProgress
from app.modules.playback.repository import PlaybackRepository
from app.modules.playback.schemas import FileAccessResponse, WatchStatusResponse


class PlaybackService:
    """Service layer coordinating media file access and watch status management."""

    def __init__(
        self,
        session: Session,
        opener: OSOpenerPort | None = None,
    ) -> None:
        self.session = session
        self.repository = PlaybackRepository(session)
        self.library_repo = LibraryRepository(session)
        self.metadata_repo = MetadataRepository(session)
        self.opener: OSOpenerPort = opener or SystemFileOpener()

    def open_media_file(self, media_file_id: int) -> FileAccessResponse:
        """Open a local media file with the operating system default application."""
        media_file = self.library_repo.get_media_file_by_id(media_file_id)
        if media_file is None:
            raise ApplicationError(
                code="media_file_not_found",
                message=f"MediaFile {media_file_id} not found",
                status_code=404,
            )

        target_path = Path(media_file.file_path).resolve()
        if not target_path.is_file():
            raise FileMissingError(f"Media file not found on disk: {target_path}")

        # Launch file in OS
        success = self.opener.open_file(str(target_path))

        # Update last accessed record
        work_id = media_file.library_item.work_id
        progress = self.repository.get_progress_by_file_id(media_file_id)
        if progress is None:
            progress = self.repository.get_progress(
                work_id=work_id, episode_id=media_file.episode_id
            )

        if progress is not None:
            progress.last_watched_at = datetime.now(UTC)
            if progress.media_file_id is None:
                progress.media_file_id = media_file_id
        else:
            progress = PlaybackProgress(
                work_id=work_id,
                episode_id=media_file.episode_id,
                media_file_id=media_file_id,
                is_completed=False,
                last_watched_at=datetime.now(UTC),
            )
            self.repository.save_progress(progress)

        self.session.commit()
        return FileAccessResponse(
            media_file_id=media_file.id,
            work_id=work_id,
            path=str(target_path),
            action="open_file",
            success=success,
        )

    def open_work(
        self, work_id: int, episode_id: int | None = None
    ) -> FileAccessResponse:
        """Open the local media file associated with a film or episode."""
        item = self.library_repo.get_item_by_work_id(work_id)
        if item is None or not item.media_files:
            raise ApplicationError(
                code="no_media_files_available",
                message=f"No local media files cataloged for Work {work_id}",
                status_code=404,
            )

        candidates = item.media_files
        if episode_id is not None:
            candidates = [f for f in candidates if f.episode_id == episode_id]

        if not candidates:
            raise ApplicationError(
                code="no_media_files_available",
                message=f"No media file found for episode {episode_id}",
                status_code=404,
            )

        # Pick first available candidate
        chosen_file = candidates[0]
        return self.open_media_file(chosen_file.id)

    def open_file_location(self, media_file_id: int) -> FileAccessResponse:
        """Reveal parent directory containing the media file in the OS file manager."""
        media_file = self.library_repo.get_media_file_by_id(media_file_id)
        if media_file is None:
            raise ApplicationError(
                code="media_file_not_found",
                message=f"MediaFile {media_file_id} not found",
                status_code=404,
            )

        parent_dir = Path(media_file.file_path).resolve().parent
        if not parent_dir.is_dir():
            raise FileMissingError(f"Directory not found on disk: {parent_dir}")

        success = self.opener.open_folder(str(parent_dir))
        return FileAccessResponse(
            media_file_id=media_file.id,
            work_id=media_file.library_item.work_id,
            path=str(parent_dir),
            action="open_location",
            success=success,
        )

    def mark_watched(
        self, work_id: int, episode_id: int | None = None
    ) -> PlaybackProgress:
        """Manually mark a film or episode as watched."""
        work = self.metadata_repo.get_work_by_id(work_id)
        if work is None:
            raise ApplicationError(
                code="work_not_found",
                message=f"MediaWork {work_id} not found",
                status_code=404,
            )

        progress = self.repository.get_progress(work_id, episode_id)
        if progress is not None:
            progress.is_completed = True
            progress.progress_percent = 100.0
            progress.last_watched_at = datetime.now(UTC)
        else:
            progress = PlaybackProgress(
                work_id=work_id,
                episode_id=episode_id,
                is_completed=True,
                progress_percent=100.0,
                last_watched_at=datetime.now(UTC),
            )
            self.repository.save_progress(progress)

        self.session.commit()
        return progress

    def mark_unwatched(
        self, work_id: int, episode_id: int | None = None
    ) -> PlaybackProgress:
        """Manually reset a film or episode to unwatched."""
        work = self.metadata_repo.get_work_by_id(work_id)
        if work is None:
            raise ApplicationError(
                code="work_not_found",
                message=f"MediaWork {work_id} not found",
                status_code=404,
            )

        progress = self.repository.get_progress(work_id, episode_id)
        if progress is not None:
            progress.is_completed = False
            progress.progress_percent = 0.0
            progress.position_seconds = 0
        else:
            progress = PlaybackProgress(
                work_id=work_id,
                episode_id=episode_id,
                is_completed=False,
                progress_percent=0.0,
                position_seconds=0,
                last_watched_at=datetime.now(UTC),
            )
            self.repository.save_progress(progress)

        self.session.commit()
        return progress

    def get_watch_status(
        self, work_id: int, episode_id: int | None = None
    ) -> WatchStatusResponse:
        """Retrieve current watched status for a film or episode."""
        progress = self.repository.get_progress(work_id, episode_id)
        if progress is not None:
            return WatchStatusResponse(
                work_id=work_id,
                episode_id=episode_id,
                is_watched=progress.is_completed,
                last_watched_at=progress.last_watched_at,
            )
        return WatchStatusResponse(
            work_id=work_id,
            episode_id=episode_id,
            is_watched=False,
            last_watched_at=None,
        )

    def list_watched(
        self, limit: int = 50, offset: int = 0
    ) -> Sequence[PlaybackProgress]:
        """Fetch all works/episodes marked as watched."""
        return self.repository.list_watched(limit=limit, offset=offset)

    def list_recently_opened(
        self, limit: int = 50, offset: int = 0
    ) -> Sequence[PlaybackProgress]:
        """Fetch recently accessed or watched media works."""
        return self.repository.list_recently_opened(limit=limit, offset=offset)
