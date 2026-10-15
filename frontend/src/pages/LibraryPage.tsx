import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Star, HardDrive, Filter, Plus, BookmarkCheck, Film, Loader2, FolderOpen, ChevronLeft, ChevronRight } from 'lucide-react';
import { useLibraryItems } from '../hooks/useLibraryItems';
import { useLibraries } from '../hooks/useLibraries';
import { getTmdbImageUrl, LibraryItem } from '../types/api';
import { AddWorkModal } from '../components/AddWorkModal';
import { ManageLibrariesModal } from '../components/ManageLibrariesModal';

function getPageRange(current: number, total: number): number[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  const pages: number[] = [1];
  if (current > 3) pages.push(-1);
  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);
  for (let i = start; i <= end; i++) {
    pages.push(i);
  }
  if (current < total - 2) pages.push(-1);
  pages.push(total);
  return pages;
}

function getBestResolution(item: LibraryItem): string {
  const files = item.media_files || [];
  if (files.some((f) => f.resolution?.includes('2160') || f.resolution?.toLowerCase().includes('4k'))) {
    return '4K UHD';
  }
  if (files.some((f) => f.resolution?.includes('1080'))) {
    return '1080p';
  }
  if (files.some((f) => f.resolution?.includes('720'))) {
    return '720p';
  }
  if (item.status === 'WANTED') {
    return 'در انتظار دانلود';
  }
  return 'SD';
}

function isItemOnline(item: LibraryItem): boolean {
  const files = item.media_files || [];
  if (files.length === 0) return false;
  return files.some((f) => f.is_online);
}

