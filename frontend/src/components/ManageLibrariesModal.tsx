import React, { useState } from 'react';
import {
  Library as LibraryIcon,
  FolderPlus,
  RefreshCw,
  Trash2,
  HardDrive,
  FolderOpen,
  Check,
  X,
  Plus,
  Loader2,
  Film,
  Tv,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { useLibraries } from '../hooks/useLibraries';
import { FolderBrowserModal } from './FolderBrowserModal';
import { Library } from '../types/api';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const ManageLibrariesModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const {
    libraries,
    isLoading,
    createLibrary,
    deleteLibrary,
    addRoot,
    removeRoot,
    triggerScan,
    isCreating,
    isScanning,
    isAddingRoot,
  } = useLibraries();

  const [activeLibraryId, setActiveLibraryId] = useState<number | null>(null);
  const [isBrowserOpen, setIsBrowserOpen] = useState(false);

  // New Library Form state
  const [isAddingLibrary, setIsAddingLibrary] = useState(false);
  const [newLibName, setNewLibName] = useState('');
  const [newLibType, setNewLibType] = useState('MOVIE');

  // New Root Form state
  const [isAddingRootForm, setIsAddingRootForm] = useState(false);
  const [rootPath, setRootPath] = useState('');
  const [rootLabel, setRootLabel] = useState('');

  // Scan feedback state
  const [scanFeedback, setScanFeedback] = useState<string | null>(null);

  if (!isOpen) return null;

  // Selected library
  const selectedLib: Library | undefined =
    libraries.find((l) => l.id === activeLibraryId) || libraries[0];

  const handleCreateLibrary = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLibName.trim()) return;
    try {
      const created = await createLibrary({
        name: newLibName.trim(),
        content_type: newLibType,
      });
      setNewLibName('');
      setIsAddingLibrary(false);
      setActiveLibraryId(created.id);
    } catch (err: any) {
      alert(err.response?.data?.error?.message || 'خطا در ایجاد کتابخانه');
    }
  };

  const handleAddRoot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLib || !rootPath.trim()) return;
    try {
      await addRoot(selectedLib.id, {
        mount_path: rootPath.trim(),
        label: rootLabel.trim() || rootPath.split('/').pop() || 'Storage Root',
      });
      setRootPath('');
      setRootLabel('');
      setIsAddingRootForm(false);
    } catch (err: any) {
      alert(err.response?.data?.error?.message || 'خطا در افزودن مسیر ریشه');
    }
  };

  const handleScan = async (libraryId: number, rootId?: number) => {
    try {
      setScanFeedback('در حال اسکن و بررسی فایل‌های ویدیویی...');
      const res = await triggerScan(libraryId, rootId);
      setScanFeedback(
        `اسکن کامل شد: ${res.files_discovered} فایل کشف شد، ${res.files_imported} اثر اضافه/بروزرسانی شد.`
      );
      setTimeout(() => setScanFeedback(null), 5000);
    } catch (err: any) {
      setScanFeedback(
        `خطا در اسکن: ${err.response?.data?.error?.message || err.message}`
      );
      setTimeout(() => setScanFeedback(null), 5000);
    }
  };

  return (
    <>
      <div
        className="fixed inset-0 z-40 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in"
        dir="rtl"
      >
        <div className="bg-shelf-card border border-shelf-border rounded-2xl w-full max-w-4xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
          {/* Header */}
          <div className="p-4 border-b border-shelf-border flex items-center justify-between bg-slate-900/50">
            <div className="flex items-center gap-2.5">
              <LibraryIcon className="w-5 h-5 text-shelf-amber" />
              <div>
                <h3 className="font-bold text-base text-white">
                  مدیریت کتابخانه‌ها و پوشه‌های ریشه
                </h3>
                <p className="text-xs text-slate-400">
                  تعریف کتابخانه‌های مستقل، مسیرهای هارد دیسک و اسکن فیلم‌ها
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

          {/* Scan Feedback Banner */}
          {scanFeedback && (
            <div className="px-4 py-2.5 bg-shelf-amber/15 border-b border-shelf-amber/30 text-shelf-amber text-xs flex items-center gap-2 animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{scanFeedback}</span>
            </div>
          )}

          {/* Main Layout: Sidebar Libraries List + Selected Library Details */}
          <div className="flex-1 flex flex-col md:flex-row overflow-hidden min-h-[360px]">
            {/* Left/Right Sidebar: Libraries list */}
            <div className="w-full md:w-64 border-b md:border-b-0 md:border-l border-shelf-border p-3 space-y-2 bg-shelf-bg/60 overflow-y-auto">
              <div className="flex items-center justify-between pb-1">
                <span className="text-xs font-bold text-slate-300">
                  کتابخانه‌ها ({libraries.length})
                </span>
                <button
                  onClick={() => setIsAddingLibrary(true)}
                  className="p-1 rounded-lg bg-shelf-amber/10 hover:bg-shelf-amber/20 text-shelf-amber text-xs flex items-center gap-1 transition"
                  title="افزودن کتابخانه جدید"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>جدید</span>
                </button>
              </div>

              {/* Add Library Form Inline */}
              {isAddingLibrary && (
                <form
                  onSubmit={handleCreateLibrary}
                  className="p-3 bg-slate-900 border border-shelf-amber/40 rounded-xl space-y-2.5 animate-in fade-in"
                >
                  <div className="text-[11px] font-bold text-white">کتابخانه جدید</div>
                  <input
                    type="text"
                    placeholder="نام کتابخانه (مثلاً فیلم‌های اصلی)"
                    value={newLibName}
                    onChange={(e) => setNewLibName(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:border-shelf-amber outline-none"
                  />
                  <div className="flex gap-2 text-xs">
                    <label className="flex items-center gap-1.5 text-slate-300 cursor-pointer">
                      <input
                        type="radio"
                        name="libType"
                        value="MOVIE"
                        checked={newLibType === 'MOVIE'}
                        onChange={() => setNewLibType('MOVIE')}
                      />
                      <span>فیلم</span>
                    </label>
                    <label className="flex items-center gap-1.5 text-slate-300 cursor-pointer">
                      <input
                        type="radio"
                        name="libType"
                        value="SHOW"
                        checked={newLibType === 'SHOW'}
                        onChange={() => setNewLibType('SHOW')}
                      />
                      <span>سریال</span>
                    </label>
                  </div>
                  <div className="flex gap-1.5 pt-1">
                    <button
                      type="submit"
                      disabled={isCreating}
                      className="flex-1 py-1 rounded-lg bg-shelf-amber hover:bg-shelf-amberHover text-black text-xs font-bold"
                    >
                      {isCreating ? 'در حال ثبت...' : 'ایجاد'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsAddingLibrary(false)}
                      className="px-2 py-1 rounded-lg bg-slate-800 text-slate-300 text-xs"
                    >
                      لغو
                    </button>
                  </div>
                </form>
              )}

              {/* Libraries List */}
              <div className="space-y-1">
                {libraries.map((lib) => {
                  const isSelected = selectedLib?.id === lib.id;
                  return (
                    <button
                      key={lib.id}
                      onClick={() => setActiveLibraryId(lib.id)}
                      className={`w-full text-right p-2.5 rounded-xl transition flex items-center justify-between border ${
                        isSelected
                          ? 'bg-shelf-card border-shelf-amber/50 text-white shadow-md'
                          : 'hover:bg-slate-800/60 border-transparent text-slate-300'
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        {lib.content_type === 'SHOW' ? (
                          <Tv className="w-4 h-4 text-purple-400 shrink-0" />
                        ) : (
                          <Film className="w-4 h-4 text-shelf-amber shrink-0" />
                        )}
                        <span className="text-xs font-bold truncate">{lib.name}</span>
                      </div>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-400">
                        {lib.movie_count} اثر
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Content Area: Selected Library Roots and Scan Operations */}
            <div className="flex-1 p-5 space-y-5 overflow-y-auto">
              {selectedLib ? (
                <>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-shelf-border pb-4">
                    <div>
                      <h4 className="text-lg font-bold text-white flex items-center gap-2">
                        <span>{selectedLib.name}</span>
                        <span className="text-xs font-normal text-slate-400">
                          ({selectedLib.content_type === 'SHOW' ? 'سریال‌ها' : 'فیلم‌های سینمایی'})
                        </span>
                      </h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {selectedLib.roots.length} پوشه ریشه متصل • {selectedLib.movie_count} اثر ثبت‌شده
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleScan(selectedLib.id)}
                        disabled={isScanning || selectedLib.roots.length === 0}
                        className="px-3.5 py-2 rounded-xl bg-shelf-amber hover:bg-shelf-amberHover text-black text-xs font-bold transition flex items-center gap-1.5 disabled:opacity-50 shadow-md"
                      >
                        {isScanning ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="w-3.5 h-3.5" />
                        )}
                        <span>اسکن کامل کتابخانه</span>
                      </button>

                      <button
                        onClick={() => deleteLibrary(selectedLib.id)}
                        title="حذف این کتابخانه"
                        className="p-2 rounded-xl bg-slate-800 hover:bg-red-950/40 text-slate-400 hover:text-red-400 border border-shelf-border transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Roots Section */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h5 className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                        <FolderOpen className="w-4 h-4 text-shelf-amber" />
                        <span>پوشه‌های ریشه (Root Folders)</span>
                      </h5>

                      <button
                        onClick={() => setIsAddingRootForm(true)}
                        className="text-xs text-shelf-amber hover:text-shelf-amberHover flex items-center gap-1 font-medium transition"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>افزودن پوشه جدید</span>
                      </button>
                    </div>

                    {/* Add Root Form */}
                    {isAddingRootForm && (
                      <form
                        onSubmit={handleAddRoot}
                        className="p-4 bg-slate-900/90 border border-shelf-border rounded-xl space-y-3 animate-in fade-in"
                      >
                        <div className="text-xs font-bold text-white">
                          افزودن پوشهٔ ریشه جدید
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                          <div className="sm:col-span-2 flex gap-1.5">
                            <input
                              type="text"
                              placeholder="مسیر پوشه در سرور (مثلاً /home/javadhm/Movies)"
                              value={rootPath}
                              onChange={(e) => setRootPath(e.target.value)}
                              required
                              className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:border-shelf-amber outline-none"
                              dir="ltr"
                            />
                            <button
                              type="button"
                              onClick={() => setIsBrowserOpen(true)}
                              className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs flex items-center gap-1 border border-shelf-border transition shrink-0"
                            >
                              <FolderOpen className="w-3.5 h-3.5 text-shelf-amber" />
                              <span>انتخاب پوشه</span>
                            </button>
                          </div>

                          <div>
                            <input
                              type="text"
                              placeholder="نام اختیاری (مثلاً هارد آرشیو)"
                              value={rootLabel}
                              onChange={(e) => setRootLabel(e.target.value)}
                              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:border-shelf-amber outline-none"
                            />
                          </div>
                        </div>

                        <div className="flex justify-end gap-2 pt-1">
                          <button
                            type="button"
                            onClick={() => setIsAddingRootForm(false)}
                            className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-medium"
                          >
                            لغو
                          </button>
                          <button
                            type="submit"
                            disabled={isAddingRoot}
                            className="px-4 py-1.5 rounded-lg bg-shelf-amber hover:bg-shelf-amberHover text-black text-xs font-bold"
                          >
                            {isAddingRoot ? 'در حال افزودن...' : 'تایید و افزودن ریشه'}
                          </button>
                        </div>
                      </form>
                    )}

                    {/* Roots List */}
                    {selectedLib.roots.length === 0 ? (
                      <div className="p-8 text-center bg-slate-900/40 border border-dashed border-slate-800 rounded-xl space-y-2">
                        <FolderOpen className="w-8 h-8 text-slate-600 mx-auto" />
                        <p className="text-xs text-slate-400 font-bold">
                          هیچ پوشهٔ ریشه‌ای برای این کتابخانه ثبت نشده است
                        </p>
                        <p className="text-[11px] text-slate-500">
                          با کلیک روی «افزودن پوشه جدید»، پوشهٔ حاوی فیلم‌های خود را به این کتابخانه معرفی کنید.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {selectedLib.roots.map((root) => {
                          const usedGb = root.used_bytes
                            ? (root.used_bytes / (1024 * 1024 * 1024)).toFixed(1)
                            : null;
                          const totalGb = root.total_bytes
                            ? (root.total_bytes / (1024 * 1024 * 1024)).toFixed(1)
                            : null;

                          return (
                            <div
                              key={root.id}
                              className="bg-shelf-card border border-shelf-border rounded-xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm hover:border-slate-700 transition"
                            >
                              <div className="space-y-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-bold text-white">
                                    {root.label}
                                  </span>
                                  <span
                                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                      root.is_online
                                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                    }`}
                                  >
                                    {root.is_online ? 'متصل' : 'قطع (آفلاین)'}
                                  </span>
                                </div>
                                <div
                                  className="text-[11px] text-slate-400 font-mono truncate"
                                  dir="ltr"
                                  title={root.mount_path}
                                >
                                  {root.mount_path}
                                </div>
                              </div>

                              <div className="flex items-center gap-3 shrink-0">
                                {usedGb && totalGb && (
                                  <span className="text-[11px] text-slate-400 font-mono" dir="ltr">
                                    {usedGb} / {totalGb} GB
                                  </span>
                                )}

                                <button
                                  onClick={() => handleScan(selectedLib.id, root.id)}
                                  disabled={isScanning || !root.is_online}
                                  title="اسکن این ریشه"
                                  className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-shelf-amber transition border border-shelf-border disabled:opacity-40"
                                >
                                  <RefreshCw className="w-3.5 h-3.5" />
                                </button>

                                <button
                                  onClick={() => removeRoot(root.id)}
                                  title="حذف ریشه"
                                  className="p-2 rounded-lg bg-slate-800 hover:bg-red-950/40 text-slate-400 hover:text-red-400 transition border border-shelf-border"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="p-12 text-center text-slate-400 text-xs">
                  کتابخانه‌ای انتخاب نشده است.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Directory Browser Modal */}
      <FolderBrowserModal
        isOpen={isBrowserOpen}
        onClose={() => setIsBrowserOpen(false)}
        onSelectPath={(selected) => setRootPath(selected)}
        initialPath={rootPath || undefined}
      />
    </>
  );
};
