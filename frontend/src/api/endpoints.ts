import { apiClient } from './client';
import {
  Aria2Stats,
  DownloadTask,
  ExternalSearchResult,
  FileAccessResult,
  ImportSummary,
  LibraryItem,
  MediaFile,
  MediaWorkDetail,
  MediaWorkSummary,
  PersonDetail,
  PersonalRecord,
  PersonalWorkCatalogItem,
  SourceRelease,
  StorageVolume,
  WatchStatusResult,
  WorkType,
} from '../types/api';

// -----------------------------------------------------------------------------
// Library & Storage Volumes
// -----------------------------------------------------------------------------

export async function getLibraryItems(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<LibraryItem[]> {
  const response = await apiClient.get<LibraryItem[]>('/library/items', {
    params,
  });
  return response.data;
}

export async function getLibraryItem(id: number): Promise<LibraryItem> {
  const response = await apiClient.get<LibraryItem>(`/library/items/${id}`);
  return response.data;
}

export async function getLibraryItemByWork(workId: number): Promise<LibraryItem | null> {
  try {
    const response = await apiClient.get<LibraryItem>(`/library/by-work/${workId}`);
    return response.data;
  } catch (err: any) {
    if (err.response?.status === 404) {
      return null;
    }
    throw err;
  }
}

export async function addLibraryItem(payload: {
  work_id?: number;
  tmdb_id?: number;
  work_type?: WorkType;
  status?: string;
  root_folder_path?: string;
}): Promise<LibraryItem> {
  const response = await apiClient.post<LibraryItem>('/library/items', payload);
  return response.data;
}

export async function updateLibraryItemStatus(
  id: number,
  status: string
): Promise<LibraryItem> {
  const response = await apiClient.patch<LibraryItem>(`/library/items/${id}/status`, {
    status,
  });
  return response.data;
}

export async function attachMediaFile(
  itemId: number,
  fileData: {
    file_path: string;
    file_name: string;
    file_size_bytes?: number;
    resolution?: string;
    video_codec?: string;
    source_type?: string;
    audio_languages?: string[];
    subtitle_paths?: string[];
    has_soft_sub?: boolean;
    episode_id?: number;
  }
): Promise<MediaFile> {
  const response = await apiClient.post<MediaFile>(`/library/items/${itemId}/files`, fileData);
  return response.data;
}

export async function deleteLibraryItem(id: number): Promise<void> {
  await apiClient.delete(`/library/items/${id}`);
}

export async function getStorageVolumes(): Promise<StorageVolume[]> {
  const response = await apiClient.get<StorageVolume[]>('/library/volumes');
  return response.data;
}

// -----------------------------------------------------------------------------
// Metadata & People
// -----------------------------------------------------------------------------

export async function searchMetadata(
  query: string,
  year?: number,
  workType: WorkType = 'MOVIE'
): Promise<ExternalSearchResult[]> {
  const response = await apiClient.get<ExternalSearchResult[]>('/metadata/search', {
    params: {
      query,
      year: year || undefined,
      work_type: workType,
    },
  });
  return response.data;
}

export async function ingestWork(
  tmdbId: number,
  workType: WorkType = 'MOVIE'
): Promise<MediaWorkDetail> {
  const response = await apiClient.post<MediaWorkDetail>('/metadata/ingest', {
    tmdb_id: tmdbId,
    work_type: workType,
  });
  return response.data;
}

export async function getWorkDetails(id: number): Promise<MediaWorkDetail> {
  const response = await apiClient.get<MediaWorkDetail>(`/metadata/works/${id}`);
  return response.data;
}

export async function getPersonDetails(id: number): Promise<PersonDetail> {
  const response = await apiClient.get<PersonDetail>(`/metadata/people/${id}`);
  return response.data;
}

export async function getPersonFilmography(
  id: number,
  creditType?: string,
  job?: string
): Promise<MediaWorkSummary[]> {
  const response = await apiClient.get<MediaWorkSummary[]>(`/metadata/people/${id}/filmography`, {
    params: {
      credit_type: creditType,
      job,
    },
  });
  return response.data;
}

// -----------------------------------------------------------------------------
// Sources & Zarfilm Releases
// -----------------------------------------------------------------------------

export async function discoverReleases(workId: number): Promise<{
  work_id: number;
  source_page_url?: string;
  total_found: number;
  releases: SourceRelease[];
}> {
  const response = await apiClient.post<{
    work_id: number;
    source_page_url?: string;
    total_found: number;
    releases: SourceRelease[];
  }>(`/sources/works/${workId}/discover`);
  return response.data;
}

export async function listReleases(
  workId: number,
  episodeId?: number
): Promise<SourceRelease[]> {
  const response = await apiClient.get<SourceRelease[]>(`/sources/works/${workId}/releases`, {
    params: { episode_id: episodeId },
  });
  return response.data;
}

// -----------------------------------------------------------------------------
// Downloads & Aria2 Management
// -----------------------------------------------------------------------------

export async function getDownloadTasks(params?: {
  status?: string;
  library_item_id?: number;
  limit?: number;
  offset?: number;
}): Promise<DownloadTask[]> {
  const response = await apiClient.get<DownloadTask[]>('/downloads', { params });
  return response.data;
}

export async function getDownloadTask(id: number): Promise<DownloadTask> {
  const response = await apiClient.get<DownloadTask>(`/downloads/${id}`);
  return response.data;
}

export async function createDownloadTask(
  payload: {
    library_item_id: number;
    release_id?: number;
    episode_id?: number;
    download_url?: string;
    destination_dir?: string;
    file_name?: string;
  },
  startImmediately = true
): Promise<DownloadTask> {
  const response = await apiClient.post<DownloadTask>('/downloads', payload, {
    params: { start_immediately: startImmediately },
  });
  return response.data;
}

export async function pauseDownload(id: number): Promise<DownloadTask> {
  const response = await apiClient.post<DownloadTask>(`/downloads/${id}/pause`);
  return response.data;
}

export async function resumeDownload(id: number): Promise<DownloadTask> {
  const response = await apiClient.post<DownloadTask>(`/downloads/${id}/resume`);
  return response.data;
}

export async function cancelDownload(id: number): Promise<DownloadTask> {
  const response = await apiClient.delete<DownloadTask>(`/downloads/${id}`);
  return response.data;
}

export async function getAria2Stats(): Promise<Aria2Stats> {
  const response = await apiClient.get<Aria2Stats>('/downloads/stats');
  return response.data;
}

export async function setSpeedLimit(limitKb: number): Promise<void> {
  await apiClient.post('/downloads/speed-limit', {
    max_download_limit_kb: limitKb,
  });
}

// -----------------------------------------------------------------------------
// Playback & OS Launching
// -----------------------------------------------------------------------------

export async function openMediaFile(mediaFileId: number): Promise<FileAccessResult> {
  const response = await apiClient.post<FileAccessResult>(`/playback/files/${mediaFileId}/open`);
  return response.data;
}

export async function openWork(workId: number, episodeId?: number): Promise<FileAccessResult> {
  const response = await apiClient.post<FileAccessResult>(`/playback/works/${workId}/open`, null, {
    params: { episode_id: episodeId },
  });
  return response.data;
}

export async function openFileLocation(mediaFileId: number): Promise<FileAccessResult> {
  const response = await apiClient.post<FileAccessResult>(
    `/playback/files/${mediaFileId}/open-location`
  );
  return response.data;
}

export async function getWatchStatus(
  workId: number,
  episodeId?: number
): Promise<WatchStatusResult> {
  const response = await apiClient.get<WatchStatusResult>(`/playback/works/${workId}/status`, {
    params: { episode_id: episodeId },
  });
  return response.data;
}

// -----------------------------------------------------------------------------
// Personal Records, Ratings, Watchlist, Diary
// -----------------------------------------------------------------------------

export async function getPersonalRecord(workId: number): Promise<PersonalRecord> {
  const response = await apiClient.get<PersonalRecord>(`/personal/records/${workId}`);
  return response.data;
}

export async function toggleWatchlist(
  workId: number,
  inWatchlist?: boolean
): Promise<PersonalRecord> {
  const response = await apiClient.post<PersonalRecord>(
    `/personal/records/${workId}/watchlist`,
    inWatchlist !== undefined ? { in_watchlist: inWatchlist } : null
  );
  return response.data;
}

export async function toggleFavorite(
  workId: number,
  isFavorite?: boolean
): Promise<PersonalRecord> {
  const response = await apiClient.post<PersonalRecord>(
    `/personal/records/${workId}/favorite`,
    isFavorite !== undefined ? { is_favorite: isFavorite } : null
  );
  return response.data;
}

export async function rateWork(
  workId: number,
  rating: number | null
): Promise<PersonalRecord> {
  const response = await apiClient.post<PersonalRecord>(`/personal/records/${workId}/rate`, {
    rating,
  });
  return response.data;
}

export async function updatePersonalRecord(
  workId: number,
  data: {
    watch_status?: string;
    user_rating?: number | null;
    in_watchlist?: boolean;
    is_favorite?: boolean;
    user_review?: string | null;
  }
): Promise<PersonalRecord> {
  const response = await apiClient.patch<PersonalRecord>(`/personal/records/${workId}`, data);
  return response.data;
}

export async function logWatchDiary(payload: {
  work_id: number;
  episode_id?: number;
  watched_at?: string;
  user_rating?: number;
  review_note?: string;
  is_rewatch?: boolean;
}): Promise<any> {
  const response = await apiClient.post('/personal/diary', payload);
  return response.data;
}

export async function filterPersonalCatalog(params?: {
  watch_status?: string;
  in_watchlist?: boolean;
  is_favorite?: boolean;
  min_rating?: number;
  max_rating?: number;
  shelf_id?: number;
  genre_id?: number;
  sort_by?: string;
  sort_order?: string;
  limit?: number;
  offset?: number;
}): Promise<PersonalWorkCatalogItem[]> {
  const response = await apiClient.get<PersonalWorkCatalogItem[]>('/personal/works', { params });
  return response.data;
}

export async function listShelves(): Promise<any[]> {
  const response = await apiClient.get('/personal/shelves');
  return response.data;
}

export async function createShelf(payload: {
  name: string;
  description?: string;
  is_smart_shelf?: boolean;
}): Promise<any> {
  const response = await apiClient.post('/personal/shelves', payload);
  return response.data;
}

// -----------------------------------------------------------------------------
// Integrations (Letterboxd)
// -----------------------------------------------------------------------------

export async function importLetterboxdFile(
  file: File,
  conflictPolicy: 'PRESERVE_LOCAL' | 'OVERWRITE_LOCAL' = 'PRESERVE_LOCAL',
  scaleMode: 'RAW' | 'TEN_POINT' = 'RAW'
): Promise<ImportSummary> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('conflict_policy', conflictPolicy);
  formData.append('scale_mode', scaleMode);

  const response = await apiClient.post<ImportSummary>(
    '/integrations/letterboxd/import-file',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
}

export async function listSyncRuns(params?: {
  provider?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<any[]> {
  const response = await apiClient.get('/integrations/sync-runs', { params });
  return response.data;
}
