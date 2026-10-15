import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  Film,
  BookmarkCheck,
  HardDrive,
  Download,
  Search,
  RefreshCw,
  Disc,
  AlertTriangle,
  Plus,
  FolderOpen,
} from 'lucide-react';
import { useStorageVolumes } from '../hooks/useStorageVolumes';
import { useDownloadQueue } from '../hooks/useDownloadQueue';
import { useWatchlistWorks } from '../hooks/usePersonalActions';
import { AddWorkModal } from './AddWorkModal';
import { ManageLibrariesModal } from './ManageLibrariesModal';

export const AppLayout: React.FC<{
  searchQuery: string;
  setSearchQuery: (q: string) => void;
}> = ({ searchQuery, setSearchQuery }) => {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isManageLibrariesOpen, setIsManageLibrariesOpen] = useState(false);
  const { volumes, disconnectedVolumes, hasDisconnectedVolumes } = useStorageVolumes();
  const { speedMbps, activeCount, isOnline } = useDownloadQueue();
  const { data: watchlistItems } = useWatchlistWorks();

  const watchlistCount = watchlistItems?.length || 0;

  const navItems = [
    { to: '/', label: 'کتابخانه من', icon: Film },
    {
      to: '/watchlist',
      label: 'واچ‌لیست و مرکز دانلودها',
      icon: BookmarkCheck,
      badge: watchlistCount > 0 ? String(watchlistCount) : undefined,
    },
  ];

  return (
    <div className="min-h-screen flex bg-shelf-bg text-slate-100">
      {/* Right Sidebar (RTL) */}
      <aside className="w-64 shrink-0 bg-shelf-card border-l border-shelf-border flex flex-col justify-between p-4 sticky top-0 h-screen overflow-y-auto">
        <div className="space-y-6">
          {/* Brand Logo */}
          <div className="flex items-center justify-between px-2 py-1">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-shelf-amber flex items-center justify-center text-black font-black shadow-lg shadow-shelf-amber/20">
                <Disc className="w-5 h-5" />
              </div>
              <div>
                <h1 className="font-bold text-base tracking-tight text-white">CinemaShelf</h1>
                <p className="text-[11px] text-slate-400">آرشیو و مدیاسنتر شخصی</p>
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5">
            <p className="px-3 text-[11px] font-semibold text-slate-500 uppercase">قفسه‌ها و آرشیو</p>
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) =>
                    `flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-shelf-amber text-black font-bold shadow-md shadow-shelf-amber/10'
                        : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                    }`
                  }
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-4 h-4 shrink-0" />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-black/20 font-mono">
                      {item.badge}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Storage Drives Status Widget */}
        <div className="space-y-3 border-t border-shelf-border pt-4">
          <div className="flex items-center justify-between text-xs text-slate-400 px-1">
            <span className="font-semibold flex items-center gap-1.5">
              <HardDrive className="w-3.5 h-3.5 text-shelf-amber" />
              وضعیت هاردها و دیسک‌ها
            </span>
            <button
              onClick={() => setIsManageLibrariesOpen(true)}
              className="p-1 hover:text-shelf-amber transition rounded text-slate-400 hover:text-slate-200"
              title="مدیریت کتابخانه‌ها و ریشه‌ها"
            >
              <FolderOpen className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2.5">
            {volumes.length === 0 && (
              <div className="p-2 text-center text-[11px] text-slate-500">
                در حال بررسی درایوهای ذخیره‌سازی...
              </div>
            )}

            {volumes.map((drive) => {
              const usedGb = (drive.used_bytes / (1024 * 1024 * 1024)).toFixed(1);
              const totalGb = (drive.total_bytes / (1024 * 1024 * 1024)).toFixed(1);
              const pct =
                drive.total_bytes > 0
                  ? Math.round((drive.used_bytes / drive.total_bytes) * 100)
                  : 0;

              return (
                <div
                  key={drive.id}
                  className="p-2.5 rounded-lg bg-shelf-bg/80 border border-shelf-border/80 space-y-1.5"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono font-medium truncate max-w-[140px]" dir="ltr" title={drive.mount_path}>
                      {drive.label}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full ${
                        drive.is_online
                          ? 'bg-emerald-500/15 text-emerald-400'
                          : 'bg-red-500/15 text-red-400'
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          drive.is_online ? 'bg-emerald-400' : 'bg-red-400'
                        }`}
                      />
                      {drive.is_online ? 'متصل' : 'قطع'}
                    </span>
                  </div>

                  <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${
                        !drive.is_online
                          ? 'bg-red-500/50'
                          : pct > 90
                          ? 'bg-amber-500'
                          : 'bg-emerald-500'
                      }`}
                      style={{ width: drive.is_online ? `${pct}%` : '0%' }}
                    />
                  </div>

                  <div className="flex justify-between text-[10px] text-slate-400 font-mono" dir="ltr">
                    <span>{usedGb} GB used</span>
                    <span>{totalGb} GB</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Clean Top Header */}
        <header className="h-16 border-b border-shelf-border bg-shelf-card/60 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-20">
          <div className="relative w-96">
            <Search className="w-4 h-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="جستجوی فیلم در کتابخانه..."
              className="w-full bg-shelf-bg border border-shelf-border rounded-lg pr-10 pl-4 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-shelf-amber"
            />
          </div>

          <div className="flex items-center gap-3">
            {/* Manage Libraries Button */}
            <button
              onClick={() => setIsManageLibrariesOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-shelf-border font-medium text-xs transition"
              title="مدیریت و اسکن ریشه‌های ذخیره‌سازی"
            >
              <FolderOpen className="w-3.5 h-3.5 text-shelf-amber" />
              <span>مدیریت کتابخانه‌ها</span>
            </button>

            {/* Add Movie / TMDB Search Button */}
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-shelf-amber hover:bg-shelf-amberHover text-black font-bold text-xs shadow-md shadow-shelf-amber/10 transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>افزودن فیلم / جستجوی TMDB</span>
            </button>

            <div className="hidden sm:flex items-center gap-2 text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1.5 rounded-lg">
              <RefreshCw className="w-3.5 h-3.5" />
              <span>سینک Letterboxd فعال</span>
            </div>

            <NavLink
              to="/watchlist"
              className={`flex items-center gap-2 text-xs border px-3 py-1.5 rounded-lg font-mono transition ${
                !isOnline
                  ? 'bg-red-500/10 border-red-500/30 text-red-400 hover:border-red-500/50'
                  : 'bg-shelf-bg border-shelf-border hover:border-slate-600'
              }`}
              dir="ltr"
            >
              <Download
                className={`w-3.5 h-3.5 ${!isOnline ? 'text-red-400' : 'text-shelf-amber'}`}
              />
              <span>
                {!isOnline
                  ? 'Aria2: آفلاین'
                  : `Aria2: ${speedMbps} MB/s ${activeCount > 0 ? `(${activeCount})` : ''}`}
              </span>
            </NavLink>
          </div>
        </header>

        {/* Disconnected Drive Banner (if any) */}
        {hasDisconnectedVolumes && (
          <div className="mx-6 mt-4 px-4 py-2.5 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center justify-between text-xs text-red-200 animate-in fade-in">
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
              <span>
                هارد دیسک{' '}
                <strong className="font-mono text-white">
                  {disconnectedVolumes[0]?.label || 'اکسترنال'}
                </strong>{' '}
                قطع است. فیلم‌های موجود روی این هارد در حالت «آرشیو آفلاین» نمایش داده می‌شوند.
              </span>
            </div>
          </div>
        )}

        <main className="p-6 flex-1">
          <Outlet />
        </main>
      </div>

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
