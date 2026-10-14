# Frontend Integration Walkthrough — CinemaShelf

This walkthrough documents the full integration between the React + TypeScript + Vite frontend (`frontend/`) and the FastAPI backend (`app/`), replacing all mock data with real REST API endpoints using **Axios** and **TanStack Query (React Query v5)**.

---

## 1. Architecture & Layer Integration

```text
React (Vite 5 + React 18)
  ├── UI Pages & Components
  │     ├── AppLayout (Sidebar volumes + Header speed + TMDB search modal)
  │     ├── LibraryPage (Real items catalog + Dynamic filters + Loading skeletons)
  │     ├── MovieDetailsPage (Full metadata + 10-star rating + Direct player launch + Zarfilm releases)
  │     ├── PersonDetailsPage (/people/:id: Bio + Crew filmography + Cast filmography)
  │     └── WatchlistDownloadsPage (Watchlist grid + Letterboxd CSV/ZIP import modal + 4-col Aria2 queue)
  ├── TanStack Query Hooks (frontend/src/hooks/)
  │     ├── useLibraryItems (catalog listing, multi-field filtering)
  │     ├── useWorkDetails (metadata, credits, media files, watch status, personal rating)
  │     ├── usePersonDetails (biography, cast and crew filmographies)
  │     ├── useDownloadQueue (2-second polling of Aria2 tasks & stats, pause/resume/cancel/add)
  │     ├── usePlaybackLaunch (direct OS player launcher & file location reveal)
  │     ├── usePersonalActions (watchlist toggle, 10-point rating, watch diary)
  │     ├── useSearchAndAddWork (TMDB external search, library ingestion, Zarfilm scraping)
  │     ├── useLetterboxdSync (CSV/ZIP multipart import, sync run status)
  │     └── useStorageVolumes (periodic disk space & online/offline volume polling)
  └── Typed API Layer (frontend/src/api/ & frontend/src/types/api.ts)
        ├── client.ts (Axios instance with baseURL /api & response interceptors)
        └── endpoints.ts (Type-safe functions matching FastAPI Pydantic contracts)
              │
              ▼ (HTTP JSON / Multipart)
FastAPI Backend (app/)
  ├── CORS Middleware (Allow origins: http://localhost:5173, http://127.0.0.1:5173)
  ├── Root & /api Routers Mount:
  │     ├── /api/library & /library (items, by-work, volumes)
  │     ├── /api/metadata & /metadata (search, ingest, works, people)
  │     ├── /api/sources & /sources (releases, discovery, tasks)
  │     ├── /api/downloads & /downloads (consolidated download tasks & stats)
  │     ├── /api/playback & /playback (launch, location, watch status)
  │     ├── /api/personal & /personal (records, watchlist, diary, shelves)
  │     └── /api/integrations & /integrations (Letterboxd import, sync runs)
  └── SQLite / SQLAlchemy Persistence Layer
```

---

## 2. Implemented Backend Adjustments

1. **CORS Configuration & `/api` Router Mount (`app/main.py`):**
   - Added `CORSMiddleware` permitting requests from `http://localhost:5173` and `http://127.0.0.1:5173` with credentials, all methods, and headers.
   - Built a consolidated `api_router = APIRouter(prefix="/api")` mounting all module routers under `/api` while maintaining direct root mounts for existing integration tests.
2. **Storage Volumes Status Endpoint (`GET /library/volumes` & `GET /api/library/volumes`):**
   - Automatically detects volumes from `settings.download_dir`, non-null `root_folder_path` in `LibraryItem`, and registered `file_path` entries in `MediaFile`.
   - Inspects physical accessibility using `os.path.exists()` and computes disk space using `shutil.disk_usage()`.
   - Disconnected drives are reported with `is_online=False`, ensuring offline archive indicators work as intended.
3. **Person Biography & Filmography Endpoint (`GET /metadata/people/{id}` & `GET /api/metadata/people/{id}`):**
   - Returns complete person details along with their work credits categorized into `cast` (Actor with character names) and `crew` (Director, Writer, etc.).
4. **Downloads Router (`app/modules/downloads/router.py`):**
   - Exposes download queue management endpoints (`GET /downloads`, `POST /downloads`, `GET /downloads/stats`, `POST /downloads/{id}/pause`, `POST /downloads/{id}/resume`, `DELETE /downloads/{id}`, `POST /downloads/speed-limit`).
5. **Physical Media File Online Status:**
   - Added `is_online` dynamic property on `MediaFile` checking `os.path.exists(file_path)` and mirrored in `MediaFileResponse`.

---

## 3. Frontend Integration Components & Pages

