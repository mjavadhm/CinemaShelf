"""Smoke test for basic application setup."""

from app.core.config import Settings


def test_default_settings_localhost() -> None:
    """Verify that default binding remains strictly localhost."""
    settings = Settings()
    assert settings.app_host == "127.0.0.1"
    assert settings.llm_enabled is False


def test_startup_app_loads_all_mappers() -> None:
    """Verify that startup_app registers and configures all SQLAlchemy mappers cleanly."""
    from app.bootstrap import load_all_models

    # Must execute configure_mappers without raising InvalidRequestError
    load_all_models()
