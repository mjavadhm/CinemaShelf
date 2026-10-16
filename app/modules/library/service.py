import logging
import os
from pathlib import Path
import re
import shutil
from collections.abc import Sequence
from typing import Any

import psutil
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.modules.library.models import (
    Library,
    LibraryContentType,
    LibraryItem,
    LibraryItemStatus,
    LibraryRoot,
    MediaFile,
    ScanJob,
)
from app.modules.library.repository import LibraryRepository
from app.modules.library.scanner import LibraryScanner
from app.modules.library.schemas import (
    DirectoryBrowseResponse,
    DirectoryEntry,
    LibraryCreate,
    LibraryItemCreate,
    LibraryResponse,
    LibraryRootCreate,
    LibraryRootResponse,
    MediaFileCreate,
    ScanJobResponse,
    StorageDriveShortcut,
    StorageVolumeResponse,
)
from app.modules.metadata.models import WorkType
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
        library_id: int | None = None,
        search: str | None = None,
        genre: str | None = None,
        watch_status_filter: str | None = None,
        in_watchlist_filter: bool | None = None,
        sort_by: str = "added_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[LibraryItem]:
        """List library items with filtering and sorting."""
        return self.repository.list_items(
            status=status,
            library_id=library_id,
            search=search,
            genre=genre,
            watch_status_filter=watch_status_filter,
            in_watchlist_filter=in_watchlist_filter,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )

    def count_items(
        self,
        status: LibraryItemStatus | None = None,
        library_id: int | None = None,
        search: str | None = None,
        genre: str | None = None,
        watch_status_filter: str | None = None,
        in_watchlist_filter: bool | None = None,
    ) -> int:
        """Count total library items matching query filters."""
        return self.repository.count_items(
            status=status,
            library_id=library_id,
            search=search,
            genre=genre,
            watch_status_filter=watch_status_filter,
            in_watchlist_filter=in_watchlist_filter,
        )

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

    async def rematch_item(
        self,
        item_id: int,
        target_tmdb_id: int,
        work_type: WorkType = WorkType.MOVIE,
    ) -> LibraryItem:
        """Rematch a LibraryItem and its associated media files to a different MediaWork."""
        item = self.get_item(item_id)

        target_work = await self.metadata_service.get_or_ingest_work(
            tmdb_id=target_tmdb_id,
            work_type=work_type,
        )

        old_work_id = item.work_id
        if old_work_id == target_work.id:
            return item

        # Check if target work already has a LibraryItem
        existing_target_item = self.repository.get_item_by_work_id(target_work.id)

        if existing_target_item is not None and existing_target_item.id != item.id:
            # Move all media files to the existing target item
            for mf in list(item.media_files):
                mf.library_item_id = existing_target_item.id

            if existing_target_item.status in (LibraryItemStatus.WANTED, LibraryItemStatus.DOWNLOADING):
                existing_target_item.status = LibraryItemStatus.AVAILABLE

            self.session.flush()
            self.session.delete(item)
            self.session.commit()
            return self.get_item(existing_target_item.id)

        # Otherwise, change this item's work_id to target_work.id
        item.work_id = target_work.id

        # Update LibraryMembership records
        from app.modules.library.models import LibraryMembership
        from sqlalchemy import select

        memberships = self.session.scalars(
            select(LibraryMembership).where(LibraryMembership.work_id == old_work_id)
        ).all()
        for m in memberships:
            existing_m = self.session.scalars(
                select(LibraryMembership).where(
                    LibraryMembership.library_id == m.library_id,
                    LibraryMembership.work_id == target_work.id,
                )
            ).first()
            if not existing_m:
                m.work_id = target_work.id
            else:
                self.session.delete(m)

        # Transfer personal record if target doesn't have one
        from app.modules.personal.models import PersonalRecord

        old_pr = self.session.scalars(
            select(PersonalRecord).where(PersonalRecord.work_id == old_work_id)
        ).first()
        target_pr = self.session.scalars(
            select(PersonalRecord).where(PersonalRecord.work_id == target_work.id)
        ).first()

        if old_pr and not target_pr:
            old_pr.work_id = target_work.id

        self.session.commit()
        return self.get_item(item.id)

    @staticmethod
    def _discover_system_drives() -> list[StorageDriveShortcut]:
        """Discover mounted storage volumes and partitions accessible to the server."""
        drives: list[StorageDriveShortcut] = []
        seen_paths: set[str] = set()

        # 1. User Home Directory
        try:
            home = Path.home().resolve()
            if home.exists() and str(home) not in seen_paths:
                usage = shutil.disk_usage(str(home))
                drives.append(
                    StorageDriveShortcut(
                        id="user_home",
                        label=f"خانه کاربر ({home.name})",
                        mount_path=str(home),
                        total_bytes=usage.total,
                        free_bytes=usage.free,
                        is_external=False,
                    )
                )
                seen_paths.add(str(home))
        except (OSError, PermissionError):
            pass

        # 2. psutil disk partitions (Linux mounts, Windows drive letters, etc.)
        try:
            partitions = psutil.disk_partitions(all=False)
        except Exception:
            partitions = []

        for p in partitions:
            try:
                mp = Path(p.mountpoint).resolve()
                mp_str = str(mp)
                dev = p.device
                fstype = p.fstype

                if dev.startswith("/dev/loop") or fstype in {"squashfs", "tmpfs", "devtmpfs", "overlay"}:
                    continue
                if any(
                    mp_str.startswith(skip)
                    for skip in ["/var/lib/snapd", "/snap", "/boot", "/etc", "/sys", "/proc", "/dev"]
                ):
                    continue
                if mp_str in seen_paths:
                    continue

                usage = shutil.disk_usage(mp_str)
                is_ext = any(
                    mp_str.startswith(prefix)
                    for prefix in ["/run/media", "/media", "/mnt", "/Volumes"]
                ) or ("removable" in getattr(p, "opts", "").lower())

                drive_name = mp.name if mp.name else (p.device or mp_str).rstrip("\\/")
                if is_ext:
                    label = f"هارد اکسترنال ({drive_name})"
                elif mp_str in ("/", "C:\\", "c:\\", "C:", "c:"):
                    label = f"دیسک سیستم ({drive_name})"
                elif mp_str == "/home":
                    label = "پارتیشن کاربری (/home)"
                else:
                    label = f"درایو ({drive_name})" if (p.device and ":" in p.device) else (mp.name or mp_str)

                drive_id = re.sub(r"[^a-zA-Z0-9_-]", "_", drive_name.lower()).strip("_") or f"drive_{len(drives)}"

                drives.append(
                    StorageDriveShortcut(
                        id=drive_id,
                        label=label,
                        mount_path=mp_str,
                        total_bytes=usage.total,
                        free_bytes=usage.free,
                        is_external=is_ext,
                    )
                )
                seen_paths.add(mp_str)
            except (OSError, PermissionError):
                continue

        # 3. Explicit check for external drive mount points in /run/media, /media, /mnt
        for base_mount in ["/run/media", "/media", "/mnt"]:
            base_p = Path(base_mount)
            if not base_p.exists():
                continue
            try:
                for sub in base_p.glob("*/*"):
                    if sub.is_dir() and str(sub) not in seen_paths:
                        try:
                            usage = shutil.disk_usage(str(sub))
                            drive_id = re.sub(r"[^a-zA-Z0-9_-]", "_", sub.name.lower()).strip("_") or f"ext_{len(drives)}"
                            drives.append(
                                StorageDriveShortcut(
                                    id=drive_id,
                                    label=f"هارد اکسترنال ({sub.name})",
                                    mount_path=str(sub),
                                    total_bytes=usage.total,
                                    free_bytes=usage.free,
                                    is_external=True,
                                )
                            )
                            seen_paths.add(str(sub))
                        except (OSError, PermissionError):
                            pass
            except (OSError, PermissionError):
                pass

        return drives

    def get_storage_volumes(self) -> list[StorageVolumeResponse]:
        """Detect and return storage volumes status (online/offline, used, total space)."""
        settings = get_settings()
        detected_paths: dict[str, str] = {}

        # 1. Configured local download directory
        dl_path = str(settings.download_dir.resolve())
        detected_paths[dl_path] = "حافظه داخلی (دانلودها)"

        # 2. Configured LibraryRoot records from database
        for root in self.repository.list_all_roots():
            if root.mount_path and root.mount_path not in detected_paths:
                detected_paths[root.mount_path] = root.label or Path(root.mount_path).name

        # 3. Discovered external drives
        discovered_drives = self._discover_system_drives()
        for drive in discovered_drives:
            if drive.is_external and drive.mount_path not in detected_paths:
                detected_paths[drive.mount_path] = drive.label

        # 4. Paths from registered MediaFiles (only if matching a real path or known external prefix)
        for media_file in self.repository.get_all_media_files():
            if media_file.file_path:
                resolved = self._resolve_volume(media_file.file_path)
                if resolved:
                    mount_pt, label = resolved
                    if mount_pt not in detected_paths:
                        detected_paths[mount_pt] = label

        # 5. Paths from existing LibraryItem roots (if any exist)
        for item_root in self.repository.get_all_root_folders():
            if item_root:
                resolved = self._resolve_volume(item_root)
                if resolved:
                    mount_pt, label = resolved
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
    def _resolve_volume(path_str: str) -> tuple[str, str] | None:
        """Extract mount directory and user-friendly drive label from a file/folder path."""
        p = Path(path_str)
        parts = p.parts
        # Check /run/media/<user>/<label>
        if len(parts) >= 5 and parts[1] == "run" and parts[2] == "media":
            return str(Path(*parts[:5])), f"هارد اکسترنال ({parts[4]})"
        # Check /media/<user>/<label>
        if len(parts) >= 4 and parts[1] == "media":
            return str(Path(*parts[:4])), f"هارد اکسترنال ({parts[3]})"
        # Check /mnt/<label>
        if len(parts) >= 3 and parts[1] == "mnt":
            return str(Path(*parts[:3])), f"هارد اکسترنال ({parts[2]})"

        # If existing path on filesystem, find real mount point
        if os.path.exists(path_str):
            cur = p.resolve()
            while not os.path.ismount(cur) and cur.parent != cur:
                cur = cur.parent
            label = cur.name if cur.name else ("دیسک سیستم" if str(cur) == "/" else str(cur))
            return str(cur), label

        # Check Windows drive letter if disconnected (e.g. "D:\Movies\film.mkv" -> "D:\")
        if p.drive and len(p.drive) >= 2 and p.drive[1] == ":":
            drive_root = p.drive + "\\"
            return drive_root, f"درایو ({p.drive})"

        # Non-existing path: do not invent phantom offline volumes for temporary or test paths
        return None

    # -------------------------------------------------------------------------
    # Multi-Library Operations
    # -------------------------------------------------------------------------

    def create_library(self, req: LibraryCreate) -> LibraryResponse:
        """Create a new named library collection."""
        existing = self.repository.get_library_by_name(req.name)
        if existing:
            raise ApplicationError(
                code="library_already_exists",
                message=f"کتابخانه‌ای با نام «{req.name}» از قبل وجود دارد",
                status_code=409,
            )

        content_type = LibraryContentType(req.content_type)
        lib = Library(
            name=req.name,
            content_type=content_type,
            preferred_language=req.preferred_language,
        )
        self.repository.create_library(lib)
        self.session.commit()
        return self._build_library_response(lib)

    def list_libraries(self) -> list[LibraryResponse]:
        """Fetch all libraries and their configured storage roots."""
        libs = self.repository.list_libraries()
        return [self._build_library_response(lib) for lib in libs]

    def get_library(self, library_id: int) -> LibraryResponse:
        """Fetch single library by ID."""
        lib = self.repository.get_library_by_id(library_id)
        if not lib:
            raise ApplicationError(
                code="library_not_found",
                message=f"کتابخانه با شناسه {library_id} یافت نشد",
                status_code=404,
            )
        return self._build_library_response(lib)

    def delete_library(self, library_id: int) -> None:
        """Remove a library."""
        lib = self.repository.get_library_by_id(library_id)
        if not lib:
            raise ApplicationError(
                code="library_not_found",
                message=f"کتابخانه با شناسه {library_id} یافت نشد",
                status_code=404,
            )
        self.repository.delete_library(lib)
        self.session.commit()

    def add_root_to_library(self, library_id: int, req: LibraryRootCreate) -> LibraryRootResponse:
        """Register a new storage root folder under a library."""
        lib = self.repository.get_library_by_id(library_id)
        if not lib:
            raise ApplicationError(
                code="library_not_found",
                message=f"کتابخانه با شناسه {library_id} یافت نشد",
                status_code=404,
            )

        clean_path = str(Path(req.mount_path).expanduser().resolve())
        existing = self.repository.get_root_by_path(clean_path)
        if existing:
            raise ApplicationError(
                code="root_already_exists",
                message=f"مسیر «{clean_path}» قبلاً به عنوان ریشه ثبت شده است",
                status_code=409,
            )

        is_online = os.path.exists(clean_path)
        is_writable = os.access(clean_path, os.W_OK) if is_online else False
        used_b = 0
        total_b = 0
        if is_online:
            try:
                usage = shutil.disk_usage(clean_path)
                used_b = usage.used
                total_b = usage.total
            except OSError:
                pass

        root = LibraryRoot(
            library_id=library_id,
            label=req.label,
            mount_path=clean_path,
            is_online=is_online,
            is_writable=is_writable,
            used_bytes=used_b,
            total_bytes=total_b,
        )
        self.repository.create_root(root)

        # Set default download root if not already set
        if not lib.default_download_root_id:
            lib.default_download_root_id = root.id

        self.session.commit()
        return LibraryRootResponse.model_validate(root)

    def remove_root(self, root_id: int) -> None:
        """Remove a storage root."""
        root = self.repository.get_root_by_id(root_id)
        if not root:
            raise ApplicationError(
                code="root_not_found",
                message=f"ریشه با شناسه {root_id} یافت نشد",
                status_code=404,
            )
        self.repository.delete_root(root)
        self.session.commit()

    async def trigger_scan(self, library_id: int, root_id: int | None = None) -> ScanJobResponse:
        """Execute filesystem scanner for a library and its roots."""
        lib = self.repository.get_library_by_id(library_id)
        if not lib:
            raise ApplicationError(
                code="library_not_found",
                message=f"کتابخانه با شناسه {library_id} یافت نشد",
                status_code=404,
            )

        roots_to_scan = [r for r in lib.roots if root_id is None or r.id == root_id]
        if not roots_to_scan:
            raise ApplicationError(
                code="no_roots_configured",
                message="هیچ پوشه ریشه‌ای برای این کتابخانه تنظیم نشده است",
                status_code=400,
            )

        scanner = LibraryScanner(self.session, self.metadata_service)
        last_job: ScanJob | None = None

        for root in roots_to_scan:
            job = ScanJob(library_id=library_id, root_id=root.id, status="RUNNING")
            self.repository.create_scan_job(job)
            self.session.commit()
            last_job = await scanner.scan_root(root, job)

        assert last_job is not None
        return ScanJobResponse.model_validate(last_job)

    def list_scan_jobs(self, library_id: int | None = None) -> list[ScanJobResponse]:
        """Fetch scan jobs."""
        jobs = self.repository.list_scan_jobs(library_id=library_id)
        return [ScanJobResponse.model_validate(j) for j in jobs]

    def browse_directories(self, requested_path: str | None = None) -> DirectoryBrowseResponse:
        """Browse local server filesystem directories safely."""
        start = Path(requested_path).expanduser().resolve() if requested_path else Path.home()
        if not start.exists() or not start.is_dir():
            start = Path.home()

        entries: list[DirectoryEntry] = []
        try:
            for item in sorted(start.iterdir(), key=lambda p: p.name.lower()):
                if item.is_dir() and not item.name.startswith("."):
                    is_w = os.access(str(item), os.W_OK)
                    has_sub = False
                    try:
                        has_sub = any(c.is_dir() for c in item.iterdir() if not c.name.startswith("."))
                    except (PermissionError, OSError):
                        pass

                    entries.append(
                        DirectoryEntry(
                            name=item.name,
                            path=str(item),
                            is_writable=is_w,
                            has_subdirectories=has_sub,
                        )
                    )
        except (PermissionError, OSError) as exc:
            logger.warning("Directory browse error at %s: %s", start, exc)

        parent_str = str(start.parent) if start.parent != start else None
        total_b, used_b, free_b = None, None, None
        try:
            du = shutil.disk_usage(str(start))
            total_b = du.total
            used_b = du.used
            free_b = du.free
        except OSError:
            pass

        system_drives = self._discover_system_drives()

        return DirectoryBrowseResponse(
            current_path=str(start),
            parent_path=parent_str,
            is_writable=os.access(str(start), os.W_OK),
            directories=entries,
            system_drives=system_drives,
            total_bytes=total_b,
            used_bytes=used_b,
            free_bytes=free_b,
        )

    def _build_library_response(self, lib: Library) -> LibraryResponse:
        """Helper to build LibraryResponse with movie count."""
        root_resps = [LibraryRootResponse.model_validate(r) for r in (lib.roots or [])]
        movie_count = len(lib.memberships) if lib.memberships else 0
        return LibraryResponse(
            id=lib.id,
            name=lib.name,
            content_type=lib.content_type.value,
            default_download_root_id=lib.default_download_root_id,
            preferred_language=lib.preferred_language,
            roots=root_resps,
            movie_count=movie_count,
            created_at=lib.created_at,
        )

    def get_library_stats(self, library_id: int | None = None) -> dict[str, Any]:
        """Compute aggregated statistics across library items."""
        from app.modules.library.stats import calculate_library_stats

        return calculate_library_stats(self.session, library_id=library_id)

    def categorize_library(
        self,
        destination_path: str,
        library_id: int | None = None,
        by_director: bool = True,
        by_rating: bool = True,
        by_decade: bool = True,
    ) -> dict[str, Any]:
        """Generate virtual shortcut tree by director, rating, and decade."""
        from app.modules.library.categorizer import categorize_library_items

        return categorize_library_items(
            session=self.session,
            destination_path=destination_path,
            library_id=library_id,
            by_director=by_director,
            by_rating=by_rating,
            by_decade=by_decade,
        )


