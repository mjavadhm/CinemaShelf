"""Application service and transaction orchestration for the library module."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.errors import ApplicationError
from app.modules.library.models import LibraryItem, LibraryItemStatus, MediaFile
from app.modules.library.repository import LibraryRepository
from app.modules.library.schemas import LibraryItemCreate, MediaFileCreate
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
