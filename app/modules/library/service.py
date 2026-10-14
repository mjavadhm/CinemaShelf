import os
from pathlib import Path
import re
import shutil
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.modules.library.models import LibraryItem, LibraryItemStatus, MediaFile
from app.modules.library.repository import LibraryRepository
from app.modules.library.schemas import (
    LibraryItemCreate,
    MediaFileCreate,
    StorageVolumeResponse,
)
from app.modules.metadata.service import MetadataService


class LibraryService:
    """Service layer coordinating library domain rules and transactions."""

    def __init__(
        self,
        session: Session,
        metadata_service: MetadataService | None = None,
    ) -> None:
        self.session = session
        self.repository = LibraryRepository(session)
        self.metadata_service = metadata_service or MetadataService(session)

    async def add_to_library(self, request: LibraryItemCreate) -> LibraryItem:
        """Add a MediaWork to the local library."""
        work_id = request.work_id

        if work_id is None:
            if request.tmdb_id is None:
                raise ApplicationError(
                    code="invalid_request",
                    message="Either work_id or tmdb_id must be provided",
                    status_code=400,
                )
            # Ingest work via metadata service
            work = await self.metadata_service.get_or_ingest_work(
                tmdb_id=request.tmdb_id,
                work_type=request.work_type,
            )
            work_id = work.id
        else:
            # Verify work exists
            self.metadata_service.get_work(work_id)

        # Check if already present in library
        existing = self.repository.get_item_by_work_id(work_id)
        if existing is not None:
            raise ApplicationError(
                code="item_already_in_library",
                message=f"Work {work_id} is already cataloged in the library",
                status_code=409,
            )

        item = LibraryItem(
            work_id=work_id,
            status=request.status,
            root_folder_path=request.root_folder_path,
        )
        self.repository.create_item(item)
        self.session.commit()

        loaded = self.repository.get_item_by_id(item.id)
        assert loaded is not None
        return loaded

    def get_item(self, item_id: int) -> LibraryItem:
        """Fetch LibraryItem by ID or raise 404."""
        item = self.repository.get_item_by_id(item_id)
        if item is None:
            raise ApplicationError(
                code="item_not_found",
                message=f"LibraryItem {item_id} not found",
                status_code=404,
            )
        return item

    def list_items(
        self,
        status: LibraryItemStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[LibraryItem]:
        """List library items with filtering."""
        return self.repository.list_items(status=status, limit=limit, offset=offset)

    def update_status(self, item_id: int, status: LibraryItemStatus) -> LibraryItem:
        """Update the acquisition/availability status of a library item."""
        item = self.get_item(item_id)
        item.status = status
        self.session.commit()
        return self.get_item(item_id)

    def attach_media_file(self, item_id: int, file_data: MediaFileCreate) -> MediaFile:
        """Register a physical file under a library item."""
        item = self.get_item(item_id)

        existing_file = self.repository.get_media_file_by_path(file_data.file_path)
        if existing_file is not None:
            raise ApplicationError(
                code="duplicate_file_path",
                message=f"A media file with path '{file_data.file_path}' already exists",
                status_code=409,
            )

        media_file = MediaFile(
            library_item_id=item.id,
            episode_id=file_data.episode_id,
            file_path=file_data.file_path,
            file_name=file_data.file_name,
            file_size_bytes=file_data.file_size_bytes,
            resolution=file_data.resolution,
            video_codec=file_data.video_codec,
            source_type=file_data.source_type,
            audio_languages=file_data.audio_languages,
            subtitle_paths=file_data.subtitle_paths,
            has_soft_sub=file_data.has_soft_sub,
            is_missing=False,
        )
        self.repository.add_media_file(media_file)

        # Update item status if it was previously wanted or downloading
        if item.status in (LibraryItemStatus.WANTED, LibraryItemStatus.DOWNLOADING):
            item.status = LibraryItemStatus.AVAILABLE

        self.session.commit()
        return media_file

    def remove_item(self, item_id: int) -> None:
        """Remove a LibraryItem (does not delete physical file on disk)."""
        item = self.get_item(item_id)
        self.repository.delete_item(item)
        self.session.commit()

    def get_item_by_work_id(self, work_id: int) -> LibraryItem:
        """Fetch LibraryItem by associated MediaWork ID or raise 404."""
        item = self.repository.get_item_by_work_id(work_id)
        if item is None:
            raise ApplicationError(
                code="item_not_found",
                message=f"LibraryItem for work {work_id} not found",
                status_code=404,
            )
        return item

    def get_storage_volumes(self) -> list[StorageVolumeResponse]:
        """Detect and return storage volumes status (online/offline, used, total space)."""
        settings = get_settings()
        detected_paths: dict[str, str] = {}

        # 1. Configured local download directory
        dl_path = str(settings.download_dir.resolve())
        detected_paths[dl_path] = "Internal Storage (Downloads)"

        # 2. Paths from LibraryItem roots
        for root in self.repository.get_all_root_folders():
            if root:
                mount_pt, label = self._resolve_volume(root)
                if mount_pt not in detected_paths:
                    detected_paths[mount_pt] = label

        # 3. Paths from registered MediaFiles
        for media_file in self.repository.get_all_media_files():
            if media_file.file_path:
                mount_pt, label = self._resolve_volume(media_file.file_path)
                if mount_pt not in detected_paths:
                    detected_paths[mount_pt] = label

        volumes: list[StorageVolumeResponse] = []
        for mount_path, label in detected_paths.items():
            vol_id = re.sub(r"[^a-zA-Z0-9_-]", "_", label.lower()).strip("_") or "vol"
            is_online = os.path.exists(mount_path)
            used_bytes = 0
            total_bytes = 0
            if is_online:
                try:
                    usage = shutil.disk_usage(mount_path)
                    used_bytes = usage.used
                    total_bytes = usage.total
                except OSError:
                    is_online = False
            volumes.append(
                StorageVolumeResponse(
                    id=vol_id,
                    label=label,
                    mount_path=mount_path,
                    used_bytes=used_bytes,
                    total_bytes=total_bytes,
                    is_online=is_online,
                )
            )

        return volumes

    @staticmethod
    def _resolve_volume(path_str: str) -> tuple[str, str]:
        """Extract mount directory and user-friendly drive label from a file/folder path."""
        p = Path(path_str)
        parts = p.parts
        # Check /run/media/<user>/<label>
        if len(parts) >= 5 and parts[1] == "run" and parts[2] == "media":
            return str(Path(*parts[:5])), parts[4]
        # Check /media/<user>/<label>
        if len(parts) >= 4 and parts[1] == "media":
            return str(Path(*parts[:4])), parts[3]
        # Check /mnt/<label>
        if len(parts) >= 3 and parts[1] == "mnt":
            return str(Path(*parts[:3])), parts[2]

        # If existing path, check real mount point
        if os.path.exists(path_str):
            cur = p.resolve()
            while not os.path.ismount(cur) and cur.parent != cur:
                cur = cur.parent
            label = cur.name if cur.name else "Internal Storage"
            return str(cur), label

        # Non-existing path: use parent folder as label
        parent = str(p.parent)
        label = p.parent.name or "External Storage"
        return parent, label

