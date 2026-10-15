"""Virtual shortcut categorizer.

Creates organized virtual folders with symlinks or shortcuts organized by:
- Director (ranked by film count)
- IMDb / TMDB Rating brackets
- Decade
"""

import logging
import os
import platform
import re
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.modules.library.models import LibraryItem, MediaFile
from app.modules.metadata.models import MediaWork, WorkCredit

logger = logging.getLogger(__name__)


def sanitize_folder_name(name: str) -> str:
    """Strip illegal filesystem characters for cross-platform compatibility."""
    if not name:
        return "Unknown"
    # Replace illegal characters / \ : * ? " < > |
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", name).strip()
    return cleaned or "Unknown"


def create_virtual_link(target_file: Path, link_path: Path) -> bool:
    """Create a symlink on Unix/Linux/macOS or a .lnk shortcut on Windows."""
    try:
        link_path.parent.mkdir(parents=True, exist_ok=True)
        if link_path.exists() or link_path.is_symlink():
            if link_path.is_dir() and not link_path.is_symlink():
                return False
            link_path.unlink()

        if platform.system() == "Windows":
            # On Windows, try win32com or PowerShell shortcut
            try:
                import win32com.client  # type: ignore[import-untyped]

                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(str(link_path))
                shortcut.Targetpath = str(target_file)
                shortcut.WorkingDirectory = str(target_file.parent)
                shortcut.save()
                return True
            except Exception:
                # Fallback to symlink if permissions allow
                link_path.symlink_to(target_file)
                return True
        else:
            link_path.symlink_to(target_file)
            return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to create shortcut at %s for %s: %s", link_path, target_file, exc)
        return False


def categorize_library_items(
    session: Session,
    destination_path: str,
    library_id: int | None = None,
    by_director: bool = True,
    by_rating: bool = True,
    by_decade: bool = True,
) -> dict[str, Any]:
    """Create organized shortcut folders by Director, Rating, and Decade."""
    dest_base = Path(destination_path).resolve()
    dest_base.mkdir(parents=True, exist_ok=True)

    stmt = (
        select(LibraryItem)
        .options(
            joinedload(LibraryItem.work).selectinload(MediaWork.credits).joinedload(WorkCredit.person),
            selectinload(LibraryItem.media_files),
        )
    )
    if library_id is not None:
        from app.modules.library.models import LibraryMembership

        stmt = stmt.join(
            LibraryMembership, LibraryMembership.work_id == LibraryItem.work_id
        ).where(LibraryMembership.library_id == library_id)

    items = session.scalars(stmt).unique().all()

    shortcuts_created = 0
    categories_created: list[str] = []

    # Filter items that actually have physical files on disk
    valid_items: list[tuple[LibraryItem, Path]] = []
    for item in items:
        if not item.work or not item.media_files:
            continue
        # Pick first existing file on disk
        for mf in item.media_files:
            p = Path(mf.file_path)
            if p.is_file():
                valid_items.append((item, p))
                break

    # 1. Categorize by Director (Ranked by movie count)
    if by_director:
        director_base = dest_base / "ByDirector"
        director_base.mkdir(parents=True, exist_ok=True)
        categories_created.append("ByDirector")

        # Count movies per director
        director_movie_count: Counter[str] = Counter()
        director_to_movies: dict[str, list[tuple[str, Path]]] = {}

        for item, file_path in valid_items:
            work = item.work
            directors = [
                c.person.name
                for c in (work.credits or [])
                if c.job and c.job.lower() == "director" and c.person and c.person.name
            ]
            primary_director = directors[0] if directors else "Unknown Director"
            director_movie_count[primary_director] += 1
            director_to_movies.setdefault(primary_director, []).append(
                (work.title, file_path)
            )

        # Create ranked folders (e.g. "01. Christopher Nolan (5)")
        for rank, (director_name, count) in enumerate(director_movie_count.most_common(), 1):
            folder_name = f"{rank:02d}. {sanitize_folder_name(director_name)} ({count})"
            dir_folder = director_base / folder_name
            dir_folder.mkdir(parents=True, exist_ok=True)

            for movie_title, file_path in director_to_movies.get(director_name, []):
                safe_title = sanitize_folder_name(movie_title)
                ext = ".lnk" if platform.system() == "Windows" else ""
                link_name = f"{safe_title}{file_path.suffix}{ext}"
                if create_virtual_link(file_path, dir_folder / link_name):
                    shortcuts_created += 1

    # 2. Categorize by Rating brackets
    if by_rating:
        rating_base = dest_base / "ByRating"
        rating_base.mkdir(parents=True, exist_ok=True)
        categories_created.append("ByRating")

        for item, file_path in valid_items:
            work = item.work
            r = work.imdb_rating or work.tmdb_rating or 0.0
            if r >= 9.0:
                bracket = "9.0 - 10.0 (Masterpiece)"
            elif r >= 8.0:
                bracket = "8.0 - 8.9 (Excellent)"
            elif r >= 7.0:
                bracket = "7.0 - 7.9 (Good)"
            elif r >= 6.0:
                bracket = "6.0 - 6.9 (Above Average)"
            else:
                bracket = "Below 6.0"

            bracket_folder = rating_base / bracket
            bracket_folder.mkdir(parents=True, exist_ok=True)

            safe_title = sanitize_folder_name(f"{work.title} ({r:.1f})")
            ext = ".lnk" if platform.system() == "Windows" else ""
            link_name = f"{safe_title}{file_path.suffix}{ext}"
            if create_virtual_link(file_path, bracket_folder / link_name):
                shortcuts_created += 1

    # 3. Categorize by Decade
    if by_decade:
        decade_base = dest_base / "ByDecade"
        decade_base.mkdir(parents=True, exist_ok=True)
        categories_created.append("ByDecade")

        for item, file_path in valid_items:
            work = item.work
            decade_str = f"{(work.release_year // 10) * 10}s" if work.release_year else "Unknown Decade"
            decade_folder = decade_base / decade_str
            decade_folder.mkdir(parents=True, exist_ok=True)

            safe_title = sanitize_folder_name(f"{work.title} ({work.release_year or 'Unknown'})")
            ext = ".lnk" if platform.system() == "Windows" else ""
            link_name = f"{safe_title}{file_path.suffix}{ext}"
            if create_virtual_link(file_path, decade_folder / link_name):
                shortcuts_created += 1

    return {
        "shortcuts_created": shortcuts_created,
        "categories": categories_created,
        "destination_path": str(dest_base),
    }
