# Library Module (`app/modules/library`)

## Data Ownership
- **Owned Entities:** `Movie`, `ExternalIdentity`, `MediaFile`

## Responsibilities
Owns core film identity, external IDs (IMDb, TMDB, Letterboxd), and physical file catalog entries.

## Architectural Rules
- Do not call `session.commit()` inside `repository.py`; transaction boundaries belong in `service.py`.
- Never leak ORM models directly from `router.py`; always map to Pydantic schemas in `schemas.py`.
- See `docs/03-architecture.md` and `docs/04-data-model.md` for full specifications.
