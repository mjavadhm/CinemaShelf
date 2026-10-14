# Metadata Module (`app/modules/metadata`)

## Data Ownership
- **Owned Entities:** Public movie metadata fields and local poster cache files

## Responsibilities
Fetches and caches public movie details and posters for offline browsing.

## Architectural Rules
- Do not call `session.commit()` inside `repository.py`; transaction boundaries belong in `service.py`.
- Never leak ORM models directly from `router.py`; always map to Pydantic schemas in `schemas.py`.
- See `docs/03-architecture.md` and `docs/04-data-model.md` for full specifications.
