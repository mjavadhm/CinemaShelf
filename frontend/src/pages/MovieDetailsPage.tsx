import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowRight,
  Play,
  FolderOpen,
  Copy,
  Check,
  HardDrive,
  Star,
  Users,
  Bookmark,
  Download,
  Loader2,
  ExternalLink,
  Search,
  Globe,
  RefreshCw,
} from 'lucide-react';
import { RematchModal } from '../components/RematchModal';
import { useWorkDetails } from '../hooks/useWorkDetails';
import { usePersonalActions } from '../hooks/usePersonalActions';
import { usePlaybackLaunch } from '../hooks/usePlaybackLaunch';
import { useSearchAndAddWork, useWorkReleases } from '../hooks/useSearchAndAddWork';
import { rateMovieOnLetterboxd } from '../api/endpoints';
import { getTmdbImageUrl } from '../types/api';

export const MovieDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const {
    work,
    personalRecord,
    libraryItem,
    mediaFiles,
    isLoading,
    isError,
    error,
    refetchAll,
  } = useWorkDetails(id);

  const { rateWork, toggleWatchlist, isRating, isTogglingWatchlist } = usePersonalActions(work?.id);
  const { openMediaFile, openWork, openFileLocation, isOpening, isOpeningLocation } = usePlaybackLaunch();
  const { discoverReleases, isDiscoveringReleases, triggerDownload, isTriggeringDownload } = useSearchAndAddWork();
  const { data: discoveredReleases } = useWorkReleases(work?.id);

  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [playbackFeedback, setPlaybackFeedback] = useState<string | null>(null);
  const [downloadSuccessId, setDownloadSuccessId] = useState<number | null>(null);
  const [hoverRating, setHoverRating] = useState<number | null>(null);
  const [isSubmittingToLetterboxd, setIsSubmittingToLetterboxd] = useState(false);
  const [letterboxdFeedback, setLetterboxdFeedback] = useState<string | null>(null);
  const [isRematchOpen, setIsRematchOpen] = useState(false);

  const handleRateOnLetterboxd = async () => {
    if (!work) return;
    const ratingToSubmit = personalRecord?.user_rating ?? (hoverRating || 10);
    try {
      setIsSubmittingToLetterboxd(true);
      setLetterboxdFeedback(null);
      const res = await rateMovieOnLetterboxd(work.id, Math.round(ratingToSubmit));
      setLetterboxdFeedback(res.message || 'نمره در Letterboxd ثبت شد!');
      refetchAll();
      setTimeout(() => setLetterboxdFeedback(null), 4000);
    } catch (err: any) {
      const msg =
        err.response?.data?.error?.message ||
        err.message ||
        'خطا در ثبت نمره در Letterboxd';
      setLetterboxdFeedback(msg);
      setTimeout(() => setLetterboxdFeedback(null), 6000);
    } finally {
      setIsSubmittingToLetterboxd(false);
    }
  };

  const copyPath = (fileId: number, path: string) => {
    navigator.clipboard.writeText(path);
    setCopiedId(fileId);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const handlePlayDirect = async () => {
    if (!work) return;
    try {
      const firstOnline = mediaFiles.find((f) => f.is_online) || mediaFiles[0];
      if (firstOnline) {
        const res = await openMediaFile(firstOnline.id);
        setPlaybackFeedback(res.message);
      } else {
        const res = await openWork(work.id);
        setPlaybackFeedback(res.message);
      }
      setTimeout(() => setPlaybackFeedback(null), 3000);
    } catch (err: any) {
      setPlaybackFeedback('خطا در اجرای پلیر');
      setTimeout(() => setPlaybackFeedback(null), 3000);
    }
  };

  const handleOpenFileLocation = async (fileId: number) => {
    try {
      await openFileLocation(fileId);
    } catch (err) {
      console.error('Failed to open location:', err);
    }
  };

  const handleRate = async (star: number) => {
    if (!work) return;
    const newRating = personalRecord?.user_rating === star ? null : star;
    await rateWork(work.id, newRating);
  };

  const handleToggleWatchlist = async () => {
    if (!work) return;
    await toggleWatchlist(work.id, !personalRecord?.in_watchlist);
  };

  const handleDiscoverZarfilm = async () => {
    if (!work) return;
    try {
      await discoverReleases(work.id);
      refetchAll();
    } catch (err) {
      console.error('Failed to discover Zarfilm releases:', err);
    }
  };

  const handleDownloadRelease = async (releaseId: number, downloadUrl: string) => {
    if (!libraryItem) return;
    try {
      await triggerDownload({
        libraryItemId: libraryItem.id,
        releaseId,
        downloadUrl,
      });
      setDownloadSuccessId(releaseId);
      setTimeout(() => setDownloadSuccessId(null), 3000);
    } catch (err) {
      console.error('Failed to queue download:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center gap-3 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-shelf-amber" />
        <span className="text-sm">در حال بارگذاری اطلاعات فیلم و فایل‌های آرشیو...</span>
      </div>
    );
  }

  if (isError || !work) {
    return (
      <div className="p-8 text-center bg-shelf-card border border-shelf-border rounded-2xl max-w-md mx-auto space-y-4">
        <p className="text-red-400 font-bold text-sm">فیلم مورد نظر یافت نشد</p>
        <p className="text-xs text-slate-400">{(error as any)?.message || 'شناسه فیلم معتبر نیست.'}</p>
        <Link
          to="/"
          className="inline-block px-4 py-2 rounded-lg bg-slate-800 text-xs text-slate-200 hover:text-white"
        >
          بازگشت به کتابخانه
        </Link>
      </div>
    );
  }

  // Find director from credits
  const directorCredit = (work.credits || []).find(
    (c) => c.credit_type === 'CREW' && (c.job === 'Director' || c.department === 'Directing')
  );
  const directorName = directorCredit?.person.persian_name || directorCredit?.person.name || 'نامشخص';

  // Best resolution available
  const bestResolution = mediaFiles.some((f) => f.resolution?.includes('2160') || f.resolution?.includes('4K'))
    ? '4K UHD'
    : mediaFiles.some((f) => f.resolution?.includes('1080'))
    ? '1080p'
    : mediaFiles.length > 0
    ? '720p'
    : 'در انتظار دانلود';

  const inWatchlist = personalRecord?.in_watchlist ?? false;
  const currentRating = personalRecord?.user_rating;

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Top Back Navigation Button */}
      <div className="flex items-center justify-between">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-xs font-medium text-slate-300 hover:text-shelf-amber bg-shelf-card border border-shelf-border px-3.5 py-2 rounded-lg transition"
        >
          <ArrowRight className="w-4 h-4" />
          <span>بازگشت به کتابخانه</span>
        </Link>

        {playbackFeedback && (
          <span className="text-xs bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 px-3 py-1.5 rounded-lg animate-in fade-in">
            {playbackFeedback}
          </span>
        )}
      </div>

      {/* Hero Section */}
      <div className="bg-shelf-card border border-shelf-border rounded-2xl p-6 flex flex-col md:flex-row gap-7 shadow-xl">
        <img
          src={getTmdbImageUrl(work.poster_path, 'w500')}
          alt={work.title}
          className="w-48 md:w-56 rounded-xl object-cover shadow-2xl shrink-0 mx-auto md:mx-0 border border-white/10 bg-slate-900"
        />

        <div className="flex-1 flex flex-col justify-between space-y-5">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-0.5 rounded bg-shelf-amber/15 text-shelf-amber border border-shelf-amber/30 text-xs font-mono font-bold">
                {bestResolution}
              </span>
              {(work.genres || []).map((g) => (
                <span
                  key={g.id}
                  className="px-2.5 py-0.5 rounded bg-slate-800 text-slate-300 text-xs"
                >
                  {g.persian_name || g.name}
                </span>
              ))}
            </div>

            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-white">
                {work.persian_title || work.title}{' '}
                <span className="text-slate-400 font-mono text-xl font-normal" dir="ltr">
                  ({work.title})
                </span>
              </h1>
              <p className="text-sm text-slate-400 mt-1">
                کارگردان: <strong className="text-slate-200">{directorName}</strong> • محصول سال{' '}
                {work.release_year || '—'} {work.runtime_minutes ? `• ${work.runtime_minutes} دقیقه` : ''}
              </p>
            </div>

            {/* Ratings Bar */}
            <div className="grid grid-cols-3 gap-3 max-w-md pt-1">
              {/* Personal Rating */}
              <div className="bg-shelf-bg border border-shelf-border rounded-xl p-3 text-center">
                <div className="text-[11px] text-slate-400">امتیاز شخصی</div>
                <div className="text-lg font-bold text-shelf-amber font-mono mt-0.5">
                  {currentRating ? `${currentRating}/10` : '—'}
                </div>
              </div>

              {/* TMDB */}
              <div className="bg-shelf-bg border border-shelf-border rounded-xl p-3 text-center">
                <div className="text-[11px] text-slate-400">TMDB</div>
                <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">
                  ★ {work.tmdb_rating ? work.tmdb_rating.toFixed(1) : '—'}
                </div>
              </div>

              {/* IMDb */}
              <div className="bg-shelf-bg border border-shelf-border rounded-xl p-3 text-center">
                <div className="text-[11px] text-slate-400">IMDb</div>
                <div className="text-lg font-bold text-amber-400 font-mono mt-0.5">
                  ★ {work.imdb_rating ? work.imdb_rating.toFixed(1) : '—'}
                </div>
              </div>
            </div>

            {/* Interactive User Rating Row */}
            <div className="bg-shelf-bg/60 border border-shelf-border/80 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 max-w-lg">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-300 font-medium">امتیاز دهید:</span>
                <div className="flex items-center gap-1" dir="ltr">
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((star) => {
                    const active =
                      (hoverRating !== null && star <= hoverRating) ||
                      (hoverRating === null && currentRating != null && star <= Math.round(currentRating));
                    return (
                      <button
                        key={star}
                        onClick={() => handleRate(star)}
                        onMouseEnter={() => setHoverRating(star)}
                        onMouseLeave={() => setHoverRating(null)}
                        disabled={isRating}
                        className="p-0.5 text-slate-600 hover:scale-125 transition-transform"
                        title={`${star} از ۱۰`}
                      >
                        <Star
                          className={`w-3.5 h-3.5 ${
                            active
                              ? 'text-shelf-amber fill-shelf-amber'
                              : 'text-slate-600'
                          }`}
                        />
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Letterboxd Rate Trigger Button */}
              <button
                type="button"
                onClick={handleRateOnLetterboxd}
                disabled={isSubmittingToLetterboxd || !currentRating}
                title={
                  currentRating
                    ? `ثبت نمره ${Math.round(currentRating)} از ۱۰ در Letterboxd با مرورگر`
                    : 'ابتدا نمره دهید تا در Letterboxd ثبت شود'
                }
                className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-emerald-400 text-[11px] font-medium flex items-center gap-1.5 transition disabled:opacity-40"
              >
                {isSubmittingToLetterboxd ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Globe className="w-3 h-3" />
                )}
                <span>ثبت در Letterboxd</span>
              </button>
            </div>

            {letterboxdFeedback && (
              <div className="text-xs px-3 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 inline-block">
                {letterboxdFeedback}
              </div>
            )}

            {work.overview && (
              <p className="text-sm text-slate-300 leading-relaxed pt-2 line-clamp-4">
                {work.overview}
              </p>
            )}
          </div>

          {/* Primary Action Buttons */}
          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-shelf-border">
            {mediaFiles.length > 0 ? (
              <button
                onClick={handlePlayDirect}
                disabled={isOpening}
                className="px-5 py-2.5 rounded-xl bg-shelf-amber hover:bg-shelf-amberHover text-black font-bold text-sm flex items-center gap-2 shadow-lg shadow-shelf-amber/20 transition"
              >
                {isOpening ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 fill-current" />
                )}
                <span>پخش مستقیم فیلم ({bestResolution})</span>
              </button>
            ) : null}

            {/* Toggle Watchlist Button */}
            <button
              onClick={handleToggleWatchlist}
              disabled={isTogglingWatchlist}
              className={`px-4 py-2.5 rounded-xl border text-xs font-medium flex items-center gap-2 transition ${
                inWatchlist
                  ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                  : 'bg-shelf-bg hover:bg-slate-800 text-slate-200 border-shelf-border'
              }`}
            >
              <Bookmark className="w-4 h-4" />
              <span>{inWatchlist ? 'در واچ‌لیست شما' : 'افزودن به واچ‌لیست'}</span>
            </button>

            {/* Discover Zarfilm Releases Button */}
            <button
              onClick={handleDiscoverZarfilm}
              disabled={isDiscoveringReleases}
              className="px-4 py-2.5 rounded-xl bg-shelf-bg hover:bg-slate-800 text-shelf-amber border border-shelf-border text-xs font-medium flex items-center gap-2 transition"
            >
              {isDiscoveringReleases ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              <span>جستجوی لینک‌های دانلود (زرفیلم)</span>
            </button>

            {/* Rematch Button */}
            <button
              onClick={() => setIsRematchOpen(true)}
              className="px-4 py-2.5 rounded-xl bg-shelf-bg hover:bg-slate-800 text-rose-300 hover:text-rose-200 border border-shelf-border text-xs font-medium flex items-center gap-2 transition"
              title="اگر فایل این فیلم اشتباهی شناسایی شده، می‌توانید فیلم صحیح را از TMDB انتخاب کنید"
            >
              <RefreshCw className="w-4 h-4" />
              <span>تصحیح تطابق فیلم (Rematch)</span>
            </button>
          </div>
        </div>
      </div>

      {/* Discovered Zarfilm Releases (if any) */}
      {discoveredReleases && discoveredReleases.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Download className="w-5 h-5 text-shelf-amber" />
              <span>لینک‌های دانلود کشف شده از زرفیلم ({discoveredReleases.length} نسخه)</span>
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {discoveredReleases.map((rel) => (
              <div
                key={rel.id}
                className="p-4 rounded-xl bg-shelf-card border border-shelf-border flex flex-col justify-between space-y-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-shelf-amber/15 text-shelf-amber border border-shelf-amber/30 text-xs font-mono font-bold">
                        {rel.resolution || rel.quality_label || 'نسخه دانلود'}
                      </span>
                      {rel.encoder && (
                        <span className="text-xs text-slate-300 font-mono">
                          {rel.encoder}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400 font-mono">
                      حجم: {rel.size_text || `${rel.size_bytes ? (rel.size_bytes / (1024 * 1024 * 1024)).toFixed(2) : '—'} GB`}
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 text-[10px]">
                    {rel.has_persian_sub && (
                      <span className="px-2 py-0.5 rounded bg-blue-500/15 text-blue-400 border border-blue-500/30">
                        زیرنویس فارسی
                      </span>
                    )}
                    {rel.is_dubbed && (
                      <span className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30">
                        دوبله
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between gap-2 pt-2 border-t border-shelf-border/60">
                  <span className="text-[11px] text-slate-500 truncate font-mono max-w-[200px]" dir="ltr">
                    {rel.download_url}
                  </span>
                  <button
                    onClick={() => handleDownloadRelease(rel.id, rel.download_url)}
                    disabled={isTriggeringDownload || downloadSuccessId === rel.id}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition ${
                      downloadSuccessId === rel.id
                        ? 'bg-emerald-500 text-black'
                        : 'bg-shelf-amber hover:bg-shelf-amberHover text-black'
                    }`}
                  >
                    {downloadSuccessId === rel.id ? (
                      <>
                        <Check className="w-3.5 h-3.5" />
                        <span>ارسال شد</span>
                      </>
                    ) : (
                      <>
                        <Download className="w-3.5 h-3.5" />
                        <span>دانلود با Aria2</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Multi-File & Archive Versions Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <HardDrive className="w-5 h-5 text-shelf-amber" />
            <span>مدیریت چندفایلی و نسخه‌های آرشیو ({mediaFiles.length} نسخه)</span>
          </h2>
          <button
            onClick={() => setIsRematchOpen(true)}
            className="px-3 py-1.5 rounded-lg bg-shelf-card hover:bg-slate-800 text-rose-300 border border-shelf-border text-xs flex items-center gap-1.5 transition"
            title="انتقال فایل‌های این فیلم به فیلم دیگر از TMDB"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>تصحیح فیلم (Rematch)</span>
          </button>
        </div>

        {mediaFiles.length === 0 ? (
          <div className="p-8 text-center bg-shelf-card border border-shelf-border rounded-xl text-slate-400 text-xs space-y-2">
            <p>هنوز فایل فیزیکی برای این فیلم ثبت نشده است.</p>
            <p className="text-slate-500">
              می‌توانید از بخش «جستجوی لینک‌های دانلود» کیفیتی را انتخاب و با Aria2 دانلود نمایید.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {mediaFiles.map((file) => (
              <div
                key={file.id}
                className={`rounded-xl border p-5 space-y-4 ${
                  file.is_online
                    ? 'bg-shelf-card border-emerald-500/30'
                    : 'bg-shelf-card/60 border-red-500/30 opacity-85'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`w-2.5 h-2.5 rounded-full ${
                        file.is_online ? 'bg-emerald-400' : 'bg-red-400'
                      }`}
                    />
                    <span className="font-bold text-sm text-white">
                      {file.is_online
                        ? 'نسخه آنلاین — آماده پخش مستقیم'
                        : 'نسخه آرشیو (آفلاین) — در انتظار اتصال هارد دیسک'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 font-mono text-xs" dir="ltr">
                    {file.resolution && (
                      <span className="px-2.5 py-1 rounded bg-shelf-bg border border-shelf-border text-shelf-amber font-bold">
                        {file.resolution}
                      </span>
                    )}
                    {file.video_codec && (
                      <span className="px-2.5 py-1 rounded bg-shelf-bg border border-shelf-border text-slate-300">
                        {file.video_codec}
                      </span>
                    )}
                    {file.file_size_bytes && (
                      <span className="px-2.5 py-1 rounded bg-shelf-bg border border-shelf-border text-emerald-400">
                        {(file.file_size_bytes / (1024 * 1024 * 1024)).toFixed(2)} GB
                      </span>
                    )}
                  </div>
                </div>

                {/* Clean LTR Monospace Path Box */}
                <div
                  dir="ltr"
                  className="flex items-center justify-between gap-3 bg-shelf-bg border border-shelf-border rounded-lg px-3.5 py-2 font-mono text-xs text-slate-300"
                >
                  <span className="truncate">{file.file_path}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleOpenFileLocation(file.id)}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center gap-1.5 text-[11px] transition"
                      title="باز کردن پوشه در فایل منیجر سیستم"
                    >
                      <FolderOpen className="w-3.5 h-3.5 text-shelf-amber" />
                      <span>Open Folder</span>
                    </button>
                    <button
                      onClick={() => copyPath(file.id, file.file_path)}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center gap-1.5 text-[11px] transition"
                    >
                      {copiedId === file.id ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy Path</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Cast & Crew Section (Clickable linking to /people/:id) */}
      {(work.credits || []).length > 0 && (
        <section className="space-y-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-shelf-amber" />
            <span>بازیگران و عوامل شاخص</span>
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
            {(work.credits || []).map((credit) => (
              <Link
                to={`/people/${credit.person.id}`}
                key={credit.id}
                className="group bg-shelf-card border border-shelf-border rounded-xl overflow-hidden flex flex-col hover:border-shelf-amber/60 transition shadow-md"
              >
                <img
                  src={getTmdbImageUrl(credit.person.profile_path, 'w300')}
                  alt={credit.person.name}
                  className="w-full h-44 object-cover bg-slate-900 group-hover:scale-105 transition-transform duration-300"
                />
                <div className="p-3 space-y-1">
                  <div className="font-bold text-xs text-white group-hover:text-shelf-amber transition">
                    {credit.person.persian_name || credit.person.name}
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono truncate" dir="ltr">
                    {credit.person.name}
                  </div>
                  <div className="text-[11px] text-shelf-amber pt-1 truncate">
                    {credit.credit_type === 'CREW'
                      ? credit.job || credit.department
                      : credit.character_name || 'بازیگر'}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Rematch Modal */}
      <RematchModal
        isOpen={isRematchOpen}
        onClose={() => setIsRematchOpen(false)}
        workId={work.id}
        libraryItemId={libraryItem?.id}
        currentTitle={work.title}
        currentYear={work.release_year}
        mediaFilesCount={mediaFiles.length}
      />
    </div>
  );
};
