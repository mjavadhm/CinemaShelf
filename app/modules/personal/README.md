# Personal Module (`app/modules/personal`)

## Data Ownership
- **Owned Entities:** `PersonalState`, `WatchEvent`

## Responsibilities
Owns user watch status, personal ratings, personal notes, and watch history events tied to `Movie`.

## Architectural Rules
- Do not call `session.commit()` inside `repository.py`; transaction boundaries belong in `service.py`.
- Never leak ORM models directly from `router.py`; always map to Pydantic schemas in `schemas.py`.
- See `docs/03-architecture.md` and `docs/04-data-model.md` for full specifications.
