/**
 * Strongly typed DTO interfaces mirroring the CinemaShelf FastAPI backend schemas.
 */

export type WorkType = 'MOVIE' | 'SHOW';
export type CreditType = 'CAST' | 'CREW';
export type LibraryItemStatus =
  | 'WANTED'
  | 'DOWNLOADING'
  | 'AVAILABLE'
  | 'PARTIAL'
  | 'MISSING'
  | 'ARCHIVED';

export type WatchStatus =
  | 'UNWATCHED'
  | 'PLAN_TO_WATCH'
  | 'WATCHING'
  | 'WATCHED'
  | 'DROPPED';

export type DownloadTaskStatus =
  | 'QUEUED'
  | 'ACTIVE'
  | 'PAUSED'
  | 'COMPLETED'
  | 'ERROR'
  | 'CANCELLED';

export interface StorageVolume {
  id: string;
  label: string;
  mount_path: string;
  used_bytes: number;
  total_bytes: number;
  is_online: boolean;
}

export interface Genre {
  id: number;
  tmdb_genre_id: number;
  name: string;
  persian_name?: string | null;
}

export interface Person {
  id: number;
  tmdb_person_id: number;
  name: string;
  original_name?: string | null;
  persian_name?: string | null;
  known_for_department?: string | null;
  profile_path?: string | null;
}

export interface WorkCredit {
  id: number;
  person: Person;
  credit_type: CreditType;
  department: string;
  job: string;
  character_name?: string | null;
  billing_order?: number | null;
}

export interface MediaWorkSummary {
  id: number;
  work_type: WorkType;
  tmdb_id: number;
  imdb_id?: string | null;
  title: string;
  original_title?: string | null;
  persian_title?: string | null;
  release_date?: string | null;
  release_year?: number | null;
  runtime_minutes?: number | null;
  status?: string | null;
  poster_path?: string | null;
  tmdb_rating?: number | null;
  imdb_rating?: number | null;
  rotten_tomatoes_score?: number | null;
  metascore?: number | null;
  genres: Genre[];
}

export interface MediaWorkDetail extends MediaWorkSummary {
  original_language?: string | null;
  overview?: string | null;
  backdrop_path?: string | null;
  tmdb_vote_count?: number | null;
  imdb_votes?: number | null;
  last_synced_at?: string | null;
  credits: WorkCredit[];
  seasons?: any[];
}

export interface PersonCreditDetail {
  id: number;
  work_id: number;
  credit_type: CreditType;
  department: string;
  job: string;
  character_name?: string | null;
  billing_order?: number | null;
  work: MediaWorkSummary;
}

export interface PersonDetail extends Person {
  cast: PersonCreditDetail[];
  crew: PersonCreditDetail[];
}

export interface MediaFile {
  id: number;
  library_item_id: number;
  episode_id?: number | null;
  file_path: string;
  file_name: string;
  file_size_bytes?: number | null;
  resolution?: string | null;
  video_codec?: string | null;
  source_type?: string | null;
  audio_languages?: string[] | null;
  subtitle_paths?: string[] | null;
  has_soft_sub: boolean;
  is_missing: boolean;
  is_online: boolean;
  last_verified_at?: string | null;
  created_at: string;
}

export interface PersonalSummary {
  user_rating?: number | null;
  in_watchlist: boolean;
  is_favorite: boolean;
  watch_status?: WatchStatus | string | null;
  last_watched_at?: string | null;
}

export interface PersonalRecord {
  id: number;
  work_id: number;
  watch_status: WatchStatus;
  user_rating?: number | null;
  in_watchlist: boolean;
  is_favorite: boolean;
  user_review?: string | null;
  watch_count: number;
  last_watched_at?: string | null;
}

export interface PersonalWorkCatalogItem {
  work_id: number;
  title: string;
  original_title?: string | null;
  persian_title?: string | null;
  release_year?: number | null;
  poster_path?: string | null;
  tmdb_rating?: number | null;
  imdb_rating?: number | null;
  personal?: PersonalRecord | null;
}

export interface LibraryItem {
  id: number;
  work_id: number;
  status: LibraryItemStatus;
  root_folder_path?: string | null;
  added_at: string;
  work: MediaWorkSummary;
  media_files: MediaFile[];
  personal_record?: PersonalSummary | null;
}

export interface SourceRelease {
  id: number;
  work_id: number;
  episode_id?: number | null;
  provider: string;
  source_page_url?: string | null;
  download_url: string;
  quality_label?: string | null;
  resolution?: string | null;
  encoder?: string | null;
  size_text?: string | null;
  size_bytes?: number | null;
  is_dubbed: boolean;
  has_persian_sub: boolean;
  discovered_at: string;
}

export interface DownloadTask {
  id: number;
  library_item_id: number;
  episode_id?: number | null;
  release_id?: number | null;
  aria2_gid?: string | null;
  download_url: string;
  destination_dir: string;
  file_name?: string | null;
  status: DownloadTaskStatus;
  total_bytes?: number | null;
  downloaded_bytes: number;
  progress_percent: number;
  download_speed_bps: number;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Aria2Stats {
  download_speed: number;
  upload_speed: number;
  num_active: number;
  num_waiting: number;
  num_stopped: number;
}

export interface ExternalSearchResult {
  tmdb_id: number;
  title: string;
  work_type: WorkType;
  original_title?: string | null;
  release_year?: number | null;
  overview?: string | null;
  poster_path?: string | null;
  vote_average?: number | null;
}

export interface SyncRun {
  id: number;
  provider: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'PARTIAL';
  movies_imported: number;
  ratings_imported: number;
  reviews_imported: number;
  watchlist_imported: number;
  unmatched_count: number;
  error_message?: string | null;
  started_at: string;
  completed_at?: string | null;
}

export interface ImportSummary {
  run_id: number;
  movies_imported: number;
  ratings_imported: number;
  reviews_imported: number;
  watchlist_imported: number;
  unmatched_count: number;
  unmatched_entries: Array<{
    title: string;
    year?: number | null;
    letterboxd_uri?: string | null;
    reason: string;
  }>;
}

export interface FileAccessResult {
  success: boolean;
  message: string;
  target_path: string;
}

export interface WatchStatusResult {
  work_id: number;
  episode_id?: number | null;
  is_watched: boolean;
  last_watched_at?: string | null;
}

/**
 * Helper to construct full TMDB image URLs safely.
 */
export function getTmdbImageUrl(
  path?: string | null,
  size: 'w185' | 'w300' | 'w500' | 'original' = 'w500'
): string {
  if (!path) {
    return 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500&auto=format&fit=crop&q=80';
  }
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  const clean = path.startsWith('/') ? path : `/${path}`;
  return `https://image.tmdb.org/t/p/${size}${clean}`;
}
