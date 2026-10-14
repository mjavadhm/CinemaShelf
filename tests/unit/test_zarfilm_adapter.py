"""Unit tests for the Zarfilm browser scraper adapter and scoring logic."""

from app.adapters.zarfilm.client import (
    ZarfilmBrowserClient,
    ZarfilmMovieCard,
    ZarfilmReleaseCandidate,
    detect_x265,
    parse_resolution,
    parse_size_bytes,
)


def test_parse_size_bytes() -> None:
    assert parse_size_bytes("2.4 GB") == int(2.4 * 1024**3)
    assert parse_size_bytes("850 MB") == 850 * 1024**2
    assert parse_size_bytes("1.5 GiB") == int(1.5 * 1024**3)
    assert parse_size_bytes("500 KB") == 500 * 1024
    assert parse_size_bytes(None) is None
    assert parse_size_bytes("invalid size string") is None


def test_parse_resolution() -> None:
    assert parse_resolution("Inception 2010 1080p WEB-DL") == "1080p"
    assert parse_resolution("Movie 4K UHD Remux") == "2160p"
    assert parse_resolution("Movie 2160p HEVC") == "2160p"
    assert parse_resolution("Movie 720p HDTV") == "720p"
    assert parse_resolution("Movie 480p SD") == "480p"
    assert parse_resolution("Unknown Quality") is None


def test_detect_x265() -> None:
    assert detect_x265("1080p WEB-DL 10bit x265 PSA") is True
    assert detect_x265("720p HEVC AAC") is True
    assert detect_x265("1080p Bluray x264 YIFY") is False
    assert detect_x265(None) is False


def test_match_card() -> None:
    client = ZarfilmBrowserClient()
    cards = [
        ZarfilmMovieCard(
            title="Inception",
            year="2010",
            href="https://zarfilm.com/movies/inception-2010/",
        ),
        ZarfilmMovieCard(
            title="Inception: The Cobol Job",
            year="2010",
            href="https://zarfilm.com/movies/inception-cobol-job/",
        ),
        ZarfilmMovieCard(
            title="The Dark Knight",
            year="2008",
            href="https://zarfilm.com/movies/dark-knight/",
        ),
    ]

    # Exact title + exact year
    matched = client.match_card(cards, "Inception", "2010")
    assert matched is not None
    assert matched.href == "https://zarfilm.com/movies/inception-2010/"

    # Substring match with year
    matched = client.match_card(cards, "The Cobol Job", "2010")
    assert matched is not None
    assert matched.href == "https://zarfilm.com/movies/inception-cobol-job/"

    # Single card fallback
    matched = client.match_card([cards[0]], "Totally Different Title", 1999)
    assert matched == cards[0]

    # No match in multi-card list
    matched = client.match_card(cards, "Interstellar", 2014)
    assert matched is None


def test_score_and_pick_best_release() -> None:
    client = ZarfilmBrowserClient()
    rel1 = ZarfilmReleaseCandidate(
        download_url="https://dl.zarfilm.com/1080p_softsub_x265.mkv",
        quality_label="1080p WEB-DL x265 SoftSub",
        resolution="1080p",
        is_dubbed=False,
        has_persian_sub=True,
        is_x265=True,
    )
    rel2 = ZarfilmReleaseCandidate(
        download_url="https://dl.zarfilm.com/720p_softsub_x264.mkv",
        quality_label="720p WEB-DL x264 SoftSub",
        resolution="720p",
        is_dubbed=False,
        has_persian_sub=True,
        is_x265=False,
    )
    rel3 = ZarfilmReleaseCandidate(
        download_url="https://dl.zarfilm.com/1080p_dubbed.mkv",
        quality_label="1080p Dubbed",
        resolution="1080p",
        is_dubbed=True,
        has_persian_sub=False,
        is_x265=False,
    )

    score1 = client.score_candidate(rel1, preferred_quality="1080p", prefer_x265=True)
    score2 = client.score_candidate(rel2, preferred_quality="1080p", prefer_x265=True)
    score3 = client.score_candidate(rel3, preferred_quality="1080p", prefer_x265=True)

    assert score1 > score2
    assert score1 > score3

    best = client.pick_best_release(
        [rel1, rel2, rel3], preferred_quality="1080p", prefer_x265=True
    )
    assert best == rel1
