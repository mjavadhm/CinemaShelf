# Sources Module (`app/modules/sources`)

## Data Ownership
- **Owned Entities:** `Source`

## Responsibilities
Owns local folder/drive roots, connection availability detection, and directory scanning orchestration.

## Architectural Rules
- Do not call `session.commit()` inside `repository.py`; transaction boundaries belong in `service.py`.
- Never leak ORM models directly from `router.py`; always map to Pydantic schemas in `schemas.py`.
- See `docs/03-architecture.md` and `docs/04-data-model.md` for full specifications.
