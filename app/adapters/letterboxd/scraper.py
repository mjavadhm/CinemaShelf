"""Letterboxd browser automation adapter using DrissionPage.

Supports multi-page scraping of watched films and watchlists, persistent session login,
and automated rating submission.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any, Protocol
from urllib.parse import quote_plus

from app.adapters.letterboxd.client import LetterboxdItem, LetterboxdItemType
from app.adapters.letterboxd.parser import LetterboxdHtmlParser
from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class LetterboxdScraperPort(Protocol):
    """Protocol contract for Letterboxd browser scraping operations."""

    def open_browser(self, url: str = "https://letterboxd.com") -> None:
        """Open the browser with persistent profile for user login."""
        ...

    def scrape_user_films(self, username: str, max_pages: int = 50) -> list[LetterboxdItem]:
        """Scrape all pages of a user's watched films."""
        ...

    def scrape_user_watchlist(self, username: str, max_pages: int = 50) -> list[LetterboxdItem]:
        """Scrape all pages of a user's watchlist."""
        ...

    def scrape_all(self, username: str, max_pages: int = 50) -> list[LetterboxdItem]:
        """Scrape both watched films and watchlist, returning merged items."""
        ...

    def rate_film(
        self,
        title: str,
        rating_out_of_10: int,
        year: int | None = None,
        slug: str | None = None,
    ) -> bool:
        """Submit a rating on Letterboxd for a movie."""
        ...


