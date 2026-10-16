# Walkthrough: Library Pagination, Letterboxd HTML Parser & Browser Automation

## 1. Overview & Context

This implementation solves two major user requirements:
1. **Full Library Pagination & Server-side Search**:
   - Previously, the catalog API limited responses to a maximum of 100 items (`limit=50`, `le=100`), causing movies beyond the 100th to be invisible in the UI and undetectable via search.
   - The system now performs database-level search and filtering across the entire collection (300+ films), returning standard pagination headers (`X-Total-Count`, `X-Total-Pages`, `X-Current-Page`, `X-Page-Size`), coupled with an interactive pagination toolbar in the frontend.
2. **Dual-Mode Letterboxd Integration**:
   - **Local HTML Parser**: Ingests saved/exported Letterboxd HTML pages (such as user `films`, `watchlist`, and detail pages) directly from a local directory (defaulting to `for scraping/`, ignored by Git). It extracts movie titles, release years, Letterboxd slugs/URIs, liked flags, and user ratings (converting CSS `rated-1`..`rated-10` into calibrated scores).
   - **Automated Browser Scraper (`DrissionPage`)**: Operates identically to the Zarfilm browser scraper using a dedicated persistent user profile (`data/profiles/letterboxd`). Handles multi-page pagination (Letterboxd displays 72 movies per page; the scraper follows `a.next` across pages). Enables direct submission of user ratings from CinemaShelf to Letterboxd.

---

## 2. Component Breakdown

### A. Library Search & Pagination
- **Repository (`app/modules/library/repository.py`)**:
  - `_build_items_query(...)`: Adds dynamic `search` (matching titles, original titles, Persian titles, and file names) and `genre` filtering.
  - `list_items(...)`: Applies pagination with `offset` and `limit` (up to 1,000 items).
  - `count_items(...)`: Computes exact total items matching active filters via `select(func.count()).select_from(subquery)`.
- **Service & Router (`app/modules/library/service.py`, `router.py`)**:
  - `GET /library/items`: Returns items list and exposes HTTP headers: `X-Total-Count`, `X-Total-Pages`, `X-Current-Page`, `X-Page-Size`.
- **Frontend (`frontend/src/`)**:
  - `useLibraryItems`: Transmits `page`, `pageSize`, `search`, and `genre` to the backend.
  - `LibraryPage.tsx`: Renders pagination bar with page jumps, previous/next buttons, and selectable page sizes (24, 48, 96, 500).

### B. Letterboxd HTML Parser (`app/adapters/letterboxd/parser.py`)
- `LetterboxdHtmlParser.parse_html(...)`:
  - Parses `li.griditem` structures and `LazyPoster` React components.
  - Normalizes film titles, extracting 4-digit release years (e.g. `"The Florida Project (2017)"` -> `title="The Florida Project"`, `release_year=2017`).
  - Converts CSS rating classes `rated-1` to `rated-10` to half-star floats (`0.5` to `5.0`).
  - Detects pagination links (`a.next`) for multi-page iteration.
  - Recognizes single film detail pages (e.g., `#userpanel`) to extract individual movie ratings while ignoring ancillary recommendation carousels.
- `LetterboxdHtmlParser.parse_local_folder(...)`:
  - Scans directories for `.html` files (skipping search query results).
  - Merges records by `(title.lower(), release_year)`, preserving ratings and upgrading watchlist entries to watched when present.

### C. Letterboxd Browser Automation (`app/adapters/letterboxd/scraper.py`)
- `LetterboxdBrowserScraper`:
  - Utilizes `DrissionPage` with persistent profile directory `data/profiles/letterboxd`.
  - `open_browser(url)`: Launches the browser so users can log into their Letterboxd account once.
  - `scrape_user_films(username, max_pages)`: Navigates to `https://letterboxd.com/{username}/films/`, extracting items and following `next_url` until pagination ends or `max_pages` is reached.
  - `scrape_user_watchlist(username, max_pages)`: Scrapes all watchlist pages.
  - `scrape_all(username, max_pages)`: Combines and deduplicates films and watchlist entries.
  - `rate_film(title, rating_out_of_10, year, slug)`: Navigates to the film page directly or via search, finds the user rating radio input / star trigger within `section.actions-panel`, submits the score (1-10), and waits for the AJAX confirmation.

### D. Integrations Service & API (`app/modules/integrations/`)
- `IntegrationsService._process_items(...)`:
  - Reusable transaction orchestrator for CSV, ZIP, local HTML, and browser scraping.
  - Applies conflict policies (`PRESERVE_LOCAL`, `OVERWRITE_LOCAL`) and scale modes (`RAW`, `TEN_POINT`).
  - Records sync audits in `IntegrationSyncRun`.
- **New API Endpoints**:
  - `POST /integrations/letterboxd/sync-local-html`: Ingests from local HTML folder.
  - `POST /integrations/letterboxd/browser-sync`: Executes live multi-page browser scrape.
  - `POST /integrations/letterboxd/open-browser`: Opens persistent browser for login.
  - `POST /integrations/letterboxd/rate`: Submits rating to Letterboxd.

### E. Frontend UI Integration
- **`LetterboxdImportModal.tsx`**:
  - **Tab 1: Saved Files**: 1-click sync from `for scraping/` folder + manual ZIP/CSV drag-and-drop.
  - **Tab 2: Browser Scraper**: Button to open browser for login, username input, page limit selector, watchlist toggle, and live sync trigger.
  - Detailed summary display upon completion.
- **`MovieDetailsPage.tsx`**:
  - Interactive rating bar augmented with **"ثبت در Letterboxd"** (Rate on Letterboxd) button.
  - Triggers automated browser rating and displays feedback upon submission.

---

## 3. Verification & Test Coverage

1. **Automated Unit Tests**:
   - `tests/unit/test_letterboxd_adapter.py`: Validated CSV, ZIP, HTML films parsing with ratings, watchlist parsing, single film detail parsing, and local folder ingestion (13 tests passed).
   - `tests/unit/test_letterboxd_scraper.py`: Validated browser multi-page loop, pagination following, and rating element interaction (2 tests passed).
2. **Integration Tests**:
   - `tests/integration/test_api_phase5.py`: Validated CSV/ZIP imports, sync audit logging, local HTML sync endpoint, browser sync endpoint, browser open endpoint, and rating submission endpoint (6 tests passed).
3. **Full Test Suite**:
   - `pytest tests/`: All 112 test cases across all modules passed cleanly in ~10.5 seconds.
4. **Real-World Smoke Testing**:
   - Application startup (`startup_app(settings)`) and shutdown (`shutdown_app()`) verified against local SQLite database and background job runner.
   - Frontend production build (`npm run build`) compiled successfully with 0 errors.
