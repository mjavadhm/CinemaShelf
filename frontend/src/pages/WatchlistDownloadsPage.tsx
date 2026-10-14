import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Bookmark,
  Download,
  Pause,
  Play,
  Trash2,
  FolderOpen,
  ArrowDownCircle,
  RefreshCw,
  Loader2,
  Film,
  ExternalLink,
  CheckCircle2,
} from 'lucide-react';
import { useWatchlistWorks, usePersonalActions } from '../hooks/usePersonalActions';
import { useDownloadQueue } from '../hooks/useDownloadQueue';
import { usePlaybackLaunch } from '../hooks/usePlaybackLaunch';
import { getTmdbImageUrl } from '../types/api';
import { LetterboxdImportModal } from '../components/LetterboxdImportModal';

export const WatchlistDownloadsPage: React.FC = () => {
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  const { data: watchlistWorks, isLoading: isLoadingWatchlist } = useWatchlistWorks();
  const { toggleWatchlist } = usePersonalActions();
  const { openFileLocation } = usePlaybackLaunch();

  const {
    tasks,
    speedMbps,
    activeCount,
    queuedCount,
    pauseTask,
    resumeTask,
    cancelTask,
    isPausing,
    isResuming,
    isCancelling,
    isLoading: isLoadingDownloads,
  } = useDownloadQueue();

  const handleOpenTaskFolder = async (destDir: string) => {
    // If destination folder is known, we can call openFileLocation with a dummy or use service
    // Note: If task has no media_file_id, we can notify or copy path
    if (navigator.clipboard) {
      navigator.clipboard.writeText(destDir);
    }
  };

  return (
    <div className="space-y-8">
      {/* Top Section: Compact Watchlist Grid */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Bookmark className="w-5 h-5 text-shelf-amber" />
              <span>واچ‌لیست من ({watchlistWorks?.length || 0} اثر)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              فیلم‌های در انتظار تماشا یا دانلود خودکار از زرفیلم
            </p>
          </div>

          {/* Letterboxd Import Trigger */}
          <button
            onClick={() => setIsImportModalOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-shelf-card hover:bg-slate-800 text-slate-200 border border-shelf-border text-xs font-medium transition shrink-0"
          >
            <RefreshCw className="w-3.5 h-3.5 text-emerald-400" />
            <span>همگام‌سازی / وارد کردن فایل Letterboxd</span>
          </button>
        </div>

        {/* Watchlist Loading State */}
        {isLoadingWatchlist && (
          <div className="py-12 flex flex-col items-center justify-center gap-2 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin text-shelf-amber" />
            <span className="text-xs">در حال بارگذاری لیست تماشا...</span>
          </div>
        )}

        {/* Empty Watchlist */}
        {!isLoadingWatchlist && (!watchlistWorks || watchlistWorks.length === 0) && (
          <div className="p-8 text-center bg-shelf-card border border-shelf-border rounded-xl space-y-2">
            <p className="text-slate-300 text-xs font-bold">واچ‌لیست شما خالی است</p>
            <p className="text-slate-500 text-[11px]">
              می‌توانید با جستجوی فیلم‌ها در هدر یا وارد کردن فایل صادراتی Letterboxd فیلم‌ها را به واچ‌لیست بیفزایید.
            </p>
          </div>
        )}

        {/* Watchlist Grid */}
        {!isLoadingWatchlist && watchlistWorks && watchlistWorks.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-4">
            {watchlistWorks.map((item) => {
              const movie = item.work;
              return (
                <div
                  key={movie.id}
                  className="bg-shelf-card border border-shelf-border rounded-xl overflow-hidden flex flex-col justify-between shadow-md hover:border-shelf-amber/50 transition"
                >
                  <Link to={`/works/${movie.id}`} className="relative aspect-[2/3] bg-slate-900 block overflow-hidden">
                    <img
                      src={getTmdbImageUrl(movie.poster_path, 'w500')}
                      alt={movie.title}
                      className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                    />
                    {movie.release_year && (
                      <span className="absolute top-2 right-2 px-2 py-0.5 rounded bg-black/80 text-shelf-amber font-mono text-[10px] font-bold border border-white/10">
                        {movie.release_year}
                      </span>
                    )}
                  </Link>

                  <div className="p-3 space-y-2.5">
                    <div>
                      <h3 className="font-bold text-xs text-white line-clamp-1">
                        {movie.persian_title || movie.title}
                      </h3>
                      <p className="text-[11px] text-slate-400 font-mono truncate" dir="ltr">
                        {movie.title}
                      </p>
                    </div>

                    <div className="flex gap-1.5">
                      <Link
                        to={`/works/${movie.id}`}
                        className="flex-1 py-1.5 rounded-lg bg-shelf-amber hover:bg-shelf-amberHover text-black font-bold text-xs flex items-center justify-center gap-1.5 transition"
                      >
                        <ArrowDownCircle className="w-3.5 h-3.5" />
                        <span>مشاهده و دانلود</span>
                      </Link>
                      <button
                        onClick={() => toggleWatchlist(movie.id, false)}
                        title="حذف از واچ‌لیست"
                        className="p-1.5 rounded-lg bg-shelf-bg hover:bg-red-950/40 text-slate-400 hover:text-red-400 border border-shelf-border transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Bottom Section: Clean 4-Column Aria2 Download Queue */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-shelf-card border border-shelf-border p-4 rounded-xl">
          <div className="flex items-center gap-2.5">
            <Download className="w-5 h-5 text-shelf-amber" />
            <div>
              <h2 className="text-base font-bold text-white">
                مدیریت صف دانلودها (Aria2 JSON-RPC)
              </h2>
              <p className="text-xs text-slate-400">
                بروزرسانی زنده سرعت، درصد پیشرفت و وضعیت فایل‌های دریافتی
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 font-mono text-xs" dir="ltr">
            <span className="px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              DL: {speedMbps} MB/s
            </span>
            <span className="px-3 py-1.5 rounded-lg bg-shelf-bg border border-shelf-border text-slate-300">
              Active: {activeCount} / Queued: {queuedCount}
            </span>
          </div>
        </div>

        {/* Downloads Loading */}
        {isLoadingDownloads && (
          <div className="py-12 flex flex-col items-center justify-center gap-2 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin text-shelf-amber" />
            <span className="text-xs">در حال دریافت وضعیت دانلودها...</span>
          </div>
        )}

        {/* Empty Downloads */}
        {!isLoadingDownloads && tasks.length === 0 && (
          <div className="p-8 text-center bg-shelf-card border border-shelf-border rounded-xl space-y-2">
            <p className="text-slate-300 text-xs font-bold">صف دانلود در حال حاضر خالی است</p>
            <p className="text-slate-500 text-[11px]">
              با رفتن به صفحه هر فیلم و کلیک روی «جستجوی لینک‌های دانلود (زرفیلم)» می‌توانید دانلود را آغاز کنید.
            </p>
          </div>
        )}

        {/* Live Tasks List */}
        {!isLoadingDownloads && tasks.length > 0 && (
          <div className="space-y-3">
            {tasks.map((task) => {
              const downloadedGb = (task.downloaded_bytes / (1024 * 1024 * 1024)).toFixed(2);
              const totalGb = task.total_bytes
                ? (task.total_bytes / (1024 * 1024 * 1024)).toFixed(2)
                : '—';
              const speedMb = (task.download_speed_bps / (1024 * 1024)).toFixed(2);
              const progressPct = task.progress_percent.toFixed(1);

              return (
                <div
                  key={task.id}
                  className="bg-shelf-card border border-shelf-border rounded-xl p-4 grid grid-cols-1 lg:grid-cols-12 gap-4 items-center shadow-md"
                >
                  {/* Col 1: Movie Title & Path (4 cols) */}
                  <div className="lg:col-span-4 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-white font-mono truncate" dir="ltr" title={task.file_name || task.download_url}>
                        {task.file_name || 'در حال دریافت نام فایل...'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400 truncate" dir="ltr">
                      <span className="text-shelf-amber font-semibold">{task.status}</span>
                      <span>•</span>
                      <span className="truncate max-w-[240px]" title={task.destination_dir}>
                        {task.destination_dir}
                      </span>
                    </div>
                  </div>

                  {/* Col 2: Progress Bar & Size (5 cols) */}
                  <div className="lg:col-span-5 space-y-1.5" dir="ltr">
                    <div className="flex justify-between text-xs font-mono">
                      <span className="text-slate-200 font-semibold">{progressPct}%</span>
                      <span className="text-slate-400">
                        {downloadedGb} GB / {totalGb} GB
                      </span>
                    </div>
                    <div className="w-full h-2 bg-shelf-bg rounded-full overflow-hidden border border-shelf-border">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          task.status === 'COMPLETED'
                            ? 'bg-emerald-500'
                            : task.status === 'PAUSED'
                            ? 'bg-amber-500'
                            : task.status === 'ERROR'
                            ? 'bg-red-500'
                            : 'bg-shelf-amber'
                        }`}
                        style={{ width: `${Math.min(100, Math.max(0, task.progress_percent))}%` }}
                      />
                    </div>
                  </div>

                  {/* Col 3: Speed & Status (2 cols) */}
                  <div className="lg:col-span-2 text-left font-mono text-xs" dir="ltr">
                    {task.status === 'ACTIVE' ? (
                      <div className="text-emerald-400 font-bold">{speedMb} MB/s</div>
                    ) : (
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                          task.status === 'COMPLETED'
                            ? 'bg-emerald-500/15 text-emerald-400'
                            : task.status === 'PAUSED'
                            ? 'bg-amber-500/15 text-amber-400'
                            : task.status === 'ERROR'
                            ? 'bg-red-500/15 text-red-400'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {task.status}
                      </span>
                    )}
                  </div>

                  {/* Col 4: Action Buttons (1 col) */}
                  <div className="lg:col-span-1 flex items-center justify-end gap-1.5">
                    {task.status === 'ACTIVE' ? (
                      <button
                        onClick={() => pauseTask(task.id)}
                        disabled={isPausing}
                        title="توقف موقت"
                        className="p-2 rounded-lg bg-shelf-bg hover:bg-slate-800 text-amber-400 border border-shelf-border transition"
                      >
                        <Pause className="w-4 h-4" />
                      </button>
                    ) : task.status === 'PAUSED' || task.status === 'QUEUED' ? (
                      <button
                        onClick={() => resumeTask(task.id)}
                        disabled={isResuming}
                        title="ادامه دانلود"
                        className="p-2 rounded-lg bg-shelf-bg hover:bg-slate-800 text-emerald-400 border border-shelf-border transition"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                    ) : null}

                    {task.destination_dir && (
                      <button
                        onClick={() => handleOpenTaskFolder(task.destination_dir)}
                        title="کپی مسیر یا باز کردن پوشه"
                        className="p-2 rounded-lg bg-shelf-bg hover:bg-slate-800 text-shelf-amber border border-shelf-border transition"
                      >
                        <FolderOpen className="w-4 h-4" />
                      </button>
                    )}

                    <button
                      onClick={() => cancelTask(task.id)}
                      disabled={isCancelling}
                      title="حذف از صف"
                      className="p-2 rounded-lg bg-shelf-bg hover:bg-red-950/50 text-red-400 border border-shelf-border transition"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Letterboxd Import Modal */}
      <LetterboxdImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
      />
    </div>
  );
};
