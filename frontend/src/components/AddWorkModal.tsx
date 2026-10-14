import React, { useState } from 'react';
import { Search, Plus, Bookmark, Check, Loader2, X, Film, Tv, Star } from 'lucide-react';
import { useSearchAndAddWork } from '../hooks/useSearchAndAddWork';
import { getTmdbImageUrl, WorkType } from '../types/api';

interface AddWorkModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AddWorkModal: React.FC<AddWorkModalProps> = ({ isOpen, onClose }) => {
  const {
    queryText,
    setQueryText,
    selectedType,
    setSelectedType,
    searchResults,
    isSearching,
    addToLibrary,
    addToWatchlist,
  } = useSearchAndAddWork();

  const [addedLibraryIds, setAddedLibraryIds] = useState<Set<number>>(new Set());
  const [addedWatchlistIds, setAddedWatchlistIds] = useState<Set<number>>(new Set());
  const [loadingActionId, setLoadingActionId] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAddToLibrary = async (tmdbId: number) => {
    try {
      setLoadingActionId(`lib-${tmdbId}`);
      await addToLibrary(tmdbId);
      setAddedLibraryIds((prev) => new Set(prev).add(tmdbId));
    } catch (err) {
      console.error('Failed to add to library:', err);
    } finally {
      setLoadingActionId(null);
    }
  };

  const handleAddToWatchlist = async (tmdbId: number) => {
    try {
      setLoadingActionId(`wl-${tmdbId}`);
      await addToWatchlist(tmdbId);
      setAddedWatchlistIds((prev) => new Set(prev).add(tmdbId));
    } catch (err) {
      console.error('Failed to add to watchlist:', err);
    } finally {
      setLoadingActionId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="bg-shelf-card border border-shelf-border rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="p-4 border-b border-shelf-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-shelf-amber/20 flex items-center justify-center text-shelf-amber">
              <Search className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">جستجو و افزودن فیلم از TMDB</h2>
              <p className="text-[11px] text-slate-400">
                عنوان فیلم یا سریال را جستجو کرده و به کتابخانه یا واچ‌لیست خود اضافه کنید
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-slate-800 flex items-center justify-center text-slate-400 hover:text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search Controls */}
        <div className="p-4 border-b border-shelf-border/60 bg-shelf-bg/50 space-y-3">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={queryText}
                onChange={(e) => setQueryText(e.target.value)}
                autoFocus
                placeholder="نام انگلیسی یا فارسی اثر (مثلاً: Dune, Oppenheimer, Interstellar)..."
                className="w-full bg-shelf-card border border-shelf-border rounded-xl pr-10 pl-4 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-shelf-amber"
              />
            </div>

            {/* Type selector */}
            <div className="flex bg-shelf-card border border-shelf-border rounded-xl p-1 shrink-0">
              <button
                type="button"
                onClick={() => setSelectedType('MOVIE')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition ${
                  selectedType === 'MOVIE'
                    ? 'bg-shelf-amber text-black font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Film className="w-3.5 h-3.5" />
                <span>فیلم</span>
              </button>
              <button
                type="button"
                onClick={() => setSelectedType('SHOW')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium transition ${
                  selectedType === 'SHOW'
                    ? 'bg-shelf-amber text-black font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Tv className="w-3.5 h-3.5" />
                <span>سریال</span>
              </button>
            </div>
          </div>
        </div>

        {/* Results List */}
        <div className="p-4 overflow-y-auto flex-1 space-y-3">
          {isSearching && (
            <div className="py-12 flex flex-col items-center justify-center gap-2 text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin text-shelf-amber" />
              <span className="text-xs">در حال جستجو در پایگاه داده TMDB...</span>
            </div>
          )}

          {!isSearching && queryText.trim().length >= 2 && searchResults.length === 0 && (
            <div className="py-12 text-center text-slate-400 text-xs">
              نتیجه‌ای برای <strong className="text-slate-200">«{queryText}»</strong> یافت نشد.
            </div>
          )}

          {!isSearching && queryText.trim().length < 2 && (
            <div className="py-12 text-center text-slate-500 text-xs">
              حداقل دو حرف برای جستجو تایپ کنید.
            </div>
          )}

          {!isSearching &&
            searchResults.map((result) => {
              const inLib = addedLibraryIds.has(result.tmdb_id);
              const inWl = addedWatchlistIds.has(result.tmdb_id);
              const isLibLoading = loadingActionId === `lib-${result.tmdb_id}`;
              const isWlLoading = loadingActionId === `wl-${result.tmdb_id}`;

              return (
                <div
                  key={result.tmdb_id}
                  className="p-3 rounded-xl bg-shelf-bg/70 border border-shelf-border/80 flex gap-3.5 items-center hover:border-slate-600 transition"
                >
                  <img
                    src={getTmdbImageUrl(result.poster_path, 'w185')}
                    alt={result.title}
                    className="w-14 h-20 rounded-lg object-cover bg-slate-800 shrink-0 border border-white/5"
                  />

                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-white truncate">{result.title}</h3>
                      {result.release_year && (
                        <span className="text-xs text-slate-400 font-mono">
                          ({result.release_year})
                        </span>
                      )}
                    </div>

                    {result.original_title && result.original_title !== result.title && (
                      <p className="text-[11px] text-slate-400 font-mono truncate" dir="ltr">
                        {result.original_title}
                      </p>
                    )}

                    <div className="flex items-center gap-3 text-[11px] text-slate-400">
                      {result.vote_average && (
                        <span className="flex items-center gap-1 text-amber-400 font-mono">
                          <Star className="w-3 h-3 fill-amber-400" />
                          {result.vote_average.toFixed(1)}
                        </span>
                      )}
                      <span className="text-slate-500">•</span>
                      <span className="font-mono text-[10px] text-slate-400">
                        TMDB: {result.tmdb_id}
                      </span>
                    </div>

                    {result.overview && (
                      <p className="text-[11px] text-slate-400 line-clamp-2 mt-1">
                        {result.overview}
                      </p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col gap-2 shrink-0">
                    <button
                      onClick={() => handleAddToLibrary(result.tmdb_id)}
                      disabled={inLib || isLibLoading}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition ${
                        inLib
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-shelf-amber hover:bg-shelf-amberHover text-black font-bold shadow-md shadow-shelf-amber/10'
                      }`}
                    >
                      {isLibLoading ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : inLib ? (
                        <Check className="w-3.5 h-3.5" />
                      ) : (
                        <Plus className="w-3.5 h-3.5" />
                      )}
                      <span>{inLib ? 'در کتابخانه' : 'افزودن به آرشیو'}</span>
                    </button>

                    <button
                      onClick={() => handleAddToWatchlist(result.tmdb_id)}
                      disabled={inWl || isWlLoading}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition border ${
                        inWl
                          ? 'bg-purple-500/20 text-purple-300 border-purple-500/30'
                          : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700'
                      }`}
                    >
                      {isWlLoading ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : inWl ? (
                        <Check className="w-3.5 h-3.5" />
                      ) : (
                        <Bookmark className="w-3.5 h-3.5" />
                      )}
                      <span>{inWl ? 'در واچ‌لیست' : 'واچ‌لیست'}</span>
                    </button>
                  </div>
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
};
