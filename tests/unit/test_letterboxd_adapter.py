"""Unit tests for Letterboxd CSV and ZIP export parsing adapter."""

import io
import zipfile
from datetime import date

import pytest

from app.adapters.letterboxd import (
    LetterboxdClient,
    LetterboxdItemType,
)


@pytest.fixture
def adapter() -> LetterboxdClient:
    return LetterboxdClient()


def test_parse_standard_watchlist_csv(adapter: LetterboxdClient) -> None:
    content = """Date,Name,Year,Letterboxd URI
2024-01-10,Children of Men,2006,https://boxd.it/29pC
2024-01-11,Ex Machina,2014,https://boxd.it/70zS
"""
    items = adapter.parse_csv(content, filename="watchlist.csv")
    assert len(items) == 2
    assert items[0].title == "Children of Men"
    assert items[0].release_year == 2006
    assert items[0].letterboxd_uri == "https://boxd.it/29pC"
    assert items[0].entry_type == LetterboxdItemType.WATCHLIST
    assert items[0].date_logged == date(2024, 1, 10)

    assert items[1].title == "Ex Machina"
    assert items[1].release_year == 2014


def test_parse_legacy_simple_csv(adapter: LetterboxdClient) -> None:
    content = """Name,Year
Sympathy for Mr. Vengeance,2002
Lady Vengeance,2005
"""
    items = adapter.parse_csv(content)
    assert len(items) == 2
    assert items[0].title == "Sympathy for Mr. Vengeance"
    assert items[0].release_year == 2002
    assert items[0].entry_type == LetterboxdItemType.WATCHLIST


def test_parse_ratings_csv(adapter: LetterboxdClient) -> None:
    content = """Date,Name,Year,Letterboxd URI,Rating
2023-05-12,The Social Network,2010,https://boxd.it/17yM,4.5
2023-05-15,Festen,1998,https://boxd.it/1b1G,4.0
"""
    items = adapter.parse_csv(content, filename="ratings.csv")
    assert len(items) == 2
    assert items[0].title == "The Social Network"
    assert items[0].rating == 4.5
    assert items[0].entry_type == LetterboxdItemType.RATING
    assert items[1].rating == 4.0


def test_parse_diary_csv(adapter: LetterboxdClient) -> None:
    content = """Date,Name,Year,Letterboxd URI,Rating,Rewatch,Tags,Watched Date
2023-08-01,The Master,2012,https://boxd.it/2W34,5.0,Yes,"pta, 35mm",2023-07-31
"""
    items = adapter.parse_csv(content, filename="diary.csv")
    assert len(items) == 1
    assert items[0].title == "The Master"
    assert items[0].rating == 5.0
    assert items[0].is_rewatch is True
    assert items[0].watched_date == date(2023, 7, 31)
    assert items[0].tags == ["pta", "35mm"]
    assert items[0].entry_type == LetterboxdItemType.DIARY


def test_parse_custom_list_csv(adapter: LetterboxdClient) -> None:
    content = """Position,Name,Year,URL,Description
1,Cure,1997,https://boxd.it/170g,Masterpiece psychological thriller
2,Identity,2003,https://boxd.it/289q,Fun rainy motel mystery
"""
    items = adapter.parse_csv(
        content,
        filename="favorite-thrillers.csv",
        default_type=LetterboxdItemType.LIST,
        list_name="Favorite Thrillers",
    )
    assert len(items) == 2
    assert items[0].title == "Cure"
    assert items[0].list_rank == 1
    assert items[0].review_text == "Masterpiece psychological thriller"
    assert items[0].list_name == "Favorite Thrillers"
    assert items[1].list_rank == 2


def test_parse_utf8_bom_content(adapter: LetterboxdClient) -> None:
    raw_bytes = b"\xef\xbb\xbfName,Year\nUnbreakable,2000\n"
    items = adapter.parse_csv(raw_bytes)
    assert len(items) == 1
    assert items[0].title == "Unbreakable"
    assert items[0].release_year == 2000


def test_parse_empty_csv(adapter: LetterboxdClient) -> None:
    assert adapter.parse_csv("") == []
    assert adapter.parse_csv("Name,Year\n") == []


