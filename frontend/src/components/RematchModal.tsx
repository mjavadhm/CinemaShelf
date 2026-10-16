import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Search, RefreshCw, X, Loader2, Film, Tv, Star, AlertCircle, CheckCircle2 } from 'lucide-react';
import { searchMetadata, rematchByWorkId, rematchLibraryItem } from '../api/endpoints';
import { ExternalSearchResult, WorkType, getTmdbImageUrl } from '../types/api';

interface RematchModalProps {
  isOpen: boolean;
  onClose: () => void;
  workId: number;
  libraryItemId?: number;
  currentTitle: string;
  currentYear?: number | null;
  mediaFilesCount?: number;
}

export const RematchModal: React.FC<RematchModalProps> = ({
  isOpen,
  onClose,
  workId,
  libraryItemId,
  currentTitle,
  currentYear,
  mediaFilesCount = 0,
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState(currentTitle || '');
  const [searchYear, setSearchYear] = useState<string>(currentYear ? String(currentYear) : '');
  const [workType, setWorkType] = useState<WorkType>('MOVIE');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<ExternalSearchResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedResult, setSelectedResult] = useState<ExternalSearchResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = searchQuery.trim();
    if (!query) return;

    try {
      setIsSearching(true);
      setErrorMessage(null);
      const parsedYear = searchYear ? parseInt(searchYear, 10) : undefined;
      const results = await searchMetadata(query, isNaN(parsedYear as number) ? undefined : parsedYear, workType);
      setSearchResults(results);
      setHasSearched(true);
    } catch (err: any) {
      setErrorMessage(
        err.response?.data?.error?.message ||
        err.message ||
        'خطا در جستجوی فیلم در پایگاه داده TMDB'
      );
    } finally {
      setIsSearching(false);
    }
  };

  const handleConfirmRematch = async (result: ExternalSearchResult) => {
    try {
      setSelectedResult(result);
      setIsSubmitting(true);
      setErrorMessage(null);

      let updatedItem;
      if (libraryItemId) {
        updatedItem = await rematchLibraryItem(libraryItemId, result.tmdb_id, workType);
      } else {
        updatedItem = await rematchByWorkId(workId, result.tmdb_id, workType);
      }

      setSuccessMessage(`فایل‌ها با موفقیت به فیلم «${result.title}» منتقل شدند.`);

      // Invalidate queries so that library and work details update immediately
      await queryClient.invalidateQueries({ queryKey: ['work-details'] });
      await queryClient.invalidateQueries({ queryKey: ['library-items'] });
      await queryClient.invalidateQueries({ queryKey: ['library-item-by-work'] });
      await queryClient.invalidateQueries({ queryKey: ['watchlist-works'] });
      await queryClient.invalidateQueries({ queryKey: ['personal-record'] });

      // Navigate to the target work page after short delay for user feedback
      setTimeout(() => {
        onClose();
        if (updatedItem.work_id) {
          navigate(`/movie/${updatedItem.work_id}`);
        }
      }, 1200);
    } catch (err: any) {
      setErrorMessage(
        err.response?.data?.error?.message ||
        err.message ||
        'خطا در انجام عملیات تصحیح تطابق فیلم'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="bg-shelf-card border border-shelf-border rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-shelf-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-shelf-amber/20 flex items-center justify-center text-shelf-amber">
              <RefreshCw className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">تصحیح تطابق فیلم با فایل‌ها (Rematch)</h2>
              <p className="text-[11px] text-slate-400">
                اگر فایل‌ها به اشتباه شناسایی شده‌اند، فیلم صحیح را از TMDB جستجو و انتخاب کنید
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="w-8 h-8 rounded-lg hover:bg-slate-800 flex items-center justify-center text-slate-400 hover:text-white transition disabled:opacity-40"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Current Movie Context Banner */}
        <div className="p-3 bg-shelf-bg/70 border-b border-shelf-border/80 text-xs flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-slate-300 truncate">
            <span className="text-slate-500 shrink-0">عنوان فعلی:</span>
            <span className="font-bold text-white truncate" dir="ltr">{currentTitle}</span>
            {currentYear ? <span className="text-slate-400 font-mono">({currentYear})</span> : null}
          </div>
          <div className="text-[11px] text-shelf-amber shrink-0 font-medium">
            تعداد فایل‌های انتقالی: <strong className="font-mono">{mediaFilesCount}</strong> فایل
          </div>
        </div>

        {/* Search Controls */}
        <form onSubmit={handleSearch} className="p-4 border-b border-shelf-border/60 bg-shelf-bg/40 space-y-3">
          <div className="flex flex-wrap sm:flex-nowrap items-center gap-2">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="w-4 h-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoFocus
                placeholder="نام صحیح فیلم یا سریال به انگلیسی یا فارسی..."
                className="w-full bg-shelf-card border border-shelf-border rounded-xl pr-10 pl-4 py-2 text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-shelf-amber"
              />
            </div>

            <div className="w-24 shrink-0">
              <input
                type="text"
                value={searchYear}
                onChange={(e) => setSearchYear(e.target.value)}
                placeholder="سال (اختیاری)"
                dir="ltr"
                className="w-full bg-shelf-card border border-shelf-border rounded-xl px-3 py-2 text-xs sm:text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-shelf-amber text-center font-mono"
              />
            </div>

            <div className="flex bg-shelf-card border border-shelf-border rounded-xl p-1 shrink-0">
              <button
                type="button"
                onClick={() => setWorkType('MOVIE')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition ${
                  workType === 'MOVIE'
                    ? 'bg-shelf-amber text-black font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Film className="w-3.5 h-3.5" />
                <span>فیلم</span>
              </button>
              <button
                type="button"
                onClick={() => setWorkType('SHOW')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition ${
                  workType === 'SHOW'
                    ? 'bg-shelf-amber text-black font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Tv className="w-3.5 h-3.5" />
                <span>سریال</span>
              </button>
            </div>

            <button
              type="submit"
              disabled={isSearching || !searchQuery.trim()}
              className="px-4 py-2 rounded-xl bg-shelf-amber hover:bg-shelf-amberHover text-black text-xs font-bold flex items-center gap-1.5 transition disabled:opacity-50 shrink-0"
            >
              {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              <span>جستجو</span>
            </button>
          </div>
        </form>

        {/* Results Body */}
        <div className="p-4 overflow-y-auto flex-1 space-y-3">
          {errorMessage && (
            <div className="p-3 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          {isSearching && (
            <div className="py-12 flex flex-col items-center justify-center gap-2 text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin text-shelf-amber" />
              <span className="text-xs">در حال جستجو در پایگاه داده TMDB...</span>
            </div>
          )}

          {!isSearching && hasSearched && searchResults.length === 0 && (
            <div className="py-12 text-center text-slate-400 text-xs">
              نتیجه‌ای برای <strong className="text-slate-200">«{searchQuery}»</strong> یافت نشد.
            </div>
          )}

          {!isSearching && !hasSearched && (
            <div className="py-12 text-center text-slate-500 text-xs space-y-1">
              <p>نام صحیح فیلم را جستجو کنید تا فهرست عناوین منطبق از TMDB نمایش داده شود.</p>
              <p className="text-[11px] text-slate-600">
                پس از انتخاب، تمام فایل‌های ویدیویی به فیلم جدید پیوند داده می‌شوند.
              </p>
            </div>
          )}

          {!isSearching &&
            searchResults.map((result) => {
              const isSelected = selectedResult?.tmdb_id === result.tmdb_id && isSubmitting;
              return (
                <div
                  key={result.tmdb_id}
                  className="bg-shelf-bg/70 border border-shelf-border rounded-xl p-3 flex gap-3 hover:border-shelf-border/90 transition"
                >
                  <img
                    src={getTmdbImageUrl(result.poster_path, 'w185')}
                    alt={result.title}
                    className="w-16 h-24 rounded-lg object-cover bg-slate-900 border border-white/5 shrink-0"
                  />

                  <div className="flex-1 flex flex-col justify-between min-w-0">
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="text-sm font-bold text-white truncate" dir="ltr">
                          {result.title}
                        </h3>
                        {result.vote_average ? (
                          <div className="flex items-center gap-1 text-[11px] font-mono font-bold text-amber-400 shrink-0">
                            <Star className="w-3 h-3 fill-amber-400" />
                            <span>{result.vote_average.toFixed(1)}</span>
                          </div>
                        ) : null}
                      </div>

                      <div className="text-xs text-slate-400 font-mono mt-0.5" dir="ltr">
                        {result.release_year || 'نامشخص'} • TMDB ID: {result.tmdb_id}
                      </div>

                      {result.overview && (
                        <p className="text-xs text-slate-300 mt-1.5 line-clamp-2 leading-relaxed" dir="auto">
                          {result.overview}
                        </p>
                      )}
                    </div>

                    <div className="pt-2 flex items-center justify-end">
                      <button
                        type="button"
                        onClick={() => handleConfirmRematch(result)}
                        disabled={isSubmitting}
                        className="px-3.5 py-1.5 rounded-lg bg-shelf-amber hover:bg-shelf-amberHover text-black text-xs font-bold flex items-center gap-1.5 shadow transition disabled:opacity-50"
                      >
                        {isSelected ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            <span>در حال انتقال فایل‌ها...</span>
                          </>
                        ) : (
                          <>
                            <RefreshCw className="w-3.5 h-3.5" />
                            <span>انتخاب و انتقال فایل‌ها به این فیلم</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-shelf-border flex items-center justify-between text-xs text-slate-500">
          <span>داده‌ها مستقیماً از TMDb فراخوانی می‌شوند</span>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white transition disabled:opacity-40"
          >
            انصراف
          </button>
        </div>
      </div>
    </div>
  );
};
