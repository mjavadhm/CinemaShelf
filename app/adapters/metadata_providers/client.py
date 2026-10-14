"""Adapter implementation: External movie and TV metadata provider adapter (TMDB + OMDb)."""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import ProviderUnavailableError

logger = logging.getLogger(__name__)

KEY_CREW_JOBS: set[str] = {
    "Director",
    "Writer",
    "Screenplay",
    "Story",
    "Original Music Composer",
    "Director of Photography",
    "Editor",
}


@dataclass
class ExternalSearchResult:
    """External metadata search result candidate."""

    tmdb_id: int
    title: str
    work_type: str  # "MOVIE" | "SHOW"
    original_title: str | None = None
    release_year: int | None = None
    overview: str | None = None
    poster_path: str | None = None
    vote_average: float | None = None


@dataclass
class ExternalCredit:
    """Cast or crew credit parsed from TMDB payload."""

    tmdb_person_id: int
    name: str
    credit_type: str  # "CAST" | "CREW"
    department: str
    job: str
    character_name: str | None = None
    billing_order: int | None = None
    tmdb_credit_id: str | None = None
    profile_path: str | None = None
    original_name: str | None = None
    known_for_department: str | None = None
    imdb_person_id: str | None = None


@dataclass
class ExternalEpisode:
    """Single TV episode parsed from TMDB."""

    season_number: int
    episode_number: int
    tmdb_episode_id: int | None = None
    title: str | None = None
    overview: str | None = None
    air_date: date | None = None
    runtime_minutes: int | None = None
    still_path: str | None = None
    tmdb_rating: float | None = None


@dataclass
class ExternalSeason:
    """TV show season parsed from TMDB."""

    season_number: int
    tmdb_season_id: int | None = None
    title: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    air_date: date | None = None
    episode_count: int | None = None
    episodes: list[ExternalEpisode] = field(default_factory=list)


@dataclass
class ExternalGenre:
    """Genre parsed from TMDB."""

    tmdb_genre_id: int
    name: str
    persian_name: str | None = None


@dataclass
class ExternalWorkDetails:
    """Full work metadata payload combined from TMDB and OMDb."""

    tmdb_id: int
    work_type: str  # "MOVIE" | "SHOW"
    title: str
    imdb_id: str | None = None
    original_title: str | None = None
    persian_title: str | None = None
    original_language: str | None = None
    overview: str | None = None
    release_date: date | None = None
    release_year: int | None = None
    runtime_minutes: int | None = None
    status: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    tmdb_rating: float | None = None
    tmdb_vote_count: int | None = None
    imdb_rating: float | None = None
    imdb_votes: int | None = None
    rotten_tomatoes_score: int | None = None
    metascore: int | None = None
    genres: list[ExternalGenre] = field(default_factory=list)
    credits: list[ExternalCredit] = field(default_factory=list)
    seasons: list[ExternalSeason] = field(default_factory=list)


class MetadataProvidersPort(Protocol):
    """Protocol contract for metadata provider operations."""

    async def search(
        self,
        query: str,
        release_year: int | None = None,
        work_type: str = "MOVIE",
    ) -> list[ExternalSearchResult]:
        """Search for movies or TV series matching query."""
        ...

    async def fetch_details(
        self,
        tmdb_id: int,
        work_type: str = "MOVIE",
    ) -> ExternalWorkDetails:
        """Fetch complete work details including credits, genres, and external ratings."""
        ...

    async def fetch_omdb_ratings(self, imdb_id: str) -> dict[str, Any]:
        """Fetch supplementary external ratings from OMDb."""
        ...


