"""Filesystem scanner for discovering and cataloging media files into libraries."""

from datetime import UTC, datetime
import logging
import os
from pathlib import Path
import re
import shutil
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.library.models import (
    Library,
    LibraryItem,
    LibraryItemStatus,
    LibraryMembership,
    LibraryRoot,
    MediaFile,
    ScanJob,
)
from app.modules.metadata.models import MediaWork, WorkType
from app.modules.metadata.service import MetadataService

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".m4v"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".sub", ".ass", ".ssa"}
SAMPLE_KEYWORDS = {"sample", "trailer", "preview", "extras", "featurette"}


def parse_movie_filename(file_name: str) -> tuple[str, int | None, dict[str, Any]]:
    """Extract movie title, release year, and technical properties from filename.

    Example:
        'Inception.2010.1080p.BluRay.x265-RARBG.mkv' ->
        ('Inception', 2010, {'resolution': '1080p', 'video_codec': 'x265', 'source_type': 'BluRay'})
    """
    stem = Path(file_name).stem
    # Replace underscores and dots with spaces
    normalized = stem.replace("_", " ").replace(".", " ")

    # Extract 4-digit release year (1900-2099)
    year: int | None = None
    title = normalized
    year_match = re.search(r"\b(18|19|20)\d{2}\b", normalized)
    if year_match:
        year = int(year_match.group(0))
        title = normalized[: year_match.start()].strip(" .-")
    else:
        # Fallback if no year: clean common tags
        title = re.sub(
            r"\b(1080p|720p|2160p|4k|bluray|web-dl|webrip|x265|x264|hevc)\b.*$",
            "",
            normalized,
            flags=re.IGNORECASE,
        ).strip(" .-")

    if not title:
        title = stem

    # Extract technical specs
    resolution: str | None = None
    res_match = re.search(r"\b(2160p|4k|1080p|720p|480p)\b", normalized, re.IGNORECASE)
    if res_match:
        resolution = res_match.group(0).upper() if res_match.group(0).lower() == "4k" else res_match.group(0).lower()

    video_codec: str | None = None
    codec_match = re.search(r"\b(x265|h265|hevc|x264|h264|avc)\b", normalized, re.IGNORECASE)
    if codec_match:
        video_codec = codec_match.group(0).lower()

    source_type: str | None = None
    source_match = re.search(r"\b(bluray|web-dl|webrip|hdtv|dvdrip|remux)\b", normalized, re.IGNORECASE)
    if source_match:
        source_type = source_match.group(0)

    specs = {
        "resolution": resolution,
        "video_codec": video_codec,
        "source_type": source_type,
    }
    return title.strip(), year, specs


def find_adjacent_subtitles(video_path: Path) -> list[str]:
    """Find subtitle files matching the video file or inside a Subs directory."""
    subs: list[str] = []
    parent = video_path.parent
    base_stem = video_path.stem.lower()

    # 1. Search in same directory
    try:
        for entry in parent.iterdir():
            if entry.is_file() and entry.suffix.lower() in SUBTITLE_EXTENSIONS:
                if entry.stem.lower().startswith(base_stem):
                    subs.append(str(entry.resolve()))
    except (PermissionError, OSError):
        pass

    # 2. Search inside Subs/ or Subtitles/ subfolder
    for sub_dir_name in ("Subs", "subs", "Subtitles", "subtitles"):
        sub_folder = parent / sub_dir_name
        if sub_folder.is_dir():
            try:
                for entry in sub_folder.iterdir():
                    if entry.is_file() and entry.suffix.lower() in SUBTITLE_EXTENSIONS:
                        subs.append(str(entry.resolve()))
            except (PermissionError, OSError):
                pass

    return subs


