import React, { useState, useRef } from 'react';
import { Upload, X, CheckCircle, AlertCircle, Loader2, FileText, RefreshCw } from 'lucide-react';
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
  const { importFile, isImporting, importError } = useLetterboxdSync();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [conflictPolicy, setConflictPolicy] = useState<'PRESERVE_LOCAL' | 'OVERWRITE_LOCAL'>('PRESERVE_LOCAL');
  const [scaleMode, setScaleMode] = useState<'RAW' | 'TEN_POINT'>('RAW');
  const [result, setResult] = useState<ImportSummary | null>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setResult(null);
    }
  };

  const handleImport = async () => {
    if (!selectedFile) return;
    try {
      const summary = await importFile({
        file: selectedFile,
        conflictPolicy,
        scaleMode,
      });
      setResult(summary);
    } catch (err) {
      console.error('Letterboxd import failed:', err);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setResult(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="bg-shelf-card border border-shelf-border rounded-2xl w-full max-w-lg flex flex-col shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-shelf-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center text-emerald-400">
              <RefreshCw className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">وارد کردن آرشیو Letterboxd</h2>
              <p className="text-[11px] text-slate-400">
                فایل ZIP صادراتی کامل یا فایل‌های CSV (واچ‌لیست، امتیازات، خاطرات) را وارد کنید
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

        {/* Content */}
        <div className="p-6 space-y-5">
          {!result ? (
            <>
              {/* File Drop / Select Area */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition flex flex-col items-center justify-center gap-2.5 ${
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

                <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center text-shelf-amber">
                  {selectedFile ? <FileText className="w-6 h-6 text-emerald-400" /> : <Upload className="w-6 h-6" />}
                </div>

                <div>
                  <p className="text-sm font-bold text-white">
                    {selectedFile ? selectedFile.name : 'انتخاب فایل آرشیو Letterboxd'}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {selectedFile
                      ? `${(selectedFile.size / 1024).toFixed(1)} KB`
                      : 'فرمت‌های قابل قبول: archive.zip یا watchlist.csv, ratings.csv, diary.csv'}
                  </p>
                </div>
              </div>

              {/* Import Options */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-medium">سیاست تداخل (Conflict):</label>
                  <select
                    value={conflictPolicy}
                    onChange={(e: any) => setConflictPolicy(e.target.value)}
                    className="w-full bg-shelf-bg border border-shelf-border rounded-lg p-2 text-slate-200 focus:outline-none focus:border-shelf-amber"
                  >
                    <option value="PRESERVE_LOCAL">حفظ تغییرات محلی (توصیه شده)</option>
                    <option value="OVERWRITE_LOCAL">بازنویسی با اطلاعات فایل</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 font-medium">مقیاس امتیازها:</label>
                  <select
                    value={scaleMode}
                    onChange={(e: any) => setScaleMode(e.target.value)}
                    className="w-full bg-shelf-bg border border-shelf-border rounded-lg p-2 text-slate-200 focus:outline-none focus:border-shelf-amber"
                  >
                    <option value="RAW">عادی (۱ تا ۵ ستاره)</option>
                    <option value="TEN_POINT">تبدیل به مقیاس ۱۰ امتیازی</option>
                  </select>
                </div>
              </div>

              {/* Error Alert */}
              {importError && (
                <div className="p-3 rounded-lg bg-red-500/15 border border-red-500/30 text-red-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{(importError as any)?.response?.data?.error?.message || 'خطا در پردازش فایل'}</span>
                </div>
              )}
            </>
          ) : (
            /* Results View */
            <div className="space-y-4 py-2">
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 space-y-2">
                <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                  <CheckCircle className="w-5 h-5" />
                  <span>آرشیو با موفقیت وارد و همگام‌سازی شد!</span>
                </div>
                <div className="grid grid-cols-2 gap-2 pt-2 text-xs text-slate-300">
                  <div className="bg-shelf-bg/60 p-2 rounded-lg">
                    فیلم‌های افزوده شده: <strong className="text-white font-mono">{result.movies_imported}</strong>
                  </div>
                  <div className="bg-shelf-bg/60 p-2 rounded-lg">
                    واچ‌لیست: <strong className="text-white font-mono">{result.watchlist_imported}</strong>
                  </div>
                  <div className="bg-shelf-bg/60 p-2 rounded-lg">
                    امتیازات وارد شده: <strong className="text-white font-mono">{result.ratings_imported}</strong>
                  </div>
                  <div className="bg-shelf-bg/60 p-2 rounded-lg">
                    خاطرات تماشا: <strong className="text-white font-mono">{result.reviews_imported}</strong>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-shelf-border flex items-center justify-end gap-2.5">
          {!result ? (
            <>
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white text-xs font-medium transition"
              >
                انصراف
              </button>
              <button
                type="button"
                onClick={handleImport}
                disabled={!selectedFile || isImporting}
                className="px-5 py-2 rounded-lg bg-shelf-amber hover:bg-shelf-amberHover text-black text-xs font-bold flex items-center gap-2 shadow-md shadow-shelf-amber/10 transition disabled:opacity-50"
              >
                {isImporting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>در حال همگام‌سازی و بارگذاری...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    <span>شروع ایمپورت</span>
                  </>
                )}
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2 rounded-lg bg-shelf-amber text-black text-xs font-bold"
            >
              بستن
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
