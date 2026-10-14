# Integrations Module (`app/modules/integrations`)

## Data Ownership
- **Owned Entities:** `SyncRun`

## Responsibilities
Coordinates Letterboxd browser sync and CSV import workflows without overwriting local manual edits silently.

## Architectural Rules
- Do not call `session.commit()` inside `repository.py`; transaction boundaries belong in `service.py`.
- Never leak ORM models directly from `router.py`; always map to Pydantic schemas in `schemas.py`.
- See `docs/03-architecture.md` and `docs/04-data-model.md` for full specifications.