class LibraryScanner:
    """Orchestrates recursive folder scanning, metadata matching, and file registration."""

    def __init__(self, session: Session, metadata_service: MetadataService | None = None) -> None:
        self.session = session
        self.metadata_service = metadata_service or MetadataService(session)

    async def scan_root(self, root: LibraryRoot, job: ScanJob) -> ScanJob:
        """Execute a full scan over a LibraryRoot directory."""
        mount_path = Path(root.mount_path)

        # 1. Check drive online status
        if not mount_path.exists():
            root.is_online = False
            job.status = "FAILED"
            job.error_message = f"مسیر ریشه در دسترس نیست یا درایو قطع شده است: {root.mount_path}"
            job.completed_at = datetime.now(UTC)
            self.session.commit()
            logger.warning("Storage root %s is offline", root.mount_path)
            return job

        root.is_online = True
        try:
            usage = shutil.disk_usage(str(mount_path))
            root.total_bytes = usage.total
            root.used_bytes = usage.used
        except Exception:
            pass

        job.status = "RUNNING"
        self.session.commit()

        discovered_files: list[Path] = []
        # 2. Recursively traverse directory
        for dirpath, _, filenames in os.walk(str(mount_path)):
            for fname in filenames:
                ext = Path(fname).suffix.lower()
                if ext in VIDEO_EXTENSIONS:
                    file_path = Path(dirpath) / fname
                    # Skip sample or tiny files (< 150 MB)
                    if any(k in fname.lower() for k in SAMPLE_KEYWORDS):
                        continue
                    try:
                        if file_path.stat().st_size < 150 * 1024 * 1024:
                            continue
                    except OSError:
                        continue
                    discovered_files.append(file_path)

        job.files_discovered = len(discovered_files)
        self.session.commit()

        seen_file_ids: set[int] = set()

        # 3. Process each discovered video file
        for video_path in discovered_files:
            try:
                media_file = await self._process_video_file(root, video_path)
                if media_file:
                    seen_file_ids.add(media_file.id)
                    job.files_imported += 1
            except Exception as exc:
                logger.error("Error processing video file %s: %s", video_path, exc)
                job.files_unmatched += 1

            self.session.commit()

        # 4. Check for missing files: existing files on this root that were not discovered
        existing_stmt = select(MediaFile).where(MediaFile.root_id == root.id)
        existing_files = self.session.scalars(existing_stmt).all()
        for mf in existing_files:
            if mf.id not in seen_file_ids:
                if not os.path.exists(mf.file_path):
                    mf.is_missing = True
                    # If all files of this item are missing, mark item MISSING
                    if mf.library_item and all(f.is_missing for f in mf.library_item.media_files):
                        mf.library_item.status = LibraryItemStatus.MISSING

        root.last_scanned_at = datetime.now(UTC)
        job.status = "COMPLETED"
        job.completed_at = datetime.now(UTC)
        self.session.commit()
        return job

    async def _process_video_file(self, root: LibraryRoot, file_path: Path) -> MediaFile | None:
        """Process an individual video file, resolving or matching its MediaWork."""
        abs_str = str(file_path.resolve())
        rel_str = str(file_path.resolve().relative_to(Path(root.mount_path).resolve()))
        file_name = file_path.name
        file_size = file_path.stat().st_size

        parsed_title, parsed_year, specs = parse_movie_filename(file_name)
        subs = find_adjacent_subtitles(file_path)
        has_soft_sub = len(subs) > 0 or "softsub" in file_name.lower() or "sub" in file_name.lower()

        # Check if MediaFile already exists
        stmt = select(MediaFile).where(
            (MediaFile.file_path == abs_str)
            | ((MediaFile.root_id == root.id) & (MediaFile.relative_path == rel_str))
        )
        existing_mf = self.session.scalars(stmt).first()
        if existing_mf:
            existing_mf.root_id = root.id
            existing_mf.relative_path = rel_str
            existing_mf.file_size_bytes = file_size
            existing_mf.is_missing = False
            existing_mf.last_verified_at = datetime.now(UTC)
            if specs.get("resolution"):
                existing_mf.resolution = specs["resolution"]
            if specs.get("video_codec"):
                existing_mf.video_codec = specs["video_codec"]
            if subs:
                existing_mf.subtitle_paths = subs
            return existing_mf

        # Find or create MediaWork
        work = await self._find_or_create_work(parsed_title, parsed_year)
        if not work:
            return None

        # Ensure LibraryItem exists
        lib_item = self.session.scalars(
            select(LibraryItem).where(LibraryItem.work_id == work.id)
        ).first()
        if not lib_item:
            lib_item = LibraryItem(
                work_id=work.id,
                status=LibraryItemStatus.AVAILABLE,
                root_folder_path=str(root.mount_path),
            )
            self.session.add(lib_item)
            self.session.flush()
        else:
            if lib_item.status != LibraryItemStatus.AVAILABLE:
                lib_item.status = LibraryItemStatus.AVAILABLE

        # Ensure LibraryMembership exists
        membership = self.session.scalars(
            select(LibraryMembership).where(
                LibraryMembership.library_id == root.library_id,
                LibraryMembership.work_id == work.id,
            )
        ).first()
        if not membership:
            membership = LibraryMembership(
                library_id=root.library_id,
                work_id=work.id,
            )
            self.session.add(membership)

        # Create MediaFile
        mf = MediaFile(
            library_item_id=lib_item.id,
            root_id=root.id,
            relative_path=rel_str,
            file_path=abs_str,
            file_name=file_name,
            file_size_bytes=file_size,
            resolution=specs.get("resolution"),
            video_codec=specs.get("video_codec"),
            source_type=specs.get("source_type"),
            subtitle_paths=subs,
            has_soft_sub=has_soft_sub,
            is_missing=False,
            last_verified_at=datetime.now(UTC),
        )
        self.session.add(mf)
        self.session.flush()
        return mf

    async def _find_or_create_work(self, title: str, year: int | None) -> MediaWork:
        """Find work in local database or search TMDB metadata provider."""
        # Check local DB by title and year
        query = select(MediaWork).where(MediaWork.title.ilike(title))
        if year:
            query = query.where(MediaWork.release_year == year)
        work = self.session.scalars(query).first()
        if work:
            return work

        # Try TMDB search
        try:
            results = await self.metadata_service.search_external(
                query=title,
                release_year=year,
                work_type=WorkType.MOVIE,
            )
            if results:
                top_result = results[0]
                work = await self.metadata_service.get_or_ingest_work(
                    tmdb_id=top_result.tmdb_id,
                    work_type=WorkType.MOVIE,
                )
                return work
        except Exception as exc:
            logger.warning("External metadata search failed for '%s': %s", title, exc)

        # Fallback: create stub MediaWork locally so user still sees the film on their shelf
        fallback_tmdb_id = -abs(hash(f"{title}_{year or 0}")) % 1_000_000_000
        existing_stub = self.session.scalars(
            select(MediaWork).where(MediaWork.tmdb_id == fallback_tmdb_id)
        ).first()
        if existing_stub:
            return existing_stub

        work = MediaWork(
            work_type=WorkType.MOVIE,
            tmdb_id=fallback_tmdb_id,
            title=title,
            original_title=title,
            release_year=year,
        )
        self.session.add(work)
        self.session.flush()
        return work