def test_parse_zip_export(adapter: LetterboxdClient) -> None:
    # Build in-memory ZIP with watchlist, ratings, and a custom list
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr(
            "watchlist.csv",
            "Date,Name,Year,Letterboxd URI\n2024-01-01,In the House,2012,https://boxd.it/4kik\n",
        )
        zf.writestr(
            "ratings.csv",
            "Date,Name,Year,Letterboxd URI,Rating\n2024-01-02,Dogtooth,2009,https://boxd.it/1r2S,4.0\n",
        )
        zf.writestr(
            "lists/top-noir.csv",
            "Position,Name,Year,URL\n1,Primal Fear,1996,https://boxd.it/1Y6g\n",
        )

    zip_bytes = zip_buffer.getvalue()
    archive = adapter.parse_zip_export(zip_bytes)

    assert len(archive.watchlist) == 1
    assert archive.watchlist[0].title == "In the House"
    assert archive.watchlist[0].entry_type == LetterboxdItemType.WATCHLIST

    assert len(archive.ratings) == 1
    assert archive.ratings[0].title == "Dogtooth"
    assert archive.ratings[0].rating == 4.0

    assert "Top Noir" in archive.lists
    assert len(archive.lists["Top Noir"]) == 1
    assert archive.lists["Top Noir"][0].title == "Primal Fear"

    assert len(archive.all_items) == 3


def test_parse_invalid_zip_raises_error(adapter: LetterboxdClient) -> None:
    with pytest.raises(ValueError, match="Invalid ZIP archive"):
        adapter.parse_zip_export(b"this is not a zip file")


def test_parse_html_films_with_ratings(adapter: LetterboxdClient) -> None:
    html = """
    <html>
      <head><title>‎myuser’s films • Letterboxd</title></head>
      <body>
        <ul class="poster-list">
          <li class="griditem">
            <div class="react-component" data-component-class="LazyPoster" data-item-name="Blade Runner 2049 (2017)" data-item-slug="blade-runner-2049">
              <div class="poster"><img alt="Poster for Blade Runner 2049"></div>
            </div>
            <p class="poster-viewingdata"><span class="rating rated-8">★★★★</span></p>
          </li>
          <li class="griditem">
            <div class="react-component" data-component-class="LazyPoster" data-item-name="Dune (2021)" data-item-slug="dune-2021">
            </div>
            <p class="poster-viewingdata"><span class="rating rated-10">★★★★★</span></p>
          </li>
        </ul>
        <div class="paginate-nextprev"><a class="next" href="/myuser/films/page/2/">Older</a></div>
      </body>
    </html>
    """
    items, next_url = adapter.parse_html(html)
    assert len(items) == 2
    assert next_url == "https://letterboxd.com/myuser/films/page/2/"

    assert items[0].title == "Blade Runner 2049"
    assert items[0].release_year == 2017
    assert items[0].letterboxd_uri == "https://letterboxd.com/film/blade-runner-2049/"
    assert items[0].rating == 4.0
    assert items[0].entry_type == LetterboxdItemType.WATCHED

    assert items[1].title == "Dune"
    assert items[1].release_year == 2021
    assert items[1].rating == 5.0


def test_parse_html_watchlist(adapter: LetterboxdClient) -> None:
    html = """
    <html>
      <head><title>‎myuser’s Watchlist • Letterboxd</title></head>
      <body>
        <ul>
          <li class="griditem">
            <div class="react-component" data-component-class="LazyPoster" data-item-name="Past Lives (2023)" data-item-slug="past-lives"></div>
          </li>
        </ul>
      </body>
    </html>
    """
    items, next_url = adapter.parse_html(html)
    assert len(items) == 1
    assert next_url is None
    assert items[0].title == "Past Lives"
    assert items[0].release_year == 2023
    assert items[0].entry_type == LetterboxdItemType.WATCHLIST


def test_parse_html_single_film_page(adapter: LetterboxdClient) -> None:
    html = """
    <html>
      <head>
        <title>ASTRO (2024) directed by Tim Ewalts • Reviews, film + cast • Letterboxd</title>
        <meta property="og:title" content="ASTRO (2024)" />
        <meta property="og:url" content="https://letterboxd.com/film/astro-2024/" />
      </head>
      <body>
        <section id="userpanel" class="actions-panel">
          <input type="radio" value="7" checked="" />
        </section>
      </body>
    </html>
    """
    items, next_url = adapter.parse_html(html)
    assert len(items) == 1
    assert next_url is None
    assert items[0].title == "ASTRO"
    assert items[0].release_year == 2024
    assert items[0].letterboxd_uri == "https://letterboxd.com/film/astro-2024/"
    assert items[0].rating == 3.5  # 7 / 2.0


def test_parse_local_scraping_folder(adapter: LetterboxdClient) -> None:
    from pathlib import Path
    if not Path("for scraping").is_dir():
        pytest.skip("for scraping directory not found")

    items = adapter.parse_local_folder("for scraping")
    assert len(items) == 124
    watched_items = [i for i in items if i.entry_type == LetterboxdItemType.WATCHED]
    watchlist_items = [i for i in items if i.entry_type == LetterboxdItemType.WATCHLIST]
    assert len(watched_items) == 72
    assert len(watchlist_items) == 52
