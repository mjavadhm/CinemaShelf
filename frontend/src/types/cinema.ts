export type WorkType = 'MOVIE' | 'SHOW';
export type LibraryStatus = 'WANTED' | 'DOWNLOADING' | 'AVAILABLE' | 'MISSING';

export interface StorageDrive {
  id: string;
  label: string;
  mountPath: string;
  usedGb: number;
  totalGb: number;
  isOnline: boolean;
}

export interface MediaFileItem {
  id: number;
  resolution: '2160p' | '1080p' | '720p';
  sourceType: string;
  codec: string;
  audio: string;
  bitrate: string;
  sizeGb: number;
  filePath: string;
  driveLabel: string;
  isOnline: boolean;
  hasPersianSub: boolean;
}

export interface CreditPerson {
  id: number;
  tmdbPersonId: number;
  name: string;
  persianName?: string;
  role: 'DIRECTOR' | 'ACTOR' | 'WRITER' | 'COMPOSER';
  characterName?: string;
  profileUrl: string;
}

export interface MovieWork {
  id: number;
  tmdbId: number;
  imdbId: string;
  title: string;
  persianTitle: string;
  releaseYear: number;
  runtimeMinutes: number;
  director: string;
  genres: string[];
  imdbRating: number;
  letterboxdRating: number;
  userRating?: number;
  posterUrl: string;
  backdropUrl?: string;
  overview: string;
  bestResolution: '4K' | '1080p' | '720p';
  isDriveOnline: boolean;
  driveLabel: string;
  inWatchlist: boolean;
  isWatched: boolean;
  lastWatchedDate?: string;
  files: MediaFileItem[];
  credits: CreditPerson[];
}

export interface DownloadQueueItem {
  id: number;
  gid: string;
  title: string;
  year: number;
  qualityLabel: string;
  status: 'ACTIVE' | 'PAUSED' | 'QUEUED' | 'COMPLETED' | 'ERROR';
  progressPercent: number;
  downloadedGb: number;
  totalGb: number;
  speedMbps: number;
  etaText: string;
  destinationDrive: string;
}
