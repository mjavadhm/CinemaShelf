# Phase 5 Walkthrough: Letterboxd File Import & Sync

This walkthrough documents the design, implementation, and verification of **Phase 5** of CinemaShelf, enabling offline-friendly, high-fidelity import and synchronization of Letterboxd archives from export ZIP packages and CSV files.

---

## 1. Overview & Architecture

Phase 5 connects external cinephile archives from Letterboxd directly into CinemaShelf's local catalog and personal state tracker:
- **Multi-Format Ingestion**: Ingests both full Letterboxd data export ZIP packages (`watchlist.csv`, `watched.csv`, `ratings.csv`, `diary.csv`, `lists/*.csv`) and standalone CSV uploads (both official Letterboxd exports and legacy simplified `Name,Year` format).
- **Identity & Catalog Resolution**: Discovers internal `MediaWork` records via cached `ExternalItemMapping`, normalized title/year searches, or automatic fallback ingestion from TMDB.
- **Personal State & JIT Download Pipeline**: Watchlist imports automatically mark `in_watchlist=True`, update `watch_status=WATCHLIST`, and register a wanted `LibraryItem` with `status=WANTED` so discovered movies enter the download pipeline.
- **Conflict Policies & Invariant Protection**: Respects `ConflictPolicy.PRESERVE_LOCAL` by default (manual user ratings and notes are never overwritten without explicit user instruction). Partial or failed sync runs never delete or mark missing existing personal state or library items.

```
┌────────────────────────────────────────────────────────┐
│           FastAPI App /integrations Router             │
│   POST /integrations/letterboxd/import-file            │
│   GET  /integrations/sync-runs                         │
│   GET  /integrations/sync-runs/{run_id}                │
│   GET  /integrations/mappings                          │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                  IntegrationsService                   │
│  - import_file (.zip or .csv)                          │
│  - _resolve_media_work (cache -> DB -> TMDB ingest)    │
│  - _apply_item (watchlist, ratings, diary, shelves)    │
│  - transaction boundary management & audit logging     │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│       LetterboxdClient       │ │    IntegrationsRepository    │
│  - parse_csv (flexible keys) │ │  - create/finish sync_run    │
│  - parse_zip_export (memory) │ │  - external mapping CRUD     │
│  - BOM & header normalization│ │  - title/year work lookup    │
└──────────────────────────────┘ └──────────────┬───────────────┘
                                                │
                                                ▼
┌────────────────────────────────────────────────────────┐
│               SQLite (SQLAlchemy Models)               │
│  - integration_sync_runs, external_item_mappings       │
│  - media_works, library_items                          │
│  - personal_records, watch_diary_logs, custom_shelves  │
└────────────────────────────────────────────────────────┘
```

---

## 2. Component Breakdown

### 2.1. Adapter Layer: `app/adapters/letterboxd/`
- `LetterboxdClient` implementing `LetterboxdPort`.
- Flexible header detection tolerant to UTF-8 BOM, case differences, and alternative column names (`Name`/`Title`/`Film`, `Year`, `Letterboxd URI`/`URL`, `Rating`, `Watched Date`/`Date`, `Rewatch`, `Tags`, `Position`).
- In-memory ZIP archive streaming via `zipfile.ZipFile`, extracting structured `LetterboxdExportArchive` collections (`watchlist`, `watched`, `ratings`, `diary`, `lists`).

### 2.2. Contract Layer: `app/modules/integrations/schemas.py`
- `ConflictPolicy`: `PRESERVE_LOCAL` (default) vs `OVERWRITE_LOCAL`.
- `RatingScaleMode`: `RAW` (preserves 0.5 - 5.0 float) vs `TEN_POINT` (multiplies by 2 for a 1.0 - 10.0 scale).
- `SyncRunResponse`: Exposes full audit state, counts, duration, and error details.
- `ExternalItemMappingResponse`: Exposes external URI to `MediaWork` ID mappings.
- `ImportSummaryResponse`: Returns high-level batch counts broken down by category.

### 2.3. Persistence Layer: `app/modules/integrations/repository.py`
- Strictly persistence queries, with **no internal commits**.
- Creates and updates `IntegrationSyncRun` records.
- Reads and persists `ExternalItemMapping` records.
- Fast case-insensitive title and release year matching on `MediaWork`.

### 2.4. Service Layer: `app/modules/integrations/service.py`
- Manages transaction boundaries: commits the initial sync run, flushes per-item updates, and commits the finished run with metrics.
- Idempotent processing:
  - Diary entries are deduplicated by `(work_id, watched_date)`.
  - Custom list items are deduplicated by `(shelf_id, work_id)`.
  - Watchlist items ensure `LibraryItem` exists with status `WANTED`.
- Error isolation: Individual unmatched films or parsing errors are captured in `error_details` without rolling back the entire batch, marking the run status as `PARTIAL`.

---

## 3. API Endpoints Table

| Method | Endpoint | Description | Status Code |
|---|---|---|---|
| `POST` | `/integrations/letterboxd/import-file` | Ingest multipart CSV or ZIP archive export | `200 OK` |
| `GET` | `/integrations/sync-runs` | Query past sync runs with pagination & filters | `200 OK` |
| `GET` | `/integrations/sync-runs/{run_id}` | Retrieve single sync run audit report | `200 OK` |
| `GET` | `/integrations/mappings` | List external identifier mappings | `200 OK` |

---

## 4. Verification & Quality Gates

### 4.1. Automated Test Results
```text
======================== 92 passed, 1 warning in 4.31s =========================
- tests/unit/test_letterboxd_adapter.py: 9 passed
- tests/unit/test_integrations_service.py: 7 passed
- tests/integration/test_api_phase5.py: 4 passed
- tests/architecture/test_no_legacy_imports.py: 1 passed
- All existing Phase 1, Phase 2, Phase 3, Phase 4 tests: 71 passed
```

### 4.2. Static Analysis & Linting
- `ruff check .` -> **All checks passed!**
- `ruff format --check .` -> **132 files left unchanged (clean format).**
- `mypy app tests` -> **Success: no issues found in 91 source files.**
- `test_no_legacy_imports.py` -> **100% clean isolation; 0 imports from `legacy/`.**

### 4.3. Real-World Smoke Testing
- Ran real-world smoke test verifying:
  - SQLite database migration (`cinemashelf.db`) at head.
  - Full application startup and shutdown lifecycle (`startup_app(settings)` and `shutdown_app()`).
  - End-to-end multipart upload of sample Letterboxd watchlist to real `/integrations/letterboxd/import-file` endpoint.
  - Verified `IntegrationSyncRun` audit logging and `ExternalItemMapping` persistence on disk.
