import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  filterPersonalCatalog,
  getPersonalRecord,
  logWatchDiary,
  rateWork,
  toggleFavorite,
  toggleWatchlist,
  updatePersonalRecord,
} from '../api/endpoints';

export function usePersonalActions(workId?: number) {
  const queryClient = useQueryClient();

  const recordQuery = useQuery({
    queryKey: ['personal-record', workId],
    queryFn: () => getPersonalRecord(workId!),
    enabled: Boolean(workId),
    retry: false,
  });

  const watchlistMutation = useMutation({
    mutationFn: ({ id, inWatchlist }: { id: number; inWatchlist?: boolean }) =>
      toggleWatchlist(id, inWatchlist),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['personal-record', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['library-items'] });
      queryClient.invalidateQueries({ queryKey: ['watchlist-works'] });
    },
  });

  const favoriteMutation = useMutation({
    mutationFn: ({ id, isFavorite }: { id: number; isFavorite?: boolean }) =>
      toggleFavorite(id, isFavorite),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['personal-record', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['library-items'] });
    },
  });

  const rateMutation = useMutation({
    mutationFn: ({ id, rating }: { id: number; rating: number | null }) =>
      rateWork(id, rating),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['personal-record', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['library-items'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      updatePersonalRecord(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['personal-record', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['library-items'] });
    },
  });

  const diaryMutation = useMutation({
    mutationFn: (payload: any) => logWatchDiary(payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['personal-record', variables.work_id] });
      queryClient.invalidateQueries({ queryKey: ['watch-status', variables.work_id] });
      queryClient.invalidateQueries({ queryKey: ['library-items'] });
    },
  });

  return {
    record: recordQuery.data,
    isLoadingRecord: recordQuery.isLoading,
    toggleWatchlist: (id: number, inWatchlist?: boolean) =>
      watchlistMutation.mutateAsync({ id, inWatchlist }),
    toggleFavorite: (id: number, isFavorite?: boolean) =>
      favoriteMutation.mutateAsync({ id, isFavorite }),
    rateWork: (id: number, rating: number | null) =>
      rateMutation.mutateAsync({ id, rating }),
    updateRecord: (id: number, data: any) =>
      updateMutation.mutateAsync({ id, data }),
    logDiary: (payload: any) => diaryMutation.mutateAsync(payload),
    isTogglingWatchlist: watchlistMutation.isPending,
    isRating: rateMutation.isPending,
    isFavoriting: favoriteMutation.isPending,
  };
}

export function useWatchlistWorks() {
  return useQuery({
    queryKey: ['watchlist-works'],
    queryFn: () => filterPersonalCatalog({ in_watchlist: true, limit: 100 }),
  });
}
