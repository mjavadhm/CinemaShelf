"""Unit tests for Letterboxd browser automation scraper."""

from unittest.mock import MagicMock, patch

import pytest

from app.adapters.letterboxd import LetterboxdBrowserScraper
from app.adapters.letterboxd.client import LetterboxdItemType


@pytest.fixture
def scraper() -> LetterboxdBrowserScraper:
    instance = LetterboxdBrowserScraper()
    instance._page = MagicMock()
    return instance


def test_scraper_multi_page_films(scraper: LetterboxdBrowserScraper) -> None:
    page_1_html = """
    <html>
      <head><title>user’s films</title></head>
      <body>
        <li class="griditem">
          <div class="react-component" data-component-class="LazyPoster" data-item-name="Movie One (2020)" data-item-slug="movie-one"></div>
          <span class="rating rated-8"></span>
        </li>
        <a class="next" href="/user/films/page/2/">Next</a>
      </body>
    </html>
    """
    page_2_html = """
    <html>
      <head><title>user’s films</title></head>
      <body>
        <li class="griditem">
          <div class="react-component" data-component-class="LazyPoster" data-item-name="Movie Two (2021)" data-item-slug="movie-two"></div>
          <span class="rating rated-10"></span>
        </li>
      </body>
    </html>
    """
    scraper._page.html = page_1_html

    def fake_get(url: str) -> None:
        if "page/2" in url:
            scraper._page.html = page_2_html

    scraper._page.get.side_effect = fake_get

    items = scraper.scrape_user_films("user", max_pages=5)
    assert len(items) == 2
    assert items[0].title == "Movie One"
    assert items[0].rating == 4.0
    assert items[1].title == "Movie Two"
    assert items[1].rating == 5.0
    assert scraper._page.get.call_count == 2


def test_scraper_rate_film_with_slug(scraper: LetterboxdBrowserScraper) -> None:
    mock_panel = MagicMock()
    mock_radio = MagicMock()
    mock_radio.attr.return_value = "star_radio_8"
    mock_label = MagicMock()

    def ele_fn(selector: str) -> MagicMock | None:
        if "value=" in selector:
            return mock_radio
        if "star_radio_8" in selector:
            return mock_label
        if "actions-panel" in selector or "userpanel" in selector:
            return mock_panel
        return None

    scraper._page.ele.side_effect = ele_fn

    success = scraper.rate_film(
        title="Inception",
        rating_out_of_10=8,
        year=2010,
        slug="inception",
    )
    assert success is True
    scraper._page.get.assert_called_with("https://letterboxd.com/film/inception/")
    mock_label.click.assert_called_once()