class LetterboxdBrowserScraper(LetterboxdScraperPort):
    """Browser automation adapter using DrissionPage for Letterboxd."""

    def __init__(
        self,
        settings: Settings | None = None,
        headless: bool = False,
    ) -> None:
        self.settings = settings or get_settings()
        self.profile_dir = self.settings.letterboxd_profile_dir
        self.headless = headless
        self._page: Any = None
        self._lock = threading.Lock()
        self.parser = LetterboxdHtmlParser()

    def _ensure_page(self) -> Any:
        """Instantiate ChromiumPage with persistent profile if not running."""
        if self._page is None:
            try:
                from DrissionPage import ChromiumOptions, ChromiumPage  # type: ignore[import-untyped]
            except ImportError as exc:
                raise RuntimeError(
                    "DrissionPage is not installed. Please install DrissionPage to automate Letterboxd."
                ) from exc

            co = ChromiumOptions()
            self.settings.ensure_directories()
            co.set_user_data_path(str(self.profile_dir))
            if self.headless:
                co.headless(True)
            self._page = ChromiumPage(co)
        return self._page

    def open_browser(self, url: str = "https://letterboxd.com") -> None:
        """Open visible browser to Letterboxd so user can log in or verify credentials."""
        with self._lock:
            page = self._ensure_page()
            logger.info("Opening Letterboxd browser to: %s", url)
            page.get(url)

    def scrape_user_films(self, username: str, max_pages: int = 50) -> list[LetterboxdItem]:
        """Scrape all pages of a user's films collection following pagination."""
        clean_user = username.strip().lstrip("@")
        current_url = f"https://letterboxd.com/{clean_user}/films/"
        all_items: list[LetterboxdItem] = []
        page_num = 1

        with self._lock:
            page = self._ensure_page()
            while current_url and page_num <= max_pages:
                logger.info("Scraping Letterboxd films page %d: %s", page_num, current_url)
                page.get(current_url)
                # Wait for posters to load
                try:
                    page.wait.eles_loaded("css:li.griditem, div[data-component-class='LazyPoster']", timeout=8)
                except Exception:
                    logger.debug("Timeout waiting for grid items on page %d", page_num)

                html_content = page.html
                items, next_url = self.parser.parse_html(
                    html_content,
                    default_type=LetterboxdItemType.WATCHED,
                )
                logger.info("Parsed %d films from page %d", len(items), page_num)
                all_items.extend(items)

                if not next_url or next_url == current_url:
                    break

                current_url = next_url
                page_num += 1
                time.sleep(0.5)

        return all_items

    def scrape_user_watchlist(self, username: str, max_pages: int = 50) -> list[LetterboxdItem]:
        """Scrape all pages of a user's watchlist following pagination."""
        clean_user = username.strip().lstrip("@")
        current_url = f"https://letterboxd.com/{clean_user}/watchlist/"
        all_items: list[LetterboxdItem] = []
        page_num = 1

        with self._lock:
            page = self._ensure_page()
            while current_url and page_num <= max_pages:
                logger.info("Scraping Letterboxd watchlist page %d: %s", page_num, current_url)
                page.get(current_url)
                try:
                    page.wait.eles_loaded("css:li.griditem, div[data-component-class='LazyPoster']", timeout=8)
                except Exception:
                    logger.debug("Timeout waiting for grid items on watchlist page %d", page_num)

                html_content = page.html
                items, next_url = self.parser.parse_html(
                    html_content,
                    default_type=LetterboxdItemType.WATCHLIST,
                )
                logger.info("Parsed %d watchlist items from page %d", len(items), page_num)
                all_items.extend(items)

                if not next_url or next_url == current_url:
                    break

                current_url = next_url
                page_num += 1
                time.sleep(0.5)

        return all_items

    def scrape_all(self, username: str, max_pages: int = 50) -> list[LetterboxdItem]:
        """Scrape both films and watchlist, returning merged and deduplicated items."""
        films = self.scrape_user_films(username, max_pages=max_pages)
        watchlist = self.scrape_user_watchlist(username, max_pages=max_pages)

        merged: dict[tuple[str, int | None], LetterboxdItem] = {}
        for item in films:
            key = (item.title.lower(), item.release_year)
            merged[key] = item

        for item in watchlist:
            key = (item.title.lower(), item.release_year)
            if key not in merged:
                merged[key] = item
            else:
                # If already in films as watched, retain watched status
                pass

        return list(merged.values())

    def rate_film(
        self,
        title: str,
        rating_out_of_10: int,
        year: int | None = None,
        slug: str | None = None,
    ) -> bool:
        """Submit a rating on Letterboxd for a movie.

        Args:
            title: Movie title.
            rating_out_of_10: Score from 1 to 10 (half stars, e.g. 8 = 4 stars).
            year: Release year for search disambiguation.
            slug: Letterboxd film slug (e.g. 'astro-2024') if already known.

        Returns:
            True if rating was successfully applied.
        """
        score = max(1, min(10, rating_out_of_10))

        with self._lock:
            page = self._ensure_page()

            # 1. Navigate to film page
            if slug:
                film_url = f"https://letterboxd.com/film/{slug}/"
                logger.info("Navigating directly to Letterboxd film url: %s", film_url)
                page.get(film_url)
            else:
                search_query = quote_plus(title)
                search_url = f"https://letterboxd.com/search/{search_query}/"
                logger.info("Searching Letterboxd for '%s': %s", title, search_url)
                page.get(search_url)

                try:
                    page.wait.eles_loaded("css:ul.results li, .search-result", timeout=8)
                except Exception:
                    pass

                # Find result matching film
                results = page.eles("css:ul.results li")
                matched_href: str | None = None

                for r in results:
                    link_el = r.ele("css:h2 a, a.film-title-wrapper, a")
                    if not link_el:
                        continue
                    href = link_el.attr("href") or ""
                    if "/film/" not in href:
                        continue

                    r_text = link_el.text or ""
                    # Check year if available
                    if year:
                        y_match = re.search(r"\b(18|19|20)\d{2}\b", r_text)
                        if y_match and int(y_match.group(0)) == year:
                            matched_href = href
                            break
                    elif not matched_href:
                        matched_href = href

                if not matched_href and results:
                    # Fallback to first film link
                    first_link = results[0].ele("css:a[href*='/film/']")
                    if first_link:
                        matched_href = first_link.attr("href")

                if not matched_href:
                    logger.warning("No matching Letterboxd film found for '%s' (%s)", title, year)
                    raise RuntimeError(f"Could not find film '{title}' on Letterboxd")

                logger.info("Opening matched film page: %s", matched_href)
                page.get(matched_href)

            # 2. On film page, locate user rating panel
            try:
                page.wait.eles_loaded("css:section.actions-panel, #userpanel", timeout=8)
            except Exception:
                pass

            actions_panel = page.ele("css:section.actions-panel, #userpanel")
            if not actions_panel:
                raise RuntimeError(
                    "Actions panel not found. Please ensure you are logged into Letterboxd."
                )

            # Check if signin prompt is visible
            signin_btn = page.ele("css:.js-header-signin-form, a.js-nav-account-signin")
            if signin_btn and "display: none" not in (signin_btn.attr("style") or ""):
                # User might not be logged in
                pass

            # 3. Locate rating radio or label for value
            # Values are 1 to 10
            radio = page.ele(f"css:section.actions-panel input[type='radio'][value='{score}']")
            clicked = False

            if radio:
                radio_id = radio.attr("id")
                if radio_id:
                    label = page.ele(f"css:label[for='{radio_id}']")
                    if label:
                        label.click()
                        clicked = True

                if not clicked:
                    # Click via JS or directly
                    page.run_js("arguments[0].click();", radio)
                    clicked = True

            if not clicked:
                # Try finding star trigger by aria-label or star index
                star_triggers = page.eles("css:section.actions-panel label.n70ETG_star-trigger, .rateit .rateit-star")
                if len(star_triggers) >= score:
                    star_triggers[score - 1].click()
                    clicked = True

            if not clicked:
                raise RuntimeError(f"Could not find rating element for score {score} on Letterboxd")

            time.sleep(1.0)
            logger.info("Successfully submitted rating %d/10 for '%s' on Letterboxd", score, title)
            return True
