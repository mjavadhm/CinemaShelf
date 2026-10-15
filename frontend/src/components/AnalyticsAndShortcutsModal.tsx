import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BarChart2,
  FolderTree,
  X,
  Loader2,
  Sparkles,
  Star,
  Film,
  HardDrive,
  Calendar,
  User,
  CheckCircle2,
  AlertCircle,
  FolderOpen,
} from 'lucide-react';
import { getLibraryStats, categorizeLibrary } from '../api/endpoints';
import { CategorizeRequest, LibraryStatsResponse } from '../types/api';
import { FolderBrowserModal } from './FolderBrowserModal';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  selectedLibraryId?: number | null;
}

export const AnalyticsAndShortcutsModal: React.FC<Props> = ({
  isOpen,
  onClose,
  selectedLibraryId,
}) => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'stats' | 'categorize'>('stats');

  // Categorize form state
  const [destPath, setDestPath] = useState('');
  const [byDirector, setByDirector] = useState(true);
  const [byRating, setByRating] = useState(true);
  const [byDecade, setByDecade] = useState(true);
  const [directorMinCount, setDirectorMinCount] = useState(2);
  const [isBrowserOpen, setIsBrowserOpen] = useState(false);
  const [categorizeResult, setCategorizeResult] = useState<string | null>(null);

  const { data: stats, isLoading, isError, refetch } = useQuery<LibraryStatsResponse>({
    queryKey: ['libraryStats', selectedLibraryId],
    queryFn: () => getLibraryStats(selectedLibraryId || undefined),
    enabled: isOpen,
  });

  const categorizeMutation = useMutation({
    mutationFn: (req: CategorizeRequest) => categorizeLibrary(req),
    onSuccess: (res) => {
      setCategorizeResult(
        `با موفقیت ${res.shortcuts_created} میانبر در دسته‌های (${res.categories.join(
          '، '
        )}) در مسیر «${res.destination_path}» ایجاد شد.`
      );
    },
    onError: (err: any) => {
      setCategorizeResult(
        `خطا در ایجاد دسته‌بندی: ${err.response?.data?.error?.message || err.message}`
      );
    },
  });

  if (!isOpen) return null;

  const formatBytes = (bytes: number) => {
    if (!bytes) return '۰ گیگابایت';
    const gb = bytes / (1024 * 1024 * 1024);
    if (gb > 1024) {
      return `${(gb / 1024).toFixed(2)} ترابایت`;
    }
    return `${gb.toFixed(1)} گیگابایت`;
  };

  const handleStartCategorize = (e: React.FormEvent) => {
    e.preventDefault();
    if (!destPath.trim()) return;
    setCategorizeResult(null);
    categorizeMutation.mutate({
      library_id: selectedLibraryId || undefined,
      destination_dir: destPath.trim(),
      by_director: byDirector,
      by_rating: byRating,
      by_decade: byDecade,
      director_min_count: directorMinCount,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in" dir="rtl">
      <div className="bg-shelf-card border border-shelf-border rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[88vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-shelf-border flex items-center justify-between bg-shelf-bg/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-shelf-amber">
              <BarChart2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">آنالیز هوشمند و دسته‌بندی میانبرها</h2>
              <p className="text-xs text-slate-400">
                مشاهدهٔ آمار کارگردانان، دهه‌ها، کیفیت‌ها و ایجاد پوشه‌های ساختاریافته مجازی بدون تغییر فایل‌های اصلی
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800/80 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-shelf-border bg-slate-900/60 px-6">
          <button
            onClick={() => setActiveTab('stats')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition ${
              activeTab === 'stats'
                ? 'border-shelf-amber text-shelf-amber'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <BarChart2 className="w-4 h-4" />
            آمار و توزیع فیلم‌ها
          </button>
          <button
            onClick={() => setActiveTab('categorize')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition ${
              activeTab === 'categorize'
                ? 'border-shelf-amber text-shelf-amber'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FolderTree className="w-4 h-4" />
            دسته‌بندی مجازی با میانبر (Symlink / .lnk)
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm">
          {activeTab === 'stats' && (
            <>
              {isLoading && (
                <div className="flex flex-col items-center justify-center py-16 gap-3 text-slate-400">
                  <Loader2 className="w-8 h-8 animate-spin text-shelf-amber" />
                  <span>در حال محاسبه آمار کتابخانه...</span>
                </div>
              )}

              {isError && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-3">
                  <AlertCircle className="w-5 h-5 shrink-0" />
                  <span>خطا در دریافت آمار کتابخانه. لطفاً مجدداً تلاش کنید.</span>
                </div>
              )}

              {stats && (
                <div className="space-y-6">
                  {/* Metric Cards Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3.5 rounded-xl bg-slate-900/60 border border-shelf-border space-y-1">
                      <div className="flex items-center gap-2 text-slate-400 text-xs">
                        <Film className="w-3.5 h-3.5 text-shelf-amber" />
                        <span>تعداد فیلم‌ها</span>
                      </div>
                      <div className="text-xl font-bold font-mono text-white">
                        {stats.total_movies.toLocaleString('fa-IR')}
                      </div>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-900/60 border border-shelf-border space-y-1">
                      <div className="flex items-center gap-2 text-slate-400 text-xs">
                        <HardDrive className="w-3.5 h-3.5 text-blue-400" />
                        <span>حجم کل آرشیو</span>
                      </div>
                      <div className="text-xl font-bold text-white">
                        {formatBytes(stats.total_size_bytes)}
                      </div>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-900/60 border border-shelf-border space-y-1">
                      <div className="flex items-center gap-2 text-slate-400 text-xs">
                        <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                        <span>میانگین امتیاز IMDb</span>
                      </div>
                      <div className="text-xl font-bold font-mono text-white">
                        {stats.average_rating > 0 ? stats.average_rating.toFixed(1) : '-'}
                      </div>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-900/60 border border-shelf-border space-y-1">
                      <div className="flex items-center gap-2 text-slate-400 text-xs">
                        <Calendar className="w-3.5 h-3.5 text-emerald-400" />
                        <span>بازهٔ زمانی آرشیو</span>
                      </div>
                      <div className="text-xs font-mono font-medium text-slate-200 mt-1 truncate">
                        {stats.oldest_movie ? `${stats.oldest_movie.release_year}` : '-'} تا{' '}
                        {stats.newest_movie ? `${stats.newest_movie.release_year}` : '-'}
                      </div>
                    </div>
                  </div>

                  {/* Top Directors */}
                  <div className="p-4 rounded-xl bg-slate-900/50 border border-shelf-border space-y-3">
                    <h3 className="text-xs font-bold text-slate-300 flex items-center gap-2">
                      <User className="w-4 h-4 text-shelf-amber" />
                      کارگردانان برتر در آرشیو
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {stats.top_directors.length === 0 && (
                        <span className="text-xs text-slate-500">اطلاعات کارگردانی موجود نیست</span>
                      )}
                      {stats.top_directors.map((d, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between p-2 rounded-lg bg-slate-800/50 text-xs"
                        >
                          <span className="font-medium text-slate-200">{d.name}</span>
                          <span className="font-mono text-shelf-amber px-2 py-0.5 rounded-full bg-shelf-amber/10 text-[11px]">
                            {d.count} اثر
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Decades Distribution */}
                  <div className="p-4 rounded-xl bg-slate-900/50 border border-shelf-border space-y-3">
                    <h3 className="text-xs font-bold text-slate-300 flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-emerald-400" />
                      توزیع بر اساس دهه‌ها
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(stats.decade_distribution).map(([decade, count]) => (
                        <div
                          key={decade}
                          className="px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/60 flex items-center gap-2 text-xs"
                        >
                          <span className="text-slate-300">{decade}</span>
                          <span className="text-emerald-400 font-mono font-bold">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Genre Distribution */}
                  <div className="p-4 rounded-xl bg-slate-900/50 border border-shelf-border space-y-3">
                    <h3 className="text-xs font-bold text-slate-300 flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-purple-400" />
                      ژانرهای غالب
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(stats.genre_distribution).map(([genre, count]) => (
                        <span
                          key={genre}
                          className="px-2.5 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-xs"
                        >
                          {genre} ({count})
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {activeTab === 'categorize' && (
            <form onSubmit={handleStartCategorize} className="space-y-5">
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 leading-relaxed">
                این عملیات با ایجاد میانبرهای مجازی (Symlink در لینوکس یا فایل‌های LNK در ویندوز)، بدون جابجایی
                یا حذف فایل‌های اصلی، آرشیو شما را بر اساس کارگردان، امتیاز و دهه در یک پوشهٔ دلخواه طبقه‌بندی می‌کند.
              </div>

              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300">
                  مسیر پوشه مقصد برای ایجاد دسته‌بندی‌های مجازی:
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={destPath}
                    onChange={(e) => setDestPath(e.target.value)}
                    placeholder="مثال: /home/user/Movies_Categorized یا D:\Cinema_Shortcuts"
                    className="flex-1 bg-slate-900/80 border border-shelf-border rounded-lg px-3 py-2 text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-shelf-amber"
                    dir="ltr"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setIsBrowserOpen(true)}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg flex items-center gap-1.5 transition shrink-0"
                  >
                    <FolderOpen className="w-4 h-4" />
                    انتخاب پوشه
                  </button>
                </div>
              </div>

              <div className="space-y-3 border-t border-shelf-border pt-4">
                <span className="text-xs font-bold text-slate-300 block">دسته‌بندی‌های مدنظر:</span>
                <div className="space-y-2.5">
                  <label className="flex items-center gap-2.5 cursor-pointer text-xs text-slate-300">
                    <input
                      type="checkbox"
                      checked={byDirector}
                      onChange={(e) => setByDirector(e.target.checked)}
                      className="rounded bg-slate-900 border-shelf-border text-shelf-amber focus:ring-0 w-4 h-4"
                    />
                    <span>بر اساس کارگردان (به همراه حداقل تعداد اثر)</span>
                  </label>

                  {byDirector && (
                    <div className="mr-6 flex items-center gap-2 text-xs text-slate-400">
                      <span>حداقل تعداد فیلم کارگردان برای ساخت پوشه اختصاصی:</span>
                      <input
                        type="number"
                        min={1}
                        max={20}
                        value={directorMinCount}
                        onChange={(e) => setDirectorMinCount(parseInt(e.target.value) || 2)}
                        className="w-16 bg-slate-900 border border-shelf-border rounded px-2 py-1 text-center font-mono text-white"
                      />
                    </div>
                  )}

                  <label className="flex items-center gap-2.5 cursor-pointer text-xs text-slate-300">
                    <input
                      type="checkbox"
                      checked={byRating}
                      onChange={(e) => setByRating(e.target.checked)}
                      className="rounded bg-slate-900 border-shelf-border text-shelf-amber focus:ring-0 w-4 h-4"
                    />
                    <span>بر اساس بازه‌های امتیاز (Masterpiece +8.5، Great 8.0-8.4، و ...)</span>
                  </label>

                  <label className="flex items-center gap-2.5 cursor-pointer text-xs text-slate-300">
                    <input
                      type="checkbox"
                      checked={byDecade}
                      onChange={(e) => setByDecade(e.target.checked)}
                      className="rounded bg-slate-900 border-shelf-border text-shelf-amber focus:ring-0 w-4 h-4"
                    />
                    <span>بر اساس دهه‌های ساخت (1970s, 1980s, 1990s, 2000s, ...)</span>
                  </label>
                </div>
              </div>

              {categorizeResult && (
                <div
                  className={`p-3.5 rounded-xl border text-xs leading-relaxed flex items-start gap-2.5 ${
                    categorizeResult.includes('موفقیت')
                      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                      : 'bg-red-500/10 border-red-500/20 text-red-300'
                  }`}
                >
                  {categorizeResult.includes('موفقیت') ? (
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-4 h-4 shrink-0 text-red-400 mt-0.5" />
                  )}
                  <span>{categorizeResult}</span>
                </div>
              )}

              <div className="pt-2 flex justify-end">
                <button
                  type="submit"
                  disabled={categorizeMutation.isPending || !destPath.trim()}
                  className="px-5 py-2.5 bg-shelf-amber hover:bg-amber-400 text-black font-bold text-xs rounded-xl flex items-center gap-2 shadow-lg shadow-shelf-amber/10 transition disabled:opacity-50"
                >
                  {categorizeMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      در حال ایجاد میانبرها...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      شروع ساخت پوشه‌های میانبر مجازی
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      {/* Directory Browser Modal */}
      <FolderBrowserModal
        isOpen={isBrowserOpen}
        onClose={() => setIsBrowserOpen(false)}
        onSelectPath={(path: string) => {
          setDestPath(path);
          setIsBrowserOpen(false);
        }}
        initialPath={destPath || undefined}
      />
    </div>
  );
};
