"""Adapter implementation: Letterboxd CSV parser and export archive extractor adapter."""

from __future__ import annotations

import csv
import io
import logging
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol

logger = logging.getLogger(__name__)


class LetterboxdItemType(StrEnum):
    """Classification of an imported Letterboxd record."""

    WATCHLIST = "WATCHLIST"
    WATCHED = "WATCHED"
    RATING = "RATING"
    DIARY = "DIARY"
    LIST = "LIST"


@dataclass
class LetterboxdItem:
    """Standardized entity parsed from Letterboxd CSV or archive exports."""

    title: str
    entry_type: LetterboxdItemType
    release_year: int | None = None
    letterboxd_uri: str | None = None
    rating: float | None = None
    watched_date: date | None = None
    date_logged: date | None = None
    is_rewatch: bool = False
    review_text: str | None = None
    tags: list[str] = field(default_factory=list)
    list_name: str | None = None
    list_rank: int | None = None


@dataclass
class LetterboxdExportArchive:
    """Complete collection of Letterboxd data parsed from an export ZIP archive."""

    watchlist: list[LetterboxdItem] = field(default_factory=list)
    watched: list[LetterboxdItem] = field(default_factory=list)
    ratings: list[LetterboxdItem] = field(default_factory=list)
    diary: list[LetterboxdItem] = field(default_factory=list)
    lists: dict[str, list[LetterboxdItem]] = field(default_factory=dict)

    @property
    def all_items(self) -> list[LetterboxdItem]:
        """Return all items across all collections in logical processing sequence."""
        items: list[LetterboxdItem] = []
        items.extend(self.watchlist)
        items.extend(self.watched)
        items.extend(self.ratings)
        items.extend(self.diary)
        for shelf_items in self.lists.values():
            items.extend(shelf_items)
        return items


def _parse_date(val: str | None) -> date | None:
    """Parse an ISO date string (YYYY-MM-DD) safely."""
    if not val:
        return None
    val = val.strip()
    if not val:
        return None
    try:
        return date.fromisoformat(val[:10])
    except ValueError:
        try:
            return datetime.strptime(val[:10], "%Y/%m/%d").date()
        except ValueError:
            return None


def _parse_year(val: str | None) -> int | None:
    """Extract a 4-digit release year from a string."""
    if not val:
        return None
    match = re.search(r"\b(18|19|20)\d{2}\b", val.strip())
    if match:
        try:
            return int(match.group(0))
        except ValueError:
            return None
    return None


def _parse_rating(val: str | None) -> float | None:
    """Parse numeric rating score (e.g. 4.5, 4, 10)."""
    if not val:
        return None
    try:
        num = float(val.strip())
        return round(num, 2)
    except ValueError:
        return None


def _parse_bool(val: str | None) -> bool:
    """Parse boolean flag from CSV representations like Yes, true, 1."""
    if not val:
        return False
    return val.strip().lower() in {"yes", "true", "1", "y"}


def _infer_entry_type(filename: str | None, headers: set[str]) -> LetterboxdItemType:
    """Infer the record type from filename or present CSV headers."""
    if filename:
        lower_name = filename.lower()
        if "watchlist" in lower_name:
            return LetterboxdItemType.WATCHLIST
        if "rating" in lower_name:
            return LetterboxdItemType.RATING
        if "diary" in lower_name:
            return LetterboxdItemType.DIARY
        if "watched" in lower_name:
            return LetterboxdItemType.WATCHED
        if "lists" in lower_name or "list" in lower_name:
            return LetterboxdItemType.LIST

    # Infer from header signatures
    if "watched date" in headers or "rewatch" in headers:
        return LetterboxdItemType.DIARY
    if "rating" in headers:
        return LetterboxdItemType.RATING
    if "position" in headers:
        return LetterboxdItemType.LIST
    return LetterboxdItemType.WATCHLIST


class LetterboxdPort(Protocol):
    """Protocol contract for Letterboxd file parsing."""

    def parse_csv(
        self,
        content: str | bytes,
        filename: str | None = None,
        default_type: LetterboxdItemType | None = None,
        list_name: str | None = None,
    ) -> list[LetterboxdItem]:
        """Parse standalone CSV text or bytes into LetterboxdItem entries."""
        ...

    def parse_zip_export(self, zip_bytes: bytes) -> LetterboxdExportArchive:
        """Parse an in-memory Letterboxd export ZIP archive into structured collections."""
        ...


