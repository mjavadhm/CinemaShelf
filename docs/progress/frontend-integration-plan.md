# Frontend Integration Plan — CinemaShelf

This plan outlines the integration of the React + TypeScript + Vite frontend (`frontend/`) with the FastAPI backend (`app/`), replacing all mock data with real API calls using **Axios** and **TanStack Query (React Query v5)**.

---

## 1. Objectives & Scope
- **Backend Enhancements**:
  - Add `CORSMiddleware` in `app/main.py` allowing frontend origins (`http://localhost:5173`, `http://127.0.0.1:5173`).
  - Add `/api` router mount in `app/main.py` alongside direct mounts for full backward compatibility.
  - Implement `GET /library/volumes` (and `/api/library/volumes`) in `app/modules/library/` returning storage drives, mount paths, free/used space (`shutil.disk_usage`), and online status.
  - Implement `GET /metadata/people/{id}` (and `/api/metadata/people/{id}`) returning person details along with all associated works categorized into cast and crew.
  - Expose downloads management routes on `downloads/router.py` (and include in `/api`).
  - Add `is_online` dynamic property on `MediaFile` and `MediaFileResponse`.
- **Frontend API & State Layer**:
  - Typed Axios client (`frontend/src/api/client.ts`) with baseURL `/api` and error interceptors.
  - API endpoint functions (`frontend/src/api/endpoints.ts`) corresponding to backend Pydantic contracts.
  - React Query hooks (`frontend/src/hooks/`):
    - `useLibraryItems`: catalog listing with status, genre, resolution, and availability filters.
    - `useWorkDetails`: comprehensive work metadata, credits, media files, and watch/rating state.
    - `usePersonDetails`: person biographical information and categorized filmography.
    - `useDownloadQueue`: 2-second polling of Aria2 tasks and stats, with pause/resume/cancel/add mutations.
    - `usePlaybackLaunch`: mutations for launching OS media player or opening file directory.
    - `usePersonalActions`: mutations for rating, watchlist toggle, favorites, and watch diary logs.
    - `useSearchAndAddWork`: external TMDB search, work ingestion, Zarfilm release discovery, and download dispatch.
    - `useLetterboxdSync`: Letterboxd CSV/ZIP import and sync run status checking.
    - `useStorageVolumes`: live polling of storage disk volumes.
- **Frontend UI & Interactive Flows**:
  - `AppLayout`: live storage drive widget, live download speed badge, modal for TMDB search and work addition.
  - `LibraryPage`: real movie catalog, loading skeletons, empty state, genre & resolution filters.
  - `MovieDetailsPage`: complete metadata, interactive user rating, direct playback button, file location button, Zarfilm release discovery and download launcher, clickable cast/crew leading to person details.
  - `PersonDetailsPage`: new page displaying person information and filmography split into actor and crew sections.
  - `WatchlistDownloadsPage`: real watchlist grid with Zarfilm download buttons, Letterboxd file import modal, and real-time Aria2 download queue with pause/resume/cancel actions.

---

## 2. Verification Strategy
1. Run backend automated test suite (`/home/javadhm/venv/bin/pytest`) ensuring 100% pass on all unit, integration, and architecture tests.
2. Add new unit and integration tests covering the new endpoints:
   - Volume status query (`test_storage_volumes`)
   - Person details & filmography query (`test_person_details`)
   - Download router operations
3. Run `npm run build` inside `frontend/` to ensure clean TypeScript compilation and Vite bundle production.
