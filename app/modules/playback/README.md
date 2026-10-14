# Playback Module (`app/modules/playback`)

## Data Ownership
- **Owned Entities:** Stateless OS player execution

## Responsibilities
Safely launches configured local media player (e.g., mpv, VLC) or opens containing folder without marking movie watched.

## Architectural Rules
- Do not call `session.commit()` inside `repository.py`; transaction boundaries belong in `service.py`.
- Never leak ORM models directly from `router.py`; always map to Pydantic schemas in `schemas.py`.
- See `docs/03-architecture.md` and `docs/04-data-model.md` for full specifications.
