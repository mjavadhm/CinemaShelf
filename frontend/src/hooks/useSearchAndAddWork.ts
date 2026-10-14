import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  addLibraryItem,
  createDownloadTask,
  discoverReleases,
  ingestWork,
  listReleases,
  searchMetadata,
  toggleWatchlist,
} from '../api/endpoints';
import { ExternalSearchResult, WorkType } from '../types/api';

export function useSearchAndAddWork() {
  const queryClient = useQueryClient();
  const [queryText, setQueryText] = useState('');
  const [selectedType, setSelectedType] = useState<WorkType>('MOVIE');

  // Search query
  const searchQuery = useQuery({
    queryKey: ['metadata-search', queryText, selectedType],
    queryFn: () => searchMetadata(queryText.trim(), undefined, selectedType),
    enabled: queryText.trim().length >= 2,
    staleTime: 60000,
  });

  // Add work to library
  const addToLibraryMutation = useMutation({
    mutationFn: (tmdbId: number) =>
      addLibraryItem({
        tmdb_id: tmdbId,
        work_type: selectedType,
        status: 'WANTED',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['library-items'] });
    },
  });

  // Add work to watchlist
  const addToWatchlistMutation = useMutation({
    mutationFn: async (tmdbId: number) => {
      // First ingest work
      const work = await ingestWork(tmdbId, selectedType);
      // Then mark in watchlist
      return await toggleWatchlist(work.id, true);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist-works'] });
      queryClient.invalidateQueries({ queryKey: ['personal-record'] });
    },
  });

  // Discover Zarfilm releases
  const discoverReleasesMutation = useMutation({
    mutationFn: (workId: number) => discoverReleases(workId),
    onSuccess: (_, workId) => {
      queryClient.invalidateQueries({ queryKey: ['work-releases', workId] });
    },
  });

  // Trigger download
  const triggerDownloadMutation = useMutation({
    mutationFn: ({
      libraryItemId,
      releaseId,
      downloadUrl,
    }: {
      libraryItemId: number;
      releaseId?: number;
      downloadUrl?: string;
    }) =>
      createDownloadTask({
        library_item_id: libraryItemId,
        release_id: releaseId,
        download_url: downloadUrl,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads-queue'] });
      queryClient.invalidateQueries({ queryKey: ['library-items'] });
    },
  });

  return {
    queryText,
    setQueryText,
    selectedType,
    setSelectedType,
    searchResults: (searchQuery.data || []) as ExternalSearchResult[],
    isSearching: searchQuery.isLoading && searchQuery.fetchStatus !== 'idle',
    addToLibrary: (tmdbId: number) => addToLibraryMutation.mutateAsync(tmdbId),
    isAddingToLibrary: addToLibraryMutation.isPending,
    addToWatchlist: (tmdbId: number) => addToWatchlistMutation.mutateAsync(tmdbId),
    isAddingToWatchlist: addToWatchlistMutation.isPending,
    discoverReleases: (workId: number) => discoverReleasesMutation.mutateAsync(workId),
    isDiscoveringReleases: discoverReleasesMutation.isPending,
    triggerDownload: (payload: { libraryItemId: number; releaseId?: number; downloadUrl?: string }) =>
      triggerDownloadMutation.mutateAsync(payload),
    isTriggeringDownload: triggerDownloadMutation.isPending,
  };
}

export function useWorkReleases(workId: number | undefined) {
  return useQuery({
    queryKey: ['work-releases', workId],
    queryFn: () => listReleases(workId!),
    enabled: Boolean(workId),
  });
}
