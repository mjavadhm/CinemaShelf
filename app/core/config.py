"""Centralized application settings management."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8080
    log_level: str = "INFO"

    data_dir: Path = Path("./data")
    database_url: str = "sqlite:///./data/cinemashelf.db"
    poster_cache_dir: Path = Path("./data/posters")
    log_dir: Path = Path("./data/logs")
    zarfilm_profile_dir: Path = Path("./data/profiles/zarfilm")
    letterboxd_profile_dir: Path = Path("./data/profiles/letterboxd")

    default_player: str = "mpv"
    aria2_rpc_url: str = "http://127.0.0.1:6800/jsonrpc"
    aria2_rpc_secret: str = ""
    omdb_api_key: str = ""
    tmdb_api_key: str = ""

    llm_enabled: bool = False
    llm_provider: str = ""
    llm_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def ensure_directories(self) -> None:
        """Create local runtime directories if they do not exist."""
        for path in (
            self.data_dir,
            self.poster_cache_dir,
            self.log_dir,
            self.zarfilm_profile_dir,
            self.letterboxd_profile_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
