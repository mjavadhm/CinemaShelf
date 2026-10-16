import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  importLetterboxdFile,
  listSyncRuns,
  openLetterboxdBrowser,
  syncLetterboxdLocalHtml,
  syncLetterboxdViaBrowser,
} from '../api/endpoints';

export function useLetterboxdSync() {
  const queryClient = useQueryClient();

  const syncRunsQuery = useQuery({
    queryKey: ['sync-runs'],
    queryFn: () => listSyncRuns({ limit: 10 }),
  });

  const importMutation = useMutation({
    mutationFn: ({
      file,
      conflictPolicy,
      scaleMode,
    }: {
      file: File;
      conflictPolicy?: 'PRESERVE_LOCAL' | 'OVERWRITE_LOCAL';
      scaleMode?: 'RAW' | 'TEN_POINT';
    }) => importLetterboxdFile(file, conflictPolicy, scaleMode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sync-runs'] });
      queryClient.invalidateQueries({ queryKey: ['library-items'] });
      queryClient.invalidateQueries({ queryKey: ['watchlist-works'] });
      queryClient.invalidateQueries({ queryKey: ['personal-record'] });
      queryClient.invalidateQueries({ queryKey: ['work-details'] });
    },
  });

  const localSyncMutation = useMutation({
    mutationFn: ({
      folderPath,
      conflictPolicy,
      scaleMode,
    }: {
      folderPath?: string;
      conflictPolicy?: 'PRESERVE_LOCAL' | 'OVERWRITE_LOCAL';
      scaleMode?: 'RAW' | 'TEN_POINT';
    }) => syncLetterboxdLocalHtml(folderPath, conflictPolicy, scaleMode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sync-runs'] });
      queryClient.invalidateQueries({ queryKey: ['library-items'] });
      queryClient.invalidateQueries({ queryKey: ['watchlist-works'] });
      queryClient.invalidateQueries({ queryKey: ['personal-record'] });
      queryClient.invalidateQueries({ queryKey: ['work-details'] });
    },
  });

  const browserSyncMutation = useMutation({
    mutationFn: ({
      username,
      includeWatchlist,
      maxPages,
      conflictPolicy,
      scaleMode,
    }: {
      username: string;
      includeWatchlist?: boolean;
      maxPages?: number;
      conflictPolicy?: 'PRESERVE_LOCAL' | 'OVERWRITE_LOCAL';
      scaleMode?: 'RAW' | 'TEN_POINT';
    }) =>
      syncLetterboxdViaBrowser(
        username,
        includeWatchlist,
        maxPages,
        conflictPolicy,
        scaleMode
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sync-runs'] });
      queryClient.invalidateQueries({ queryKey: ['library-items'] });
      queryClient.invalidateQueries({ queryKey: ['watchlist-works'] });
      queryClient.invalidateQueries({ queryKey: ['personal-record'] });
      queryClient.invalidateQueries({ queryKey: ['work-details'] });
    },
  });

  const openBrowserMutation = useMutation({
    mutationFn: (url?: string) => openLetterboxdBrowser(url),
  });

  return {
    syncRuns: syncRunsQuery.data || [],
    isLoadingRuns: syncRunsQuery.isLoading,
    importFile: (params: {
      file: File;
      conflictPolicy?: 'PRESERVE_LOCAL' | 'OVERWRITE_LOCAL';
      scaleMode?: 'RAW' | 'TEN_POINT';
    }) => importMutation.mutateAsync(params),
    isImporting: importMutation.isPending,
    importResult: importMutation.data,
    importError: importMutation.error,

    syncLocalHtml: (params?: {
      folderPath?: string;
      conflictPolicy?: 'PRESERVE_LOCAL' | 'OVERWRITE_LOCAL';
      scaleMode?: 'RAW' | 'TEN_POINT';
    }) => localSyncMutation.mutateAsync(params || {}),
    isSyncingLocal: localSyncMutation.isPending,
    localSyncError: localSyncMutation.error,

    syncViaBrowser: (params: {
      username: string;
      includeWatchlist?: boolean;
      maxPages?: number;
      conflictPolicy?: 'PRESERVE_LOCAL' | 'OVERWRITE_LOCAL';
      scaleMode?: 'RAW' | 'TEN_POINT';
    }) => browserSyncMutation.mutateAsync(params),
    isSyncingBrowser: browserSyncMutation.isPending,
    browserSyncError: browserSyncMutation.error,

    openBrowser: (url?: string) => openBrowserMutation.mutateAsync(url),
    isOpeningBrowser: openBrowserMutation.isPending,
  };
}
