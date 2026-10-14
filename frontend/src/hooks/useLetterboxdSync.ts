import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { importLetterboxdFile, listSyncRuns } from '../api/endpoints';

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
    },
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
  };
}