export const LibraryPage: React.FC<{ searchQuery: string }> = ({ searchQuery }) => {
  const [selectedLibraryId, setSelectedLibraryId] = useState<number | null>(null);
  const [resolutionFilter, setResolutionFilter] = useState<string>('ALL');
  const [onlineOnly, setOnlineOnly] = useState<boolean>(false);
  const [selectedGenre, setSelectedGenre] = useState<string>('ALL');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(48);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isManageLibrariesOpen, setIsManageLibrariesOpen] = useState(false);

  // Reset to page 1 on search or filter change
  useEffect(() => {
    setPage(1);
  }, [searchQuery, selectedLibraryId, selectedGenre, resolutionFilter, onlineOnly, pageSize]);

  const { libraries } = useLibraries();

  const {
    items,
    allItems,
    allGenres,
    totalCount,
    totalPages,
    currentPage,
    isLoading,
    isError,
    error,
  } = useLibraryItems({
    libraryId: selectedLibraryId,
    search: searchQuery,
    genre: selectedGenre,
    resolution: resolutionFilter,
    onlineOnly,
    page,
    pageSize,
  });

  return (
    <div className="space-y-6">
      {/* Page Title & Clean Single-Row Filter Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-shelf-card border border-shelf-border p-4 rounded-xl">
        <div>
          <h2 className="text-xl font-bold text-white">کتابخانه اصلی فیلم‌ها</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            نمایش {items.length} اثر از {totalCount} عنوان در آرشیو شخصی شما
          </p>
        </div>

        {/* Consolidated 1-Row Filter Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Library Selector */}
          {libraries.length > 0 && (
            <select
              value={selectedLibraryId === null ? 'ALL' : selectedLibraryId}
              onChange={(e) =>
                setSelectedLibraryId(e.target.value === 'ALL' ? null : Number(e.target.value))
              }
              className="bg-shelf-bg border border-shelf-border rounded-lg px-3 py-1.5 text-xs text-shelf-amber font-medium focus:outline-none focus:border-shelf-amber"
            >
              <option value="ALL">همه کتابخانه‌ها ({libraries.length})</option>
              {libraries.map((lib) => (
                <option key={lib.id} value={lib.id}>
                  {lib.name}
                </option>
              ))}
            </select>
          )}

          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5 text-shelf-amber" />
            <span>فیلتر:</span>
          </div>

          <select
            value={selectedGenre}
            onChange={(e) => setSelectedGenre(e.target.value)}
            className="bg-shelf-bg border border-shelf-border rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-shelf-amber"
          >
            <option value="ALL">همه ژانرها</option>
            {allGenres.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>

          <select
            value={resolutionFilter}
            onChange={(e) => setResolutionFilter(e.target.value)}
            className="bg-shelf-bg border border-shelf-border rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-shelf-amber"
          >
            <option value="ALL">همه کیفیت‌ها</option>
            <option value="4K">4K UHD</option>
            <option value="1080p">1080p</option>
            <option value="720p">720p</option>
          </select>

          <button
            onClick={() => setOnlineOnly(!onlineOnly)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border flex items-center gap-1.5 transition ${
              onlineOnly
                ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
                : 'bg-shelf-bg border-shelf-border text-slate-300 hover:border-slate-600'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                onlineOnly ? 'bg-emerald-400' : 'bg-slate-500'
              }`}
            />
            فقط هاردهای متصل
          </button>

          <button
            onClick={() => setIsManageLibrariesOpen(true)}
            className="p-1.5 rounded-lg bg-shelf-bg border border-shelf-border text-slate-300 hover:text-white hover:border-slate-600 transition"
            title="مدیریت ریشه‌ها و اسکن هارد"
          >
            <FolderOpen className="w-4 h-4 text-shelf-amber" />
          </button>
        </div>
      </div>

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-5">
          {Array.from({ length: 10 }).map((_, i) => (
            <div
              key={i}
              className="bg-shelf-card border border-shelf-border rounded-xl overflow-hidden animate-pulse flex flex-col"
            >
              <div className="aspect-[2/3] bg-slate-800" />
              <div className="p-3.5 space-y-2">
                <div className="h-4 bg-slate-800 rounded w-3/4" />
                <div className="h-3 bg-slate-800/60 rounded w-1/2" />
                <div className="h-3 bg-slate-800/40 rounded w-1/3" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {isError && (
        <div className="p-8 text-center bg-red-500/10 border border-red-500/30 rounded-2xl space-y-2">
          <p className="text-red-400 text-sm font-bold">خطا در دریافت لیست فیلم‌ها</p>
          <p className="text-slate-400 text-xs">{(error as any)?.message || 'سرور پاسخ نمی‌دهد'}</p>
        </div>
      )}

      {/* Empty State: Completely Empty Library */}
      {!isLoading && !isError && allItems.length === 0 && (
        <div className="p-12 text-center bg-shelf-card border border-shelf-border rounded-2xl space-y-4 max-w-lg mx-auto">
          <div className="w-16 h-16 rounded-2xl bg-shelf-amber/15 text-shelf-amber mx-auto flex items-center justify-center">
            <Film className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">هنوز اثری در کتابخانه ثبت نشده است</h3>
            <p className="text-xs text-slate-400 mt-1">
              می‌توانید با افزودن پوشه هارددیسک و اسکن خودکار، یا با جستجوی عنوان در TMDB اثر دلخواه خود را بیفزایید.
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-3 pt-2">
            <button
              onClick={() => setIsManageLibrariesOpen(true)}
              className="px-4 py-2 rounded-lg bg-shelf-amber hover:bg-shelf-amberHover text-black font-bold text-xs flex items-center gap-1.5 shadow-md shadow-shelf-amber/10 transition"
            >
              <FolderOpen className="w-4 h-4" />
              <span>افزودن پوشه و اسکن آرشیو</span>
            </button>
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-medium text-xs flex items-center gap-1.5 border border-shelf-border transition"
            >
              <Plus className="w-4 h-4" />
              <span>جستجو و افزودن از TMDB</span>
            </button>
            <Link
              to="/watchlist"
              className="px-4 py-2 rounded-lg bg-shelf-bg border border-shelf-border text-slate-300 hover:text-white text-xs flex items-center gap-1.5 transition"
            >
              <BookmarkCheck className="w-4 h-4" />
              <span>مرکز دانلودها و Letterboxd</span>
            </Link>
          </div>
        </div>
      )}

      {/* Empty State: Filter Matched Nothing */}
      {!isLoading && !isError && allItems.length > 0 && items.length === 0 && (
        <div className="p-12 text-center bg-shelf-card border border-shelf-border rounded-2xl space-y-3">
          <p className="text-sm text-slate-300 font-bold">فیلمی با فیلترهای انتخابی شما پیدا نشد</p>
          <button
            onClick={() => {
              setSelectedGenre('ALL');
              setResolutionFilter('ALL');
              setOnlineOnly(false);
            }}
            className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 transition"
          >
            پاک کردن تمام فیلترها
          </button>
        </div>
      )}

      {/* Movie Cards Grid */}
      {!isLoading && items.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-5">
          {items.map((item) => {
            const movie = item.work;
            const bestRes = getBestResolution(item);
            const isOnline = isItemOnline(item);
            const userRating = item.personal_record?.user_rating;
            const displayRating = userRating || movie.imdb_rating || movie.tmdb_rating;

            return (
              <Link
                to={`/works/${movie.id}`}
                key={item.id}
                className="group bg-shelf-card border border-shelf-border rounded-xl overflow-hidden hover:border-shelf-amber/60 transition-all duration-200 flex flex-col shadow-lg"
              >
                {/* Poster Container */}
                <div className="relative aspect-[2/3] bg-slate-900 overflow-hidden">
                  <img
                    src={getTmdbImageUrl(movie.poster_path, 'w500')}
                    alt={movie.title}
                    loading="lazy"
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />

                  {/* Top-Right Badge: Best Resolution */}
                  <span className="absolute top-2.5 right-2.5 px-2 py-0.5 rounded-md bg-black/80 backdrop-blur-md text-shelf-amber font-mono text-[11px] font-bold border border-white/10">
                    {bestRes}
                  </span>

                  {/* Top-Left Badge: Drive Online / Offline Status */}
                  <span
                    className={`absolute top-2.5 left-2.5 px-2 py-0.5 rounded-md text-[10px] font-medium backdrop-blur-md flex items-center gap-1 border ${
                      isOnline
                        ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500/30'
                        : 'bg-red-950/80 text-red-300 border-red-500/30'
                    }`}
                  >
                    <HardDrive className="w-3 h-3" />
                    <span>{isOnline ? 'آماده پخش' : 'آرشیو آفلاین'}</span>
                  </span>

                  {/* Gradient Overlay for bottom text legibility */}
                  <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/90 via-black/40 to-transparent pointer-events-none" />

                  {/* Bottom details on poster */}
                  <div className="absolute bottom-2.5 inset-x-2.5 flex items-center justify-between text-xs text-white">
                    <span className="font-mono text-slate-300 text-[11px]">
                      {movie.release_year || '—'}
                    </span>
                    {displayRating && (
                      <span className="flex items-center gap-1 bg-black/60 px-1.5 py-0.5 rounded font-mono text-amber-400 text-xs">
                        <Star className="w-3 h-3 fill-amber-400" />
                        {displayRating}
                      </span>
                    )}
                  </div>
                </div>

                {/* Card Meta Content */}
                <div className="p-3.5 flex-1 flex flex-col justify-between space-y-2">
                  <div>
                    <h3 className="font-bold text-sm text-white group-hover:text-shelf-amber transition line-clamp-1">
                      {movie.persian_title || movie.title}
                    </h3>
                    {movie.persian_title && (
                      <p className="text-xs text-slate-400 font-mono line-clamp-1 mt-0.5" dir="ltr">
                        {movie.title}
                      </p>
                    )}
                  </div>

                  {/* Genres */}
                  <div className="flex flex-wrap gap-1 pt-1">
                    {(movie.genres || []).slice(0, 2).map((g) => (
                      <span
                        key={g.id}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400"
                      >
                        {g.persian_name || g.name}
                      </span>
                    ))}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* Pagination Bar */}
      {totalPages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 bg-shelf-card border border-shelf-border rounded-xl">
          <div className="text-xs text-slate-400">
            صفحه <span className="text-white font-bold">{page}</span> از <span className="text-white font-bold">{totalPages}</span> (نمایش {(page - 1) * pageSize + 1} تا {Math.min(page * pageSize, totalCount)} از {totalCount} اثر)
          </div>

          <div className="flex items-center gap-1.5" dir="ltr">
            <button
              onClick={() => {
                setPage((p) => Math.max(1, p - 1));
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              disabled={page <= 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-shelf-border bg-slate-800 text-xs text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-700 transition"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>قبلی</span>
            </button>

            {getPageRange(page, totalPages).map((p, idx) =>
              p === -1 ? (
                <span key={`dots-${idx}`} className="px-1.5 text-slate-500 text-xs font-mono">
                  ...
                </span>
              ) : (
                <button
                  key={p}
                  onClick={() => {
                    setPage(p);
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  className={`min-w-[32px] h-8 rounded-lg text-xs font-bold transition border ${
                    page === p
                      ? 'bg-shelf-amber text-black border-shelf-amber shadow-sm'
                      : 'bg-slate-900/60 text-slate-300 border-shelf-border hover:bg-slate-800'
                  }`}
                >
                  {p}
                </button>
              )
            )}

            <button
              onClick={() => {
                setPage((p) => Math.min(totalPages, p + 1));
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              disabled={page >= totalPages}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-shelf-border bg-slate-800 text-xs text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-700 transition"
            >
              <span>بعدی</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>تعداد در صفحه:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              className="bg-slate-900 border border-shelf-border text-white rounded-lg px-2.5 py-1 text-xs outline-none focus:border-shelf-amber"
            >
              <option value={24}>۲۴ اثر</option>
              <option value={48}>۴۸ اثر</option>
              <option value={96}>۹۶ اثر</option>
              <option value={500}>همه اثرها</option>
            </select>
          </div>
        </div>
      )}

      {/* Manage Libraries Modal */}
      <ManageLibrariesModal
        isOpen={isManageLibrariesOpen}
        onClose={() => setIsManageLibrariesOpen(false)}
      />

      {/* Add Work Modal */}
      <AddWorkModal isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)} />
    </div>
  );
};
