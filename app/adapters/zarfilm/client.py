"""Zarfilm browser automation adapter using DrissionPage.

Extracts search results and direct download links from Zarfilm,
scoring candidate releases based on Persian SoftSub, resolution, and codec preferences.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import quote_plus

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def parse_size_bytes(size_str: str | None) -> int | None:
    """Parse human readable size string like '2.4 GB' or '850 MB' to bytes."""
    if not size_str:
        return None
    cleaned = size_str.strip().upper()
    match = re.search(r"([\d.]+)\s*([KMGT]?B|GIB|MIB|KIB)", cleaned)
    if not match:
        return None
    val_str, unit = match.groups()
    try:
        val = float(val_str)
    except ValueError:
        return None

    unit_multipliers = {
        "B": 1,
        "KB": 1024,
        "KIB": 1024,
        "MB": 1024**2,
        "MIB": 1024**2,
        "GB": 1024**3,
        "GIB": 1024**3,
        "TB": 1024**4,
        "TIB": 1024**4,
    }
    multiplier = unit_multipliers.get(unit, 1)
    return int(val * multiplier)


def parse_resolution(text: str | None) -> str | None:
    """Detect resolution token from quality or filename string."""
    if not text:
        return None
    lowered = text.lower()
    if "2160p" in lowered or "4k" in lowered or "uhd" in lowered:
        return "2160p"
    if "1080p" in lowered or "fhd" in lowered:
        return "1080p"
    if "720p" in lowered or "hd" in lowered:
        return "720p"
    if "480p" in lowered or "sd" in lowered:
        return "480p"
    return None


def detect_x265(text: str | None) -> bool:
    """Check if quality label indicates x265 / HEVC / 10bit."""
    if not text:
        return False
    lowered = text.lower()
    return "x265" in lowered or "hevc" in lowered or "10bit" in lowered


@dataclass(slots=True)
class ZarfilmMovieCard:
    """Movie card extracted from Zarfilm search results."""

    title: str
    year: str | None
    href: str
    imdb_rating: str | None = None
    genres: list[str] = field(default_factory=list)
    plot: str | None = None


@dataclass(slots=True)
class ZarfilmReleaseCandidate:
    """A direct download link candidate extracted from Zarfilm."""

    download_url: str
    source_page_url: str | None = None
    quality_label: str | None = None
    resolution: str | None = None
    encoder: str | None = None
    size_text: str | None = None
    size_bytes: int | None = None
    is_dubbed: bool = False
    has_persian_sub: bool = False
    is_x265: bool = False


class ZarfilmPort(Protocol):
    """Protocol contract for Zarfilm browser scraping operations."""

    def search_cards(
        self, title: str, year: int | str | None = None
    ) -> list[ZarfilmMovieCard]:
        """Search Zarfilm and return extracted movie cards."""
        ...

    def extract_releases(self, movie_page_url: str) -> list[ZarfilmReleaseCandidate]:
        """Extract available download releases from a movie page."""
        ...

    def match_card(
        self,
        cards: list[ZarfilmMovieCard],
        title: str,
        year: int | str | None = None,
        llm_verifier: Any | None = None,
    ) -> ZarfilmMovieCard | None:
        """Find the closest matching card among search results."""
        ...

    def search_and_extract(
        self,
        title: str,
        year: int | str | None = None,
        llm_verifier: Any | None = None,
    ) -> tuple[str | None, list[ZarfilmReleaseCandidate]]:
        """Search for a movie, find the best matching card, and extract its releases."""
        ...

    def score_candidate(
        self,
        candidate: ZarfilmReleaseCandidate,
        preferred_quality: str = "1080p",
        prefer_x265: bool = True,
    ) -> int:
        """Compute score for candidate release based on user preferences."""
        ...

    def pick_best_release(
        self,
        releases: list[ZarfilmReleaseCandidate],
        preferred_quality: str = "1080p",
        prefer_x265: bool = True,
        llm_selector: Any | None = None,
        title: str = "",
        year: int | str | None = None,
    ) -> ZarfilmReleaseCandidate | None:
        """Pick the highest scoring release from candidate options."""
        ...

    def close(self) -> None:
        """Close browser resources."""
        ...


class ZarfilmBrowserClient:
    """DrissionPage-based browser client for Zarfilm."""

    def __init__(
        self,
        settings: Settings | None = None,
        headless: bool = False,
    ) -> None:
        self.settings = settings or get_settings()
        self.base_url = self.settings.zarfilm_base_url.rstrip("/")
        self.profile_dir = self.settings.zarfilm_profile_dir
        self.headless = headless
        self._page: Any = None
        self._lock = threading.Lock()

    def _ensure_page(self) -> Any:
        """Instantiate ChromiumPage with persistent user profile if not running."""
        if self._page is None:
            try:
                from DrissionPage import ChromiumOptions, ChromiumPage  # type: ignore[import-untyped]
            except ImportError as exc:
                raise RuntimeError(
                    "DrissionPage is not installed. Please install DrissionPage to scrape Zarfilm."
                ) from exc

            co = ChromiumOptions()
            self.settings.ensure_directories()
            co.set_user_data_path(str(self.profile_dir))
            if self.headless:
                co.headless(True)
            self._page = ChromiumPage(co)
        return self._page

    def search_cards(
        self, title: str, year: int | str | None = None
    ) -> list[ZarfilmMovieCard]:
        """Search Zarfilm and return parsed movie cards."""
        with self._lock:
            page = self._ensure_page()
            query_str = quote_plus(title)
            search_url = f"{self.base_url}/?s={query_str}"
            logger.info("Opening Zarfilm search for '%s': %s", title, search_url)
            page.get(search_url)

            raw_cards = page.eles("css:article.zf-card-movie")
            cards: list[ZarfilmMovieCard] = []

            for card in raw_cards[:15]:
                link_el = card.ele("css:a.zf-card-link")
                if not link_el:
                    continue
                href = link_el.attr("href") or ""
                if not href:
                    continue

                title_el = card.ele("css:.zf-card-title")
                year_el = card.ele("css:.zf-card-year")
                rating_el = card.ele("css:.zf-card-rating b")
                plot_el = card.ele("css:.zf-card-story-panel p")
                genre_els = card.eles("css:.zf-card-genre-chips span")

                c_title = (title_el.text if title_el else "").strip()
                c_year = (year_el.text if year_el else "").strip() or None
                c_rating = (rating_el.text if rating_el else "").strip() or None
                c_plot = (plot_el.text if plot_el else "").strip() or None
                c_genres = [g.text.strip() for g in genre_els if g.text]

                cards.append(
                    ZarfilmMovieCard(
                        title=c_title,
                        year=c_year,
                        href=href,
                        imdb_rating=c_rating,
                        genres=c_genres,
                        plot=c_plot,
                    )
                )

            logger.info("Found %d movie cards on Zarfilm for '%s'", len(cards), title)
            return cards

    def match_card(
        self,
        cards: list[ZarfilmMovieCard],
        title: str,
        year: int | str | None = None,
        llm_verifier: Any | None = None,
    ) -> ZarfilmMovieCard | None:
        """Find best matching movie card from list of cards, optionally using LLM verifier."""
        if not cards:
            return None

        # 0. Try LLM verifier if provided
        if callable(llm_verifier):
            try:
                card_dicts = [
                    {
                        "index": idx,
                        "title": c.title,
                        "year": c.year,
                        "href": c.href,
                        "imdb_rating": c.imdb_rating,
                        "genres": c.genres,
                        "plot": c.plot,
                    }
                    for idx, c in enumerate(cards)
                ]
                idx, reason = llm_verifier(title, year, card_dicts)
                if idx is not None and 0 <= idx < len(cards):
                    logger.info("LLM verified movie card index %d for '%s' (%s): %s", idx, title, year, reason)
                    return cards[idx]
                if idx == -1:
                    logger.info("LLM explicitly verified that no card matches '%s' (%s): %s", title, year, reason)
                    return None
            except Exception as exc:  # noqa: BLE001
                logger.warning("LLM verifier failed, falling back to heuristic: %s", exc)

        title_clean = title.strip().lower()
        year_str = str(year).strip() if year is not None else None

        # 1. Exact title match and exact year match
        for card in cards:
            card_title = card.title.strip().lower()
            if card_title == title_clean and (not year_str or card.year == year_str):
                return card

        # 2. Substring title match with year match
        if year_str:
            for card in cards:
                card_title = card.title.strip().lower()
                if (
                    title_clean in card_title or card_title in title_clean
                ) and card.year == year_str:
                    return card

        # 3. Exact title match (any year)
        for card in cards:
            if card.title.strip().lower() == title_clean:
                return card

        # 4. Fallback to first card if only one card found
        if len(cards) == 1:
            return cards[0]

        return None

    def extract_releases(self, movie_page_url: str) -> list[ZarfilmReleaseCandidate]:
        """Extract available download options from a Zarfilm single movie page."""
        with self._lock:
            page = self._ensure_page()
            logger.info("Opening Zarfilm movie page: %s", movie_page_url)
            page.get(movie_page_url)

            rows = page.eles("css:.item_row_dl")
            releases: list[ZarfilmReleaseCandidate] = []

            for row in rows:
                btn = (
                    row.ele("css:a.dllink.subtitle_link")
                    or row.ele("css:a.dllink.double_link")
                    or row.ele("css:a.dllink")
                )
                if not btn:
                    continue

                btn_class = btn.attr("class") or ""
                if "sound_link" in btn_class:
                    continue

                href = btn.attr("href") or ""
                if not href.startswith("http"):
                    continue

                is_softsub = "subtitle_link" in btn_class
                is_dubbed = "double_link" in btn_class

                q_el = row.ele("css:.quality_name")
                s_el = row.ele("css:.size_meta .value")
                e_el = row.ele("css:.encoder_name")

                quality_name = (q_el.text if q_el else "").strip()
                size_text = (s_el.text if s_el else "").strip() or None
                encoder_text = (e_el.text if e_el else "").strip() or None

                resolution = parse_resolution(quality_name) or parse_resolution(href)
                is_x265 = detect_x265(quality_name) or detect_x265(href)
                size_bytes = parse_size_bytes(size_text)

                label_parts = [quality_name]
                if encoder_text:
                    label_parts.append(f"({encoder_text})")
                quality_label = " ".join(filter(None, label_parts)) or "Standard"

                releases.append(
                    ZarfilmReleaseCandidate(
                        download_url=href,
                        source_page_url=movie_page_url,
                        quality_label=quality_label,
                        resolution=resolution,
                        encoder=encoder_text,
                        size_text=size_text,
                        size_bytes=size_bytes,
                        is_dubbed=is_dubbed,
                        has_persian_sub=is_softsub,
                        is_x265=is_x265,
                    )
                )

            logger.info(
                "Extracted %d download options from %s", len(releases), movie_page_url
            )
            return releases

    def search_and_extract(
        self,
        title: str,
        year: int | str | None = None,
        llm_verifier: Any | None = None,
    ) -> tuple[str | None, list[ZarfilmReleaseCandidate]]:
        """Search for movie on Zarfilm, select best match card, and extract all releases."""
        cards = self.search_cards(title, year)
        matched = self.match_card(cards, title, year, llm_verifier=llm_verifier)
        if not matched:
            logger.warning(
                "No matching movie card found on Zarfilm for '%s' (%s)", title, year
            )
            return None, []

        releases = self.extract_releases(matched.href)
        return matched.href, releases

    def score_candidate(
        self,
        candidate: ZarfilmReleaseCandidate,
        preferred_quality: str = "1080p",
        prefer_x265: bool = True,
    ) -> int:
        """Score candidate release based on priority: SoftSub (+20), resolution (+10), x265 (+5)."""
        score = 0
        if candidate.has_persian_sub:
            score += 20
        if not candidate.is_dubbed:
            score += 10
        if (
            candidate.resolution
            and preferred_quality.lower() in candidate.resolution.lower()
            or candidate.quality_label
            and preferred_quality.lower() in candidate.quality_label.lower()
        ):
            score += 10
        if (
            prefer_x265
            and candidate.is_x265
            or not prefer_x265
            and not candidate.is_x265
        ):
            score += 5
        return score

    def pick_best_release(
        self,
        releases: list[ZarfilmReleaseCandidate],
        preferred_quality: str = "1080p",
        prefer_x265: bool = True,
        llm_selector: Any | None = None,
        title: str = "",
        year: int | str | None = None,
    ) -> ZarfilmReleaseCandidate | None:
        """Return the highest scoring release from candidates, optionally using LLM selector."""
        if not releases:
            return None

        if callable(llm_selector):
            try:
                candidate_dicts = [
                    {
                        "quality_label": r.quality_label,
                        "resolution": r.resolution,
                        "encoder": r.encoder,
                        "size_text": r.size_text,
                        "is_dubbed": r.is_dubbed,
                        "has_persian_sub": r.has_persian_sub,
                        "is_x265": r.is_x265,
                        "href": r.download_url,
                        "section_type": "SoftSub" if r.has_persian_sub else ("Dubbed" if r.is_dubbed else "Standard"),
                    }
                    for r in releases
                ]
                pref_prompt = f"Preferred quality: {preferred_quality}, prefer x265/HEVC: {prefer_x265}"
                idx, reason = llm_selector(title, year, candidate_dicts, pref_prompt)
                if idx is not None and 0 <= idx < len(releases):
                    logger.info("LLM selected release index %d for '%s': %s", idx, title, reason)
                    return releases[idx]
            except Exception as exc:  # noqa: BLE001
                logger.warning("LLM release selector failed, falling back to heuristic: %s", exc)

        # Prefer non-dubbed softsub releases if any exist
        softsub_candidates = [
            r for r in releases if r.has_persian_sub and not r.is_dubbed
        ]
        pool = softsub_candidates if softsub_candidates else releases

        return max(
            pool,
            key=lambda c: self.score_candidate(
                c, preferred_quality=preferred_quality, prefer_x265=prefer_x265
            ),
        )

    def close(self) -> None:
        """Safely close browser page."""
        with self._lock:
            if self._page is not None:
                try:
                    self._page.quit()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Error closing ChromiumPage: %s", exc)
                finally:
                    self._page = None
