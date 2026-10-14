# CinemaShelf — AI Coding Agent Guidelines (`AGENTS.md`)

Welcome! This repository is structured as a **Modular Monolith** in Python (FastAPI + SQLite/SQLAlchemy) following the architectural blueprint in `docs/`.

---

## 1. Golden Rules & Architectural Boundaries

1. **Read Docs Before Writing Logic:**
   - Product scope & invariants: `docs/01-product-and-scope.md` & `docs/decisions/0002-domain-invariants.md`
   - Architecture & layering: `docs/03-architecture.md` & `docs/decisions/0001-architecture.md`
   - Conceptual data model: `docs/04-data-model.md`
   - Background jobs & workflows: `docs/05-workflows-and-jobs.md`
   - Logging & error contracts: `docs/06-logging-and-errors.md`
   - Coding standards: `docs/07-development-rules.md`
   - Step-by-step feature guide: `docs/08-adding-a-feature.md`
   - Execution roadmap: `docs/09-roadmap-and-acceptance.md`

2. **Legacy Code (`legacy/`):**
   - The `legacy/` folder (`legacy/cinemashelf` and `legacy/zarfilm-downloader`) is **ignored by Git** (`.gitignore`) and exists **ONLY as a local reference** during initial porting (see `docs/10-legacy-code-map.md`).
   - **NEVER** import anything from `legacy/` into `app/` or `tests/`.
   - **NEVER** run `legacy/cinemashelf/mover.py` on real directories.
   - Once logic is cleanly adapted into `app/adapters/` or `app/modules/`, `legacy/` will be deleted.

3. **Strict Layer Responsibilities:**
   - `router.py` (HTTP Layer): Validates HTTP inputs, injects dependencies, maps application errors to HTTP responses. **No SQL queries or domain rules here.**
   - `service.py` (Application Layer): Owns use-cases, transaction boundaries, and domain invariants. **Must not depend on FastAPI `Request`/`Response` objects.**
   - `repository.py` (Persistence Layer): Executes meaningful queries on SQLite via SQLAlchemy Session. **Never call `session.commit()` inside a repository** (commits belong to the Service layer).
   - `schemas.py` (Contract Layer): Pydantic models for API/DTO boundaries. **Never return raw SQLAlchemy ORM objects directly from API endpoints.**
   - `app/adapters/` (External Boundaries): Encapsulates Aria2 RPC, Zarfilm browser scraping (`DrissionPage`), Letterboxd scraping/CSV, OMDb/TMDB providers, and OS file/player execution.

4. **Core Domain Invariants:**
   - `Movie` (the film identity) is distinct from `MediaFile` (a physical file on a `Source`).
   - Multiple files/qualities of the same film map to **one** `Movie` card.
   - `PersonalState` (watched status, personal rating, notes) and `WatchEvent` belong to `Movie`, **not** `MediaFile`.
   - Unplugged external drives (`Source` offline) must **never** delete or mark `MediaFile` records as missing.
   - Playing a file in an external player does **not** automatically mark the `Movie` as watched.
   - No physical file move or deletion may happen without explicit user selection and confirmation.

---

## 2. Project Directory Map

```text
app/
  main.py                  # FastAPI app factory & lifespan
  bootstrap.py             # Dependency wiring & startup/shutdown hooks
  core/
    config.py              # Central Pydantic Settings (.env)
    database.py            # SQLAlchemy engine & Session lifecycle
    errors.py              # Base ApplicationError & error codes
    logging.py             # Central structured logging setup
  modules/
    library/               # Movie identity, ExternalIdentity, MediaFile catalog
    sources/               # Storage roots, drive availability, scanning logic
    personal/              # PersonalState, WatchEvent, manual watch/rating
    metadata/              # Public metadata & local poster caching
    integrations/          # Letterboxd sync & CSV import coordination
    downloads/             # Unified JIT/nightly download queue & LibraryImport
    playback/              # Safe OS media player launching & folder opening
  adapters/
    aria2/                 # Aria2 JSON-RPC client adapter
    zarfilm/               # Zarfilm browser scraper adapter
    letterboxd/           # Letterboxd browser/CSV parser adapter
    metadata_providers/    # OMDb / TMDB API client adapter
  jobs/
    runner.py              # Controlled background job runner & state transitions
    handlers.py            # Job execution handlers (scan, sync, download)
migrations/                # Alembic database migrations
tests/
  unit/                    # Pure domain & service logic tests
  integration/             # SQLite repository & FastAPI endpoint tests
  architecture/            # Layer boundary & import rule verification
```

---

## 3. How to Add or Modify a Feature

Always follow `docs/08-adding-a-feature.md` and verify against `templates/review-checklist.md`:
1. Check `docs/09-roadmap-and-acceptance.md` for the current milestone scope.
2. Define/update models in the owning module's `models.py` and generate an Alembic migration if needed.
3. Define input/output DTOs in `schemas.py`.
4. Implement persistence methods in `repository.py` (no internal commits).
5. Implement use-case orchestration and transaction commit/rollback in `service.py`.
6. Expose HTTP endpoints in `router.py` and register in `app/main.py`.
7. Write unit and integration tests in `tests/` (never require live internet or real user media drives in tests).
8. Document implementation plans and walkthroughs in `docs/progress/`.

---

## 4. Git Commits & Progress Documentation Rules

1. **Frequent & Atomic Commits**:
   - Commit code changes promptly at the end of each phase or clear vertical slice so commits remain manageable and cleanly isolated. Avoid massive multi-feature commits.

2. **Commit Message Hygiene (Strictly No AI Mentions)**:
   - Use standard Conventional Commits format (`feat: ...`, `fix: ...`, `test: ...`, `docs: ...`, `refactor: ...`, `chore: ...`).
   - **NEVER** include the name of any AI assistant, model, or tool in commit titles, descriptions, or code comments (e.g., never write "commented by claude", "generated by gemini", "audited by antigravity", "Co-authored-by: ...", etc.). All commit messages and comments must read as clean, standard human engineering.

3. **Progress Documentation in `docs/progress/`**:
   - Maintain full documentation for each milestone/phase under `docs/progress/` (e.g., `phase-1-plan.md`, `phase-1-walkthrough.md`, `phase-2-plan.md`, `phase-2-walkthrough.md`).
   - Include component breakdowns, data flows, endpoint contracts, and test verification results so developers exploring the repository can readily understand and extend any part of the system.