class LetterboxdClient(LetterboxdPort):
    """Concrete adapter for Letterboxd CSV and export archive ingestion."""

    def parse_csv(
        self,
        content: str | bytes,
        filename: str | None = None,
        default_type: LetterboxdItemType | None = None,
        list_name: str | None = None,
    ) -> list[LetterboxdItem]:
        """Parse CSV text or bytes into structured LetterboxdItem instances."""
        if isinstance(content, bytes):
            # Decode with utf-8-sig to automatically strip BOM headers
            text = content.decode("utf-8-sig", errors="replace")
        else:
            text = content.lstrip("\ufeff")

        if not text.strip():
            return []

        reader = csv.DictReader(io.StringIO(text.strip()))
        if not reader.fieldnames:
            return []

        # Normalize header keys to lowercase stripped strings for lookup
        raw_headers = [h.strip() for h in reader.fieldnames if h]
        lower_headers = {h.lower(): h for h in raw_headers}
        entry_type = default_type or _infer_entry_type(
            filename, set(lower_headers.keys())
        )
        if entry_type == LetterboxdItemType.LIST and not list_name and filename:
            clean_name = filename.split("/")[-1].split("\\")[-1]
            if clean_name.lower().endswith(".csv"):
                clean_name = clean_name[:-4]
            list_name = clean_name.replace("-", " ").replace("_", " ").title()

        def get_val(row: dict[str, str], *keys: str) -> str | None:
            for k in keys:
                actual_key = lower_headers.get(k.lower())
                if actual_key and row.get(actual_key):
                    v = row[actual_key].strip()
                    if v:
                        return v
            return None

        items: list[LetterboxdItem] = []
        for row in reader:
            title = get_val(row, "name", "title", "film")
            if not title:
                continue

            year_raw = get_val(row, "year", "release year", "release_year")
            release_year = _parse_year(year_raw)
            uri = get_val(row, "letterboxd uri", "url", "letterboxd_uri", "uri")
            rating = _parse_rating(get_val(row, "rating", "user_rating"))
            watched_date = _parse_date(get_val(row, "watched date", "watched_date"))
            date_logged = _parse_date(get_val(row, "date", "date_logged", "added_at"))
            is_rewatch = _parse_bool(get_val(row, "rewatch", "is_rewatch"))
            review_text = get_val(row, "review", "review text", "description", "note")

            raw_tags = get_val(row, "tags", "tag")
            tags = (
                [t.strip() for t in raw_tags.split(",") if t.strip()]
                if raw_tags
                else []
            )

            raw_rank = get_val(row, "position", "rank", "order")
            list_rank = int(raw_rank) if raw_rank and raw_rank.isdigit() else None

            # If watched_date is not explicit but it's a watched/diary row, use date_logged
            if watched_date is None and entry_type in {
                LetterboxdItemType.WATCHED,
                LetterboxdItemType.DIARY,
            }:
                watched_date = date_logged

            item = LetterboxdItem(
                title=title,
                entry_type=entry_type,
                release_year=release_year,
                letterboxd_uri=uri,
                rating=rating,
                watched_date=watched_date,
                date_logged=date_logged,
                is_rewatch=is_rewatch,
                review_text=review_text,
                tags=tags,
                list_name=list_name,
                list_rank=list_rank,
            )
            items.append(item)

        return items

    def parse_zip_export(self, zip_bytes: bytes) -> LetterboxdExportArchive:
        """Extract and parse all known Letterboxd CSVs from an in-memory ZIP export."""
        archive = LetterboxdExportArchive()
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                for file_info in zf.infolist():
                    if file_info.is_dir() or not file_info.filename.endswith(".csv"):
                        continue

                    filename = file_info.filename.split("/")[-1]
                    lower_path = file_info.filename.lower()
                    content = zf.read(file_info)

                    if filename.lower() == "watchlist.csv":
                        archive.watchlist = self.parse_csv(
                            content,
                            filename=filename,
                            default_type=LetterboxdItemType.WATCHLIST,
                        )
                    elif filename.lower() == "watched.csv":
                        archive.watched = self.parse_csv(
                            content,
                            filename=filename,
                            default_type=LetterboxdItemType.WATCHED,
                        )
                    elif filename.lower() == "ratings.csv":
                        archive.ratings = self.parse_csv(
                            content,
                            filename=filename,
                            default_type=LetterboxdItemType.RATING,
                        )
                    elif filename.lower() == "diary.csv":
                        archive.diary = self.parse_csv(
                            content,
                            filename=filename,
                            default_type=LetterboxdItemType.DIARY,
                        )
                    elif "lists/" in lower_path or "list" in lower_path:
                        # Custom list CSV
                        shelf_title = (
                            filename[:-4].replace("-", " ").replace("_", " ").title()
                        )
                        archive.lists[shelf_title] = self.parse_csv(
                            content,
                            filename=filename,
                            default_type=LetterboxdItemType.LIST,
                            list_name=shelf_title,
                        )
        except zipfile.BadZipFile as exc:
            logger.error("Failed to extract Letterboxd ZIP archive: %s", exc)
            raise ValueError(f"Invalid ZIP archive file: {exc}") from exc

        return archive