1. **`AppLayout.tsx`:**
   - Right sidebar connects to `useStorageVolumes()` to show live drive labels, used/total GB, and online/offline status dots.
   - Shows an alert banner when any configured storage volume is disconnected.
   - Header displays live download speed (MB/s) and active tasks counter polled every 2s via `useDownloadQueue()`.
   - Header includes "+ افزودن فیلم / جستجوی TMDB" button opening `AddWorkModal`.
2. **`LibraryPage.tsx` (`/`):**
   - Loads real catalog items with loading skeletons.
   - Clean 1-row filter bar with dynamic genre filter (extracted from available items), resolution selector, and "فقط هاردهای متصل" toggle.
   - Movie cards render poster, best resolution badge, online/offline status, rating, and navigation to details.
3. **`MovieDetailsPage.tsx` (`/works/:id`):**
   - Displays full work metadata, IMDb and TMDB ratings, personal rating, runtime, director, and genres.
   - Interactive 10-star rating widget allows rating or clearing rating in real time.
   - Watchlist toggle button updates personal state immediately.
   - "پخش مستقیم فیلم" launches the OS media player for the selected file via `openMediaFile`.
   - "Open Folder" reveals the file location in the OS file manager.
   - "جستجوی لینک‌های دانلود (زرفیلم)" triggers live release discovery and displays quality releases with a direct "دانلود با Aria2" button.
   - Notable cast & crew cards are clickable, routing to `/people/:id`.
4. **`PersonDetailsPage.tsx` (`/people/:id`):**
   - Renders photo, Persian name, original English name, and department badge.
   - Dual-tab filmography view: "آثار به عنوان کارگردان / عوامل" and "آثار به عنوان بازیگر", linking back to work cards.
5. **`WatchlistDownloadsPage.tsx` (`/watchlist`):**
   - Top section shows all watchlist items with direct movie links and "وارد کردن آرشیو Letterboxd" button.
   - Includes `LetterboxdImportModal` for uploading Letterboxd ZIP archives or CSV files with customizable conflict and rating scale policies.
   - Bottom section features a live 4-column Aria2 download manager with real-time speed, progress bars, downloaded/total GB, and working Pause, Resume, Cancel, and Open Folder controls.

---

## 4. Verification Results

### Backend Automated Test Suite
```text
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/javadhm/CinemaShelf
configfile: pyproject.toml
plugins: anyio-4.15.1, asyncio-1.4.0
collected 97 items

tests/architecture/test_no_legacy_imports.py .                           [  1%]
tests/integration/test_api_phase1.py ...                                 [  4%]
tests/integration/test_api_phase2.py ...                                 [  7%]
tests/integration/test_api_phase3.py .                                   [  8%]
tests/integration/test_api_phase4.py ....                                [ 12%]
tests/integration/test_api_phase5.py ....                                [ 16%]
tests/integration/test_db_session.py .                                   [ 17%]
tests/integration/test_frontend_api_endpoints.py .....                   [ 22%]
tests/integration/test_models.py ......                                  [ 28%]
tests/unit/test_aria2_adapter.py .......                                 [ 36%]
tests/unit/test_download_handlers.py ....                                [ 40%]
tests/unit/test_health.py ..                                             [ 42%]
tests/unit/test_integrations_service.py .......                          [ 49%]
tests/unit/test_letterboxd_adapter.py .........                          [ 58%]
tests/unit/test_library_service.py .....                                 [ 63%]
tests/unit/test_metadata_adapter.py ...                                  [ 67%]
tests/unit/test_metadata_service.py ....                                 [ 71%]
tests/unit/test_os_opener.py ....                                        [ 75%]
tests/unit/test_personal_service.py .......                              [ 82%]
tests/unit/test_playback_service.py ......                               [ 88%]
tests/unit/test_sources_service.py ......                                [ 94%]
tests/unit/test_zarfilm_adapter.py .....                                 [100%]

======================== 97 passed, 1 warning in 4.85s =========================
```

### Real-World Smoke Testing Lifecycle
- Real database migration status: `alembic upgrade head` succeeded cleanly.
- Application startup/shutdown: `startup_app(settings)` and `shutdown_app()` booted background schedulers and resolved SQLAlchemy mappers.
- Smoke request verification against `/health`, `/api/library/volumes`, `/api/library/items`, and `/api/downloads/stats` (connected to real Aria2 daemon) returned HTTP 200 OK.

### Frontend TypeScript & Bundle Verification
```text
> cinemashelf-frontend@0.1.0 build
> tsc -b && vite build

vite v5.4.21 building for production...
✓ 1693 modules transformed.
dist/index.html                   0.84 kB │ gzip:   0.51 kB
dist/assets/index-CMx6YUho.css   25.50 kB │ gzip:   5.26 kB
dist/assets/index-I3ZHFnaO.js   335.56 kB │ gzip: 102.74 kB
✓ built in 2.97s
```
Zero TypeScript or bundling errors. Mock data has been completely eliminated.
