"""Letterboxd HTML parser extracting films, watchlists, ratings, and pagination links."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import lxml.html

from app.adapters.letterboxd.client import LetterboxdItem, LetterboxdItemType

logger = logging.getLogger(__name__)


class LetterboxdHtmlParser:
    """Parser for exported or scraped Letterboxd HTML pages."""

    def parse_html(
        self,
        content: str | bytes,
        default_type: LetterboxdItemType | None = None,
    ) -> tuple[list[LetterboxdItem], str | None]:
        """Parse Letterboxd HTML page into LetterboxdItem entries and next page URL if any.

        Args:
            content: Raw HTML text or bytes.
            default_type: Optional override for item type. If None, inferred from page title.

        Returns:
            Tuple of (list of parsed LetterboxdItems, next_page_url or None).
        """
        if isinstance(content, bytes):
            html_text = content.decode("utf-8", errors="replace")
        else:
            html_text = content

        if not html_text.strip():
            return [], None

        try:
            doc = lxml.html.fromstring(html_text)
        except Exception as exc:
            logger.warning("Failed to parse HTML with lxml: %s", exc)
            return [], None

        title_el = doc.find(".//title")
        page_title = (title_el.text or "").strip() if title_el is not None else ""

        # Detect pagination next link
        next_url: str | None = None
        next_els = doc.cssselect("a.next, .paginate-nextprev a.next")
        if next_els:
            raw_href = next_els[0].get("href")
            if raw_href:
                raw_href = raw_href.strip()
                if raw_href.startswith("/"):
                    next_url = f"https://letterboxd.com{raw_href}"
                elif raw_href.startswith("http"):
                    next_url = raw_href

        # 1. Single film detail page check
        if doc.cssselect("section#userpanel, #featured-film-header"):
            single_item = self._extract_single_film_page(doc)
            return ([single_item] if single_item else []), next_url

        # Determine entry type for collections
        entry_type = default_type
        if entry_type is None:
            lower_title = page_title.lower()
            if "watchlist" in lower_title:
                entry_type = LetterboxdItemType.WATCHLIST
            elif "film" in lower_title or "diary" in lower_title or "watched" in lower_title:
                entry_type = LetterboxdItemType.WATCHED
            else:
                entry_type = LetterboxdItemType.WATCHED

        # 2. Look for list items (standard Letterboxd grid)
        grid_items = doc.cssselect("li.griditem")
        items: list[LetterboxdItem] = []
        seen_keys: set[tuple[str, int | None]] = set()

        if grid_items:
            for li in grid_items:
                item = self._extract_item_from_node(li, entry_type)
                if item:
                    key = (item.title.lower(), item.release_year)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        items.append(item)
        else:
            # Fallback to direct poster extraction if griditem li is not present
            poster_nodes = doc.cssselect(
                "div.react-component[data-component-class='LazyPoster'], div.poster[data-target-link], div.film-poster"
            )
            for node in poster_nodes:
                item = self._extract_item_from_node(node, entry_type)
                if item:
                    key = (item.title.lower(), item.release_year)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        items.append(item)

        return items, next_url

    def _extract_single_film_page(self, doc: Any) -> LetterboxdItem | None:
        """Extract movie identity and personal rating from a single film detail page."""
        og_title = doc.cssselect("meta[property='og:title']")
        raw_name = og_title[0].get("content") if og_title else None
        if not raw_name:
            h1 = doc.cssselect("h1.headline-1, .film-title-wrapper")
            if h1:
                raw_name = h1[0].text_content()

        if not raw_name:
            return None

        clean_name = raw_name.strip()
        title = clean_name
        year: int | None = None
        year_match = re.search(r"^(.*?)(?:\s+\((\d{4})\))?$", clean_name)
        if year_match:
            matched_title = year_match.group(1).strip()
            if matched_title:
                title = matched_title
            if year_match.group(2):
                try:
                    year = int(year_match.group(2))
                except ValueError:
                    year = None

        og_url = doc.cssselect("meta[property='og:url']")
        uri = og_url[0].get("content") if og_url else None

        # Check user rating on the page
        rating: float | None = None
        checked_radio = doc.cssselect("section#userpanel input[type='radio'][checked]")
        for cr in checked_radio:
            val = cr.get("value")
            if val and val.isdigit() and int(val) > 0:
                rating = int(val) / 2.0  # 1-10 to 0.5-5.0

        is_watched = bool(doc.cssselect("section#userpanel [data-is-watched='true']"))
        is_watchlist = bool(doc.cssselect("section#userpanel [data-is-in-watchlist='true']"))

        if not is_watched and not is_watchlist and rating is None:
            # No user interaction recorded on this page
            return None

        entry_type = LetterboxdItemType.WATCHLIST if (is_watchlist and not is_watched) else LetterboxdItemType.WATCHED

        return LetterboxdItem(
            title=title,
            entry_type=entry_type,
            release_year=year,
            letterboxd_uri=uri,
            rating=rating,
        )

    def _extract_item_from_node(
        self,
        node: Any,
        entry_type: LetterboxdItemType,
    ) -> LetterboxdItem | None:
        """Extract a single LetterboxdItem from an HTML node (either li.griditem or poster div)."""
        raw_name: str | None = None
        slug: str | None = None

        # Check for React LazyPoster component
        lazy_posters = node.cssselect("div[data-component-class='LazyPoster']") if node.tag == "li" else [node]
        if lazy_posters and lazy_posters[0].get("data-item-name"):
            raw_name = lazy_posters[0].get("data-item-name")
            slug = lazy_posters[0].get("data-item-slug")

        # Fallback to poster div or img attributes
        if not raw_name:
            poster_divs = node.cssselect("div.poster, div.film-poster") if node.tag == "li" else [node]
            if poster_divs:
                p_div = poster_divs[0]
                target_link = p_div.get("data-target-link")
                if target_link:
                    m = re.search(r"/film/([^/]+)/?", target_link)
                    if m:
                        slug = m.group(1)
                raw_name = p_div.get("data-film-name")
                if not raw_name:
                    imgs = p_div.cssselect("img")
                    if imgs:
                        raw_name = imgs[0].get("alt")

        if not raw_name:
            return None

        clean_name = raw_name.strip()
        if clean_name.lower().startswith("poster for "):
            clean_name = clean_name[11:].strip()

        # Extract title and release year: e.g. "The Florida Project (2017)"
        title = clean_name
        year: int | None = None
        year_match = re.search(r"^(.*?)(?:\s+\((\d{4})\))?$", clean_name)
        if year_match:
            matched_title = year_match.group(1).strip()
            if matched_title:
                title = matched_title
            if year_match.group(2):
                try:
                    year = int(year_match.group(2))
                except ValueError:
                    year = None

        # Extract rating if present
        rating: float | None = None
        rating_spans = node.cssselect("span.rating")
        for s in rating_spans:
            cls = s.get("class", "")
            rm = re.search(r"rated-(\d+)", cls)
            if rm:
                # Letterboxd half-star scale is 1 to 10 in CSS (e.g. rated-4 = 2.0 stars)
                rating = int(rm.group(1)) / 2.0
                break

        effective_type = entry_type
        if rating is not None and effective_type == LetterboxdItemType.WATCHED:
            effective_type = LetterboxdItemType.WATCHED

        uri = f"https://letterboxd.com/film/{slug}/" if slug else None

        return LetterboxdItem(
            title=title,
            entry_type=effective_type,
            release_year=year,
            letterboxd_uri=uri,
            rating=rating,
        )

    def parse_local_folder(
        self,
        folder_path: Path | str = "for scraping",
    ) -> list[LetterboxdItem]:
        """Read and parse all saved Letterboxd HTML files from a local directory.

        Deduplicates items and merges ratings with watchlist items.
        """
        folder = Path(folder_path)
        if not folder.is_dir():
            logger.warning("Letterboxd scraping directory '%s' does not exist.", folder)
            return []

        merged: dict[tuple[str, int | None], LetterboxdItem] = {}

        for file_path in sorted(folder.glob("*.htm*")):
            lower_name = file_path.name.lower()
            # Skip search result pages and internal asset folders
            if "search" in lower_name:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                items, _ = self.parse_html(content)
                for item in items:
                    key = (item.title.lower(), item.release_year)
                    if key not in merged:
                        merged[key] = item
                    else:
                        existing = merged[key]
                        # If existing had no rating and new has rating, update rating
                        if existing.rating is None and item.rating is not None:
                            existing.rating = item.rating
                        # If existing is WATCHLIST and new is WATCHED, upgrade to WATCHED
                        if existing.entry_type == LetterboxdItemType.WATCHLIST and item.entry_type == LetterboxdItemType.WATCHED:
                            existing.entry_type = LetterboxdItemType.WATCHED
                        # If existing had no URI and new has URI, update URI
                        if not existing.letterboxd_uri and item.letterboxd_uri:
                            existing.letterboxd_uri = item.letterboxd_uri
            except Exception as exc:
                logger.warning("Failed parsing HTML file '%s': %s", file_path.name, exc)

        return list(merged.values())
