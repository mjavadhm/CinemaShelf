# Phase 6 Walkthrough: Multi-Library Management, Filesystem Scanner, Virtual Categorizer & LLM Multi-Model Router

This walkthrough documents the design, implementation, and verification of **Phase 6** of CinemaShelf, transforming the platform into a true multi-library media management system with automated server-side filesystem scanning, directory browsing, virtual shortcut categorization, and an intelligent LLM multi-model router with token cost tracking.

---

## 1. Overview & Architecture

Phase 6 implements the capabilities previously scattered across standalone scripts and tools into a cohesive, modular backend architecture and interactive frontend:
- **True Multi-Library Architecture**: Users can define multiple libraries (e.g. Movies, Documentaries, Anime, Criterion Collection) with individual root storage folders across local drives or external media volumes.
- **Recursive Filesystem Scanner & Parser**: Scans folders on disk, detects video files and subtitle streams, parses release titles, release years, and video codecs, and creates catalog items and media files without altering original disk structures.
- **Interactive Server Folder Browser**: Exposes secure directory browsing (`GET /api/library/directories/browse`), allowing users to navigate and pick filesystem paths directly from modal dialogs in the web UI.
- **Virtual Shortcut Categorizer**: Non-destructive categorization creating symlinks (Linux/macOS) or `.lnk` shortcuts (Windows) by Director (ranked), Rating bracket, and Decade into a dedicated directory without touching original media.
- **LLM Multi-Model Router & Cost Tracking**: Provider-agnostic failover router supporting OpenRouter, OpenAI, DeepSeek, and local Ollama instances. Dynamically fails over according to priority order, tracks exact prompt and completion token usage, calculates USD cost, and exposes verification agents for entity resolution and quality picking.

```
┌────────────────────────────────────────────────────────┐
│                   FastAPI Application                  │
│   /api/library: /libraries, /roots, /scan, /stats      │
│   /api/llm:     /providers, /models, /usage, /test     │
│   /api/sources: /releases (with LLM callbacks)         │
└──────────────────────────┬─────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        ▼                                     ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│        LibraryService        │ │          LLMService          │
│  - Multi-Library & Roots     │ │  - Priority failover loop    │
│  - Scanner & Metadata parser │ │  - Exact token & USD cost    │
│  - Stats & Virtual shortcuts │ │  - Entity & Quality agents   │
└──────────────┬───────────────┘ └──────────────┬───────────────┘
               │                                │
               ▼                                ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│     SQLite DB (Alembic)      │ │   Zarfilm Browser Adapter    │
│  - libraries, library_roots  │ │  - ChromiumPage automation   │
│  - llm_providers, models     │ │  - LLM verifier callback     │
│  - llm_usage_logs            │ │  - Heuristic score fallback  │
└──────────────────────────────┘ └──────────────────────────────┘
```

---

## 2. Component Breakdown

### 2.1. Multi-Library & Scanner (`app/modules/library/`)
- **Models & Migration**:
  - `Library`: Represents an archive category with `content_type` and `preferred_language`.
  - `LibraryRoot`: Configured physical storage root path with drive online status and disk space monitoring.
  - `LibraryMembership`: Maps a `MediaWork` to a `Library`.
  - `ScanJob`: Asynchronous tracking record with counts of files discovered, imported, and unmatched.
- **Scanner Engine (`scanner.py`)**:
  - `scan_library_root()`: Traverses directory trees recursively, extracts title, year, codec, resolution, and subtitle paths, and catalogs media files into the database.
- **Directory Browser**:
  - `browse_directory()`: Returns safe listing of subdirectories, drive space usage, and write permissions for directory picking dialogs.

### 2.2. Analytics & Virtual Shortcut Categorizer (`app/modules/library/`)
- **`calculate_library_stats()`**: Computes total items, total disk size, average rating, top directors, decade distribution, and genre breakdown.
- **`categorize_library_virtually()`**: Creates symbolic links on Unix or `.lnk` shortcuts on Windows without touching or copying the original files:
  - By Director: Folders for directors meeting a configurable film threshold.
  - By Rating Bracket: `Masterpiece (8.5+)`, `Great (8.0 - 8.4)`, `Good (7.0 - 7.9)`, `Above Average (6.0 - 6.9)`, `Below 6.0`.
  - By Decade: `1970s`, `1980s`, `1990s`, `2000s`, `2010s`, `2020s`.

### 2.3. LLM Router & Cost Tracking (`app/modules/llm/`)
- **Models (`models.py`)**:
  - `LLMProvider`: Provider endpoint configuration with masked API key (`••••-key`) and priority.
  - `LLMModel`: Candidate model under a provider with input/output pricing per 1M tokens.
  - `LLMUsageLog`: Audit record storing prompt tokens, completion tokens, cost in USD, and success/failure status.
- **Service (`service.py`)**:
  - `call_with_failover()`: Evaluates candidate models in ascending priority order; if a model returns a 5xx or connection error, logs the attempt and cascades to the next candidate model.
  - `verify_or_select_movie()`: Specialized agent comparing candidate title, year, genres, and Persian plot summaries.
  - `select_best_quality()`: Specialized agent evaluating SoftSub vs Dubbed releases against natural language quality criteria.
  - `fetch_remote_models()`: Connects to `{base_url}/models` and discovers available models with pricing metadata.

### 2.4. Frontend React Integration (`frontend/src/`)
- **`FolderBrowserModal.tsx`**: Interactive server filesystem browser with breadcrumbs and directory navigation.
- **`ManageLibrariesModal.tsx`**: Interface for adding/deleting libraries, assigning multiple storage roots, and triggering live scans with real-time job progress tracking.
- **`AnalyticsAndShortcutsModal.tsx`**: Tabs for rich catalog analytics (directors, decades, genres) and non-destructive virtual shortcut generation.
- **`LLMSettingsModal.tsx`**: Management panel for LLM providers, model discovery, live playground testing, and token/USD cost audit logs.

---

## 3. Verification & Testing

1. **Automated Integration Tests**:
   - `tests/integration/test_multi_library_and_scanner.py`: Library CRUD, root assignment, and filesystem scanning.
   - `tests/integration/test_stats_and_categorizer.py`: Analytics calculation and symlink creation.
   - `tests/integration/test_llm_router.py`: Provider CRUD, model listing, remote discovery, failover cascade, token cost computation, and specialized agents.
   - Full test suite: **104 passing tests** in `pytest`.
2. **Frontend Type Checking & Build**:
   - `npm run build` executed with zero TypeScript or Vite bundle errors.
3. **Real-World Application Lifecycle**:
   - Verified local SQLite database migrations (`alembic upgrade head`).
   - Verified clean application startup and shutdown (`startup_app()` and `shutdown_app()`).
