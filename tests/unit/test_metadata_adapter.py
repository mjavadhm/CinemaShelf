"""Unit tests for MetadataProvidersClient (TMDB + OMDb adapter)."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.adapters.metadata_providers.client import MetadataProvidersClient
from app.core.config import Settings
from app.core.errors import ProviderUnavailableError


@pytest.fixture
def mock_settings() -> Settings:
    """Settings with configured test API keys."""
    return Settings(
        tmdb_api_key="test_tmdb_key",
        omdb_api_key="test_omdb_key",
    )


@pytest.mark.asyncio
async def test_search_movies_success(mock_settings: Settings) -> None:
    """Verify movie search queries TMDB and correctly normalizes results."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "id": 27205,
                "title": "Inception",
                "original_title": "Inception",
                "release_date": "2010-07-16",
                "overview": "A thief who steals corporate secrets...",
                "poster_path": "/inception.jpg",
                "vote_average": 8.4,
            }
        ]
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response

    adapter = MetadataProvidersClient(settings=mock_settings, http_client=mock_client)
    results = await adapter.search("Inception", release_year=2010, work_type="MOVIE")

    assert len(results) == 1
    res = results[0]
    assert res.tmdb_id == 27205
    assert res.title == "Inception"
    assert res.release_year == 2010
    assert res.work_type == "MOVIE"
    assert res.vote_average == 8.4


@pytest.mark.asyncio
async def test_fetch_details_success_with_credits_and_omdb(
    mock_settings: Settings,
) -> None:
    """Verify fetching work details parses top 20 cast, key crew, genres, and OMDb ratings."""
    tmdb_payload: dict[str, Any] = {
        "id": 27205,
        "title": "Inception",
        "original_title": "Inception",
        "original_language": "en",
        "overview": "Cobb steals information from targets...",
        "release_date": "2010-07-15",
        "runtime": 148,
        "status": "Released",
        "poster_path": "/poster.jpg",
        "backdrop_path": "/backdrop.jpg",
        "vote_average": 8.36,
        "vote_count": 34000,
        "external_ids": {"imdb_id": "tt1375666"},
        "genres": [
            {"id": 28, "name": "Action"},
            {"id": 878, "name": "Science Fiction"},
        ],
        "credits": {
            "cast": [
                {
                    "id": 6193,
                    "name": "Leonardo DiCaprio",
                    "order": 0,
                    "character": "Dom Cobb",
                    "credit_id": "c1",
                    "known_for_department": "Acting",
                },
                {
                    "id": 9999,
                    "name": "Background Actor",
                    "order": 25,  # Should be filtered out (> 19)
                    "character": "Extra",
                    "credit_id": "c2",
                },
            ],
            "crew": [
                {
                    "id": 525,
                    "name": "Christopher Nolan",
                    "job": "Director",
                    "department": "Directing",
                    "credit_id": "c3",
                },
                {
                    "id": 947,
                    "name": "Hans Zimmer",
                    "job": "Original Music Composer",
                    "department": "Sound",
                    "credit_id": "c4",
                },
                {
                    "id": 8888,
                    "name": "Catering Manager",
                    "job": "Catering",  # Should be filtered out
                    "department": "Production",
                    "credit_id": "c5",
                },
            ],
        },
    }

    omdb_payload: dict[str, Any] = {
        "Response": "True",
        "imdbRating": "8.8",
        "imdbVotes": "2,400,000",
        "Metascore": "74",
        "Ratings": [{"Source": "Rotten Tomatoes", "Value": "87%"}],
    }

    def side_effect(url: str, params: dict[str, Any]) -> MagicMock:
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        if "themoviedb.org" in url:
            resp.json.return_value = tmdb_payload
        else:
            resp.json.return_value = omdb_payload
        return resp

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = side_effect

    adapter = MetadataProvidersClient(settings=mock_settings, http_client=mock_client)
    details = await adapter.fetch_details(tmdb_id=27205, work_type="MOVIE")

    assert details.title == "Inception"
    assert details.imdb_id == "tt1375666"
    assert details.runtime_minutes == 148
    assert len(details.genres) == 2
    assert details.genres[0].name == "Action"

    # Verify credit filtering
    assert (
        len(details.credits) == 3
    )  # DiCaprio (cast 0), Nolan (Director), Zimmer (Composer)
    jobs = {c.job for c in details.credits}
    assert "Actor" in jobs
    assert "Director" in jobs
    assert "Original Music Composer" in jobs
    assert "Catering" not in jobs

    # Verify OMDb ratings enrichment
    assert details.imdb_rating == 8.8
    assert details.imdb_votes == 2400000
    assert details.metascore == 74
    assert details.rotten_tomatoes_score == 87


@pytest.mark.asyncio
async def test_missing_api_key_raises_provider_unavailable() -> None:
    """Verify unconfigured API key raises ProviderUnavailableError."""
    settings = Settings(tmdb_api_key="")
    adapter = MetadataProvidersClient(settings=settings)

    with pytest.raises(
        ProviderUnavailableError, match="TMDB API key is not configured"
    ):
        await adapter.search("The Dark Knight")