class MetadataProvidersClient:
    """Concrete HTTP adapter for TMDB and OMDb APIs."""

    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    OMDB_BASE_URL: str = "http://www.omdbapi.com"

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http_client = http_client

    def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is not None:
            return self._http_client
        import os

        for key in (
            "ALL_PROXY",
            "all_proxy",
            "HTTP_PROXY",
            "http_proxy",
            "HTTPS_PROXY",
            "https_proxy",
        ):
            val = os.environ.get(key)
            if val and val.startswith("socks://"):
                os.environ[key] = "socks5://" + val[len("socks://") :]
        return httpx.AsyncClient(timeout=15.0)

    def _parse_date(self, date_str: str | None) -> date | None:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None

    async def search(
        self,
        query: str,
        release_year: int | None = None,
        work_type: str = "MOVIE",
    ) -> list[ExternalSearchResult]:
        """Search TMDB for movies or TV shows."""
        if not self.settings.tmdb_api_key:
            raise ProviderUnavailableError("TMDB API key is not configured in settings")

        endpoint = "/search/movie" if work_type == "MOVIE" else "/search/tv"
        params: dict[str, Any] = {
            "api_key": self.settings.tmdb_api_key,
            "query": query,
            "include_adult": "false",
        }
        if release_year:
            if work_type == "MOVIE":
                params["year"] = release_year
            else:
                params["first_air_date_year"] = release_year

        client = self._get_client()
        should_close = self._http_client is None
        try:
            response = await client.get(
                f"{self.TMDB_BASE_URL}{endpoint}",
                params=params,
            )
            if response.status_code != 200:
                raise ProviderUnavailableError(
                    f"TMDB search failed with status {response.status_code}: {response.text}"
                )
            data = response.json()
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(
                f"Network error communicating with TMDB: {exc}"
            ) from exc
        finally:
            if should_close:
                await client.aclose()

        results: list[ExternalSearchResult] = []
        for item in data.get("results", []):
            tmdb_id = item.get("id")
            if not tmdb_id:
                continue

            if work_type == "MOVIE":
                title = item.get("title") or item.get("original_title") or "Unknown"
                orig_title = item.get("original_title")
                rel_date = item.get("release_date") or ""
            else:
                title = item.get("name") or item.get("original_name") or "Unknown"
                orig_title = item.get("original_name")
                rel_date = item.get("first_air_date") or ""

            year = (
                int(rel_date[:4])
                if len(rel_date) >= 4 and rel_date[:4].isdigit()
                else None
            )

            results.append(
                ExternalSearchResult(
                    tmdb_id=tmdb_id,
                    title=title,
                    work_type=work_type,
                    original_title=orig_title,
                    release_year=year,
                    overview=item.get("overview"),
                    poster_path=item.get("poster_path"),
                    vote_average=item.get("vote_average"),
                )
            )

        return results

    async def fetch_omdb_ratings(self, imdb_id: str) -> dict[str, Any]:
        """Fetch rating data from OMDb API."""
        if not self.settings.omdb_api_key or not imdb_id:
            return {}

        params = {
            "apikey": self.settings.omdb_api_key,
            "i": imdb_id,
        }
        client = self._get_client()
        should_close = self._http_client is None
        try:
            response = await client.get(self.OMDB_BASE_URL, params=params)
            if response.status_code != 200:
                return {}
            data = response.json()
            if data.get("Response") != "True":
                return {}

            # Parse IMDb rating
            imdb_rating = None
            try:
                imdb_rating = float(data.get("imdbRating", ""))
            except (ValueError, TypeError):
                pass

            # Parse IMDb votes (e.g., "1,234,567")
            imdb_votes = None
            votes_raw = data.get("imdbVotes", "").replace(",", "")
            if votes_raw.isdigit():
                imdb_votes = int(votes_raw)

            # Parse Metascore
            metascore = None
            meta_raw = data.get("Metascore", "")
            if meta_raw.isdigit():
                metascore = int(meta_raw)

            # Parse Rotten Tomatoes score from Ratings array
            rotten_tomatoes = None
            for r in data.get("Ratings", []):
                if r.get("Source") == "Rotten Tomatoes":
                    val_str = r.get("Value", "").rstrip("%")
                    if val_str.isdigit():
                        rotten_tomatoes = int(val_str)
                    break

            return {
                "imdb_rating": imdb_rating,
                "imdb_votes": imdb_votes,
                "metascore": metascore,
                "rotten_tomatoes_score": rotten_tomatoes,
            }
        except (httpx.RequestError, ValueError, KeyError) as exc:
            logger.warning("Failed to fetch OMDb ratings for %s: %s", imdb_id, exc)
            return {}
        finally:
            if should_close:
                await client.aclose()

    async def fetch_details(
        self,
        tmdb_id: int,
        work_type: str = "MOVIE",
    ) -> ExternalWorkDetails:
        """Fetch full work details from TMDB and enrich with OMDb ratings."""
        if not self.settings.tmdb_api_key:
            raise ProviderUnavailableError("TMDB API key is not configured in settings")

        endpoint = f"/movie/{tmdb_id}" if work_type == "MOVIE" else f"/tv/{tmdb_id}"
        params = {
            "api_key": self.settings.tmdb_api_key,
            "append_to_response": "credits,external_ids",
        }

        client = self._get_client()
        should_close = self._http_client is None
        try:
            response = await client.get(
                f"{self.TMDB_BASE_URL}{endpoint}",
                params=params,
            )
            if response.status_code == 404:
                raise ProviderUnavailableError(f"TMDB work {tmdb_id} not found")
            if response.status_code != 200:
                raise ProviderUnavailableError(
                    f"TMDB details failed with status {response.status_code}: {response.text}"
                )
            data = response.json()
        except httpx.RequestError as exc:
            raise ProviderUnavailableError(
                f"Network error communicating with TMDB: {exc}"
            ) from exc
        finally:
            if should_close:
                await client.aclose()

        # Parse basic fields
        if work_type == "MOVIE":
            title = data.get("title") or data.get("original_title") or "Unknown"
            original_title = data.get("original_title")
            rel_date_str = data.get("release_date")
            runtime = data.get("runtime")
        else:
            title = data.get("name") or data.get("original_name") or "Unknown"
            original_title = data.get("original_name")
            rel_date_str = data.get("first_air_date")
            # For shows, episode_run_time may be an array
            run_times: list[int] = data.get("episode_run_time") or []
            runtime = run_times[0] if run_times else None

        rel_date = self._parse_date(rel_date_str)
        rel_year = rel_date.year if rel_date else None

        # External IDs (IMDb)
        ext_ids = data.get("external_ids") or {}
        imdb_id = ext_ids.get("imdb_id") or data.get("imdb_id")

        # Genres
        genres: list[ExternalGenre] = [
            ExternalGenre(tmdb_genre_id=g["id"], name=g["name"])
            for g in data.get("genres", [])
            if "id" in g and "name" in g
        ]

        # Credits: Cast (Top 20 by order) & Key Crew
        credits_data = data.get("credits") or {}
        parsed_credits: list[ExternalCredit] = []

        # 1. Cast
        for c in credits_data.get("cast", []):
            order = c.get("order", 999)
            if order < 20 and c.get("id"):
                parsed_credits.append(
                    ExternalCredit(
                        tmdb_person_id=c["id"],
                        name=c.get("name") or "Unknown",
                        original_name=c.get("original_name"),
                        known_for_department=c.get("known_for_department") or "Acting",
                        profile_path=c.get("profile_path"),
                        credit_type="CAST",
                        department="Acting",
                        job="Actor",
                        character_name=c.get("character"),
                        billing_order=order,
                        tmdb_credit_id=c.get("credit_id"),
                    )
                )

        # 2. Crew (Filtered to key roles)
        for cr in credits_data.get("crew", []):
            job = cr.get("job", "")
            if job in KEY_CREW_JOBS and cr.get("id"):
                parsed_credits.append(
                    ExternalCredit(
                        tmdb_person_id=cr["id"],
                        name=cr.get("name") or "Unknown",
                        original_name=cr.get("original_name"),
                        known_for_department=cr.get("known_for_department"),
                        profile_path=cr.get("profile_path"),
                        credit_type="CREW",
                        department=cr.get("department") or "Directing",
                        job=job,
                        tmdb_credit_id=cr.get("credit_id"),
                    )
                )

        # Seasons & Episodes (for SHOW)
        seasons: list[ExternalSeason] = []
        if work_type == "SHOW":
            for s in data.get("seasons", []):
                s_num = s.get("season_number", 0)
                seasons.append(
                    ExternalSeason(
                        season_number=s_num,
                        tmdb_season_id=s.get("id"),
                        title=s.get("name"),
                        overview=s.get("overview"),
                        poster_path=s.get("poster_path"),
                        air_date=self._parse_date(s.get("air_date")),
                        episode_count=s.get("episode_count"),
                    )
                )

        # External ratings from OMDb
        omdb_ratings: dict[str, Any] = {}
        if imdb_id:
            omdb_ratings = await self.fetch_omdb_ratings(imdb_id)

        return ExternalWorkDetails(
            tmdb_id=tmdb_id,
            work_type=work_type,
            title=title,
            imdb_id=imdb_id,
            original_title=original_title,
            original_language=data.get("original_language"),
            overview=data.get("overview"),
            release_date=rel_date,
            release_year=rel_year,
            runtime_minutes=runtime,
            status=data.get("status"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            tmdb_rating=data.get("vote_average"),
            tmdb_vote_count=data.get("vote_count"),
            imdb_rating=omdb_ratings.get("imdb_rating"),
            imdb_votes=omdb_ratings.get("imdb_votes"),
            rotten_tomatoes_score=omdb_ratings.get("rotten_tomatoes_score"),
            metascore=omdb_ratings.get("metascore"),
            genres=genres,
            credits=parsed_credits,
            seasons=seasons,
        )
