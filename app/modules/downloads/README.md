# Downloads Module (`app/modules/downloads`)

## Data Ownership
- **Owned Entities:** `Download`, `LibraryImport`

## Responsibilities
Manages unified immediate/nightly download queue, JIT link resolution, Aria2 reconciliation, and library import.

## Architectural Rules
- Do not call `session.commit()` inside `repository.py`; transaction boundaries belong in `service.py`.
- Never leak ORM models directly from `router.py`; always map to Pydantic schemas in `schemas.py`.
- See `docs/03-architecture.md` and `docs/04-data-model.md` for full specifications.
