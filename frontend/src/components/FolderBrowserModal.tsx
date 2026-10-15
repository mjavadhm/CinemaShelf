import React, { useState } from 'react';
import {
  Folder,
  FolderOpen,
  ArrowRight,
  ArrowUp,
  Check,
  X,
  HardDrive,
  Loader2,
  Lock,
} from 'lucide-react';
import { useDirectoryBrowser } from '../hooks/useLibraries';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSelectPath: (selectedPath: string) => void;
  initialPath?: string;
}

export const FolderBrowserModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onSelectPath,
  initialPath,
}) => {
  const [currentPath, setCurrentPath] = useState<string>(initialPath || '');
  const { data, isLoading, isError, refetch } = useDirectoryBrowser(currentPath || undefined);

  if (!isOpen) return null;

  const handleSelect = (path: string) => {
    onSelectPath(path);
    onClose();
  };

  const handleNavigate = (path: string) => {
    setCurrentPath(path);
  };

  const handleNavigateUp = () => {
    if (data?.parent_path) {
      setCurrentPath(data.parent_path);
    }
  };

  const freeGb = data?.free_bytes
    ? (data.free_bytes / (1024 * 1024 * 1024)).toFixed(1)
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in" dir="rtl">
      <div className="bg-shelf-card border border-shelf-border rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-4 border-b border-shelf-border flex items-center justify-between bg-slate-900/50">
          <div className="flex items-center gap-2.5">
            <FolderOpen className="w-5 h-5 text-shelf-amber" />
            <div>
              <h3 className="font-bold text-sm text-white">انتخاب پوشه از سرور</h3>
              <p className="text-[11px] text-slate-400">
                پوشهٔ ریشه حاوی فیلم‌ها را برای این کتابخانه انتخاب کنید
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Current Path Bar & Parent Navigation */}
        <div className="p-3 bg-shelf-bg border-b border-shelf-border flex items-center gap-2 text-xs" dir="ltr">
          <button
            onClick={handleNavigateUp}
            disabled={!data?.parent_path}
            title="رفتن به پوشه بالاتر"
            className="p-1.5 rounded-lg bg-shelf-card hover:bg-slate-800 text-slate-300 disabled:opacity-40 transition border border-shelf-border shrink-0"
          >
            <ArrowUp className="w-4 h-4" />
          </button>

          <input
            type="text"
            value={data?.current_path || currentPath}
            onChange={(e) => setCurrentPath(e.target.value)}
            className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 font-mono text-xs text-white focus:border-shelf-amber outline-none"
          />

          {freeGb && (
            <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 bg-shelf-card rounded-lg border border-shelf-border text-[11px] text-emerald-400 font-mono shrink-0">
              <HardDrive className="w-3.5 h-3.5" />
              <span>{freeGb} GB آزاد</span>
            </div>
          )}
        </div>

        {/* Directory Listing */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1 min-h-[260px] max-h-[380px]">
          {isLoading && (
            <div className="py-16 flex flex-col items-center justify-center gap-2 text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin text-shelf-amber" />
              <span className="text-xs">در حال بارگذاری پوشه‌ها...</span>
            </div>
          )}

          {isError && (
            <div className="p-6 text-center text-red-400 text-xs">
              خطا در دسترسی به این مسیر. ممکن است دسترسی مجاز نباشد.
            </div>
          )}

          {!isLoading && data && data.directories.length === 0 && (
            <div className="py-12 text-center text-slate-500 text-xs">
              هیچ زیرپوشه‌ای در این مسیر یافت نشد.
            </div>
          )}

          {!isLoading &&
            data &&
            data.directories.map((dir) => (
              <div
                key={dir.path}
                className="flex items-center justify-between p-2 rounded-xl hover:bg-slate-800/80 group transition cursor-pointer border border-transparent hover:border-shelf-border"
                onClick={() => handleNavigate(dir.path)}
              >
                <div className="flex items-center gap-2.5 min-w-0" dir="ltr">
                  <Folder className="w-4 h-4 text-shelf-amber shrink-0 fill-current/20" />
                  <span className="text-xs font-mono text-slate-200 truncate group-hover:text-white">
                    {dir.name}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {!dir.is_writable && (
                    <span title="بدون دسترسی نوشتن" className="text-slate-500">
                      <Lock className="w-3.5 h-3.5" />
                    </span>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelect(dir.path);
                    }}
                    className="px-2.5 py-1 rounded-lg bg-shelf-amber hover:bg-shelf-amberHover text-black text-[11px] font-bold opacity-0 group-hover:opacity-100 transition flex items-center gap-1"
                  >
                    <Check className="w-3 h-3" />
                    <span>انتخاب</span>
                  </button>
                </div>
              </div>
            ))}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-shelf-border bg-slate-900/50 flex items-center justify-between gap-3">
          <span className="text-xs text-slate-400 truncate font-mono max-w-[340px]" dir="ltr">
            {data?.current_path || currentPath}
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
            >
              انصراف
            </button>
            <button
              onClick={() => handleSelect(data?.current_path || currentPath)}
              disabled={!data?.current_path && !currentPath}
              className="px-4 py-2 rounded-xl bg-shelf-amber hover:bg-shelf-amberHover text-black text-xs font-bold transition flex items-center gap-1.5 shadow-md"
            >
              <Check className="w-4 h-4" />
              <span>انتخاب این پوشه</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
