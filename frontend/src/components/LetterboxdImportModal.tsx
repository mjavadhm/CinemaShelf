import React, { useState, useRef } from 'react';
import {
  Upload,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
  FileText,
  RefreshCw,
  FolderSync,
  Globe,
  ExternalLink,
} from 'lucide-react';
import { useLetterboxdSync } from '../hooks/useLetterboxdSync';
import { ImportSummary } from '../types/api';

interface LetterboxdImportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LetterboxdImportModal: React.FC<LetterboxdImportModalProps> = ({
  isOpen,
  onClose,
}) => {
  const {
    importFile,
    isImporting,
    importError,
    syncLocalHtml,
    isSyncingLocal,
    localSyncError,
    syncViaBrowser,
    isSyncingBrowser,
    browserSyncError,
    openBrowser,
    isOpeningBrowser,
  } = useLetterboxdSync();

  const fileInputRef = useRef<HTMLInputElement>(null);

  const [activeTab, setActiveTab] = useState<'LOCAL_FILES' | 'BROWSER'>('LOCAL_FILES');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [localFolderPath, setLocalFolderPath] = useState<string>('for scraping');
  const [username, setUsername] = useState<string>('javadhm');
  const [includeWatchlist, setIncludeWatchlist] = useState<boolean>(true);
  const [maxPages, setMaxPages] = useState<number>(20);

  const [conflictPolicy, setConflictPolicy] = useState<'PRESERVE_LOCAL' | 'OVERWRITE_LOCAL'>('PRESERVE_LOCAL');
  const [scaleMode, setScaleMode] = useState<'RAW' | 'TEN_POINT'>('TEN_POINT');
  const [result, setResult] = useState<ImportSummary | null>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setResult(null);
    }
  };

  const handleImportFile = async () => {
    if (!selectedFile) return;
    try {
      const summary = await importFile({
        file: selectedFile,
        conflictPolicy,
        scaleMode,
      });
      setResult(summary);
    } catch (err) {
      console.error('Letterboxd file import failed:', err);
    }
  };

  const handleSyncLocalFolder = async () => {
    try {
      const summary = await syncLocalHtml({
        folderPath: localFolderPath || 'for scraping',
        conflictPolicy,
        scaleMode,
      });
      setResult(summary);
    } catch (err) {
      console.error('Letterboxd local HTML sync failed:', err);
    }
  };

  const handleSyncBrowser = async () => {
    if (!username.trim()) return;
    try {
      const summary = await syncViaBrowser({
        username: username.trim(),
        includeWatchlist,
        maxPages: Number(maxPages) || 20,
        conflictPolicy,
        scaleMode,
      });
      setResult(summary);
    } catch (err) {
      console.error('Letterboxd browser sync failed:', err);
    }
  };

  const handleOpenBrowser = async () => {
    try {
      await openBrowser('https://letterboxd.com');
    } catch (err) {
      console.error('Failed to open Letterboxd browser:', err);
    }
  };

  const isBusy = isImporting || isSyncingLocal || isSyncingBrowser || isOpeningBrowser;
  const currentError = importError || localSyncError || browserSyncError;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="bg-shelf-card border border-shelf-border rounded-2xl w-full max-w-xl flex flex-col shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-shelf-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center text-emerald-400">
              <RefreshCw className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">مرکز همگام‌سازی Letterboxd</h2>
              <p className="text-[11px] text-slate-400">
                دریافت فیلم‌های دیده‌شده، نمرات و واچ‌لیست از فایل‌های HTML، آرشیو یا مرورگر
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

        {/* Tab Navigation */}
        {!result && (
          <div className="flex border-b border-shelf-border bg-shelf-bg/60 text-xs">
            <button
              onClick={() => setActiveTab('LOCAL_FILES')}
              className={`flex-1 py-3 px-4 font-medium flex items-center justify-center gap-2 border-b-2 transition ${
                activeTab === 'LOCAL_FILES'
                  ? 'border-shelf-amber text-shelf-amber bg-shelf-card'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <FolderSync className="w-4 h-4" />
              <span>فایل‌های ذخیره‌شده (HTML / ZIP)</span>
            </button>
            <button
              onClick={() => setActiveTab('BROWSER')}
              className={`flex-1 py-3 px-4 font-medium flex items-center justify-center gap-2 border-b-2 transition ${
                activeTab === 'BROWSER'
                  ? 'border-shelf-amber text-shelf-amber bg-shelf-card'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Globe className="w-4 h-4" />
              <span>همگام‌سازی مستقیم با مرورگر</span>
            </button>
          </div>
        )}

        {/* Modal Body */}
        <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
          {!result ? (
            <>
              {activeTab === 'LOCAL_FILES' ? (
                <div className="space-y-4">
                  {/* Local Folder Sync Box */}
                  <div className="p-4 rounded-xl bg-shelf-bg/80 border border-shelf-border space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-white text-xs font-bold">
                        <FolderSync className="w-4 h-4 text-shelf-amber" />
                        <span>پوشهٔ فایل‌های HTML ذخیره‌شده</span>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        سریع و آفلاین
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      برنامه فایل‌های HTML ذخیره‌شدهٔ Letterboxd (صفحات films، watchlist و امتیازها) را می‌خواند و تطبیق می‌دهد.
                    </p>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={localFolderPath}
                        onChange={(e) => setLocalFolderPath(e.target.value)}
                        placeholder="for scraping"
                        dir="ltr"
                        className="flex-1 bg-shelf-card border border-shelf-border rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-shelf-amber"
                      />
                      <button
                        type="button"
                        onClick={handleSyncLocalFolder}
                        disabled={isBusy}
                        className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1.5 transition disabled:opacity-50"
                      >
                        {isSyncingLocal ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="w-3.5 h-3.5" />
                        )}
                        <span>شروع همگام‌سازی پوشه</span>
                      </button>
                    </div>
                  </div>

                  <div className="relative flex py-1 items-center">
                    <div className="flex-grow border-t border-shelf-border"></div>
                    <span className="flex-shrink mx-3 text-slate-500 text-[11px]">یا انتخاب دستی فایل ZIP / CSV</span>
                    <div className="flex-grow border-t border-shelf-border"></div>
                  </div>

                  {/* File Upload Box */}
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition flex flex-col items-center justify-center gap-2 ${
                      selectedFile
                        ? 'border-emerald-500/50 bg-emerald-500/5'
                        : 'border-shelf-border hover:border-slate-500 bg-shelf-bg/60'
                    }`}
                  >
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileChange}
                      accept=".zip,.csv"
                      className="hidden"
                    />

                    <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center text-shelf-amber">
                      {selectedFile ? <FileText className="w-5 h-5 text-emerald-400" /> : <Upload className="w-5 h-5" />}
                    </div>

                    <div>
                      <p className="text-xs font-bold text-white">
                        {selectedFile ? selectedFile.name : 'انتخاب فایل ZIP یا CSV صادرشده از Letterboxd'}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {selectedFile
                          ? `${(selectedFile.size / 1024).toFixed(1)} KB`
                          : 'فرمت‌های قابل قبول: archive.zip یا watchlist.csv, ratings.csv, diary.csv'}
                      </p>
                    </div>
                  </div>

                  {selectedFile && (
                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={handleImportFile}
                        disabled={isBusy}
                        className="px-4 py-2 rounded-lg bg-shelf-amber hover:bg-shelf-amberHover text-black text-xs font-bold flex items-center gap-2 transition"
                      >
                        {isImporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                        <span>شروع ایمپورت فایل انتخاب‌شده</span>
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                /* BROWSER SCRAPING TAB */
                <div className="space-y-4">
                  {/* Browser Login Notice Box */}
                  <div className="p-4 rounded-xl bg-shelf-bg/80 border border-shelf-border space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white flex items-center gap-2">
                        <Globe className="w-4 h-4 text-shelf-amber" />
                        <span>مرورگر اختصاصی Letterboxd (پروفایل دائمی)</span>
                      </span>
                      <button
                        type="button"
                        onClick={handleOpenBrowser}
                        disabled={isBusy}
                        className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-shelf-amber text-xs font-medium flex items-center gap-1.5 transition"
                      >
                        {isOpeningBrowser ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <ExternalLink className="w-3.5 h-3.5" />
                        )}
                        <span>باز کردن مرورگر برای لاگین</span>
                      </button>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      همانند زرفیلم، مرورگر با پروفایل دائمی باز می‌شود. اگر قبلاً در مرورگر لاگین کرده‌اید نیازی به ورود مجدد نیست.
                    </p>
                  </div>

                  {/* Scrape Form Inputs */}
                  <div className="space-y-3 bg-shelf-bg/60 p-4 rounded-xl border border-shelf-border text-xs">
                    <div>
                      <label className="text-slate-300 font-medium block mb-1">
                        نام کاربری در Letterboxd:
                      </label>
                      <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="نام کاربری Letterboxd (مثلاً javadhm)"
                        dir="ltr"
                        className="w-full bg-shelf-card border border-shelf-border rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-shelf-amber text-xs"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3 pt-1">
                      <div>
                        <label className="text-slate-300 font-medium block mb-1">
                          حداکثر تعداد صفحات:
                        </label>
                        <input
                          type="number"
                          min={1}
                          max={100}
                          value={maxPages}
                          onChange={(e) => setMaxPages(Number(e.target.value))}
                          className="w-full bg-shelf-card border border-shelf-border rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-shelf-amber text-xs"
                        />
                        <span className="text-[10px] text-slate-500 mt-0.5 block">
                          هر صفحه شامل ۷۲ فیلم است.
                        </span>
                      </div>

                      <div className="flex flex-col justify-center pt-2">
                        <label className="flex items-center gap-2 cursor-pointer text-slate-300">
                          <input
                            type="checkbox"
                            checked={includeWatchlist}
                            onChange={(e) => setIncludeWatchlist(e.target.checked)}
                            className="rounded bg-slate-800 border-shelf-border text-shelf-amber focus:ring-0"
                          />
                          <span>شامل واچ‌لیست (Watchlist)</span>
                        </label>
                      </div>
                    </div>

                    <div className="pt-2">
                      <button
                        type="button"
                        onClick={handleSyncBrowser}
                        disabled={isBusy || !username.trim()}
                        className="w-full py-2.5 rounded-lg bg-shelf-amber hover:bg-shelf-amberHover text-black text-xs font-bold flex items-center justify-center gap-2 shadow-md transition disabled:opacity-50"
                      >
                        {isSyncingBrowser ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>در حال پیمایش صفحات و استخراج فیلم‌ها...</span>
                          </>
                        ) : (
                          <>
                            <Globe className="w-4 h-4" />
                            <span>شروع اسکرپ خودکار با مرورگر</span>
                          </>
                        )}
                      </button>
                    </div>

                    {isSyncingBrowser && (
                      <div className="p-3 rounded-lg bg-shelf-amber/10 border border-shelf-amber/30 text-shelf-amber text-xs flex items-start gap-2">
                        <Loader2 className="w-4 h-4 animate-spin shrink-0 mt-0.5" />
                        <div className="space-y-1">
                          <p className="font-bold">مرورگر در حال استخراج صفحات است...</p>
                          <p className="text-[11px] text-slate-300">
                            پیمایش چند صفحه‌ای فیلم‌ها و واچ‌لیست به صورت دسته‌ای انجام می‌شود و ممکن است ۱ تا ۲ دقیقه زمان ببرد. لطفاً پنجره را نبندید.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Conflict & Rating Scale Options */}
              <div className="grid grid-cols-2 gap-3 text-xs pt-1 border-t border-shelf-border">
                <div className="space-y-1">
                  <label className="text-slate-300 font-medium">سیاست تداخل (Conflict):</label>
                  <select
                    value={conflictPolicy}
                    onChange={(e: any) => setConflictPolicy(e.target.value)}
                    className="w-full bg-shelf-bg border border-shelf-border rounded-lg p-2 text-slate-200 focus:outline-none focus:border-shelf-amber text-xs"
                  >
                    <option value="PRESERVE_LOCAL">حفظ تغییرات محلی (توصیه شده)</option>
                    <option value="OVERWRITE_LOCAL">بازنویسی با اطلاعات فایل</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-slate-300 font-medium">مقیاس امتیازها:</label>
                  <select
                    value={scaleMode}
                    onChange={(e: any) => setScaleMode(e.target.value)}
                    className="w-full bg-shelf-bg border border-shelf-border rounded-lg p-2 text-slate-200 focus:outline-none focus:border-shelf-amber text-xs"
                  >
                    <option value="TEN_POINT">تبدیل به مقیاس ۱۰ امتیازی (توصیه شده)</option>
                    <option value="RAW">عادی (۱ تا ۵ ستاره)</option>
                  </select>
                </div>
              </div>

              {/* Error Alert */}
              {currentError && (
                <div className="p-3 rounded-lg bg-red-500/15 border border-red-500/30 text-red-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>
                    {(currentError as any)?.response?.data?.error?.message ||
                      (currentError as any)?.message ||
                      'خطا در برقراری ارتباط یا پردازش داده‌ها'}
                  </span>
                </div>
              )}
            </>
          ) : (
            /* Results View */
            <div className="space-y-4 py-2">
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 space-y-3">
                <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                  <CheckCircle className="w-5 h-5" />
                  <span>همگام‌سازی با موفقیت انجام شد!</span>
                </div>
                <p className="text-xs text-slate-300">{result.message}</p>
                <div className="grid grid-cols-2 gap-2 pt-2 text-xs text-slate-300">
                  <div className="bg-shelf-bg/60 p-2.5 rounded-lg">
                    مجموع آیتم‌ها: <strong className="text-white font-mono">{result.total_items ?? 0}</strong>
                  </div>
                  <div className="bg-shelf-bg/60 p-2.5 rounded-lg">
                    فیلم‌های دیده‌شده: <strong className="text-white font-mono">{result.watched_count ?? 0}</strong>
                  </div>
                  <div className="bg-shelf-bg/60 p-2.5 rounded-lg">
                    امتیازات وارد شده: <strong className="text-white font-mono">{result.ratings_count ?? 0}</strong>
                  </div>
                  <div className="bg-shelf-bg/60 p-2.5 rounded-lg">
                    واچ‌لیست: <strong className="text-white font-mono">{result.watchlist_count ?? 0}</strong>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-shelf-border flex items-center justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 rounded-lg bg-slate-800 text-slate-200 hover:text-white text-xs font-medium transition"
          >
            {result ? 'بستن' : 'انصراف'}
          </button>
        </div>
      </div>
    </div>
  );
};
