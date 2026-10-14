import { useQuery } from '@tanstack/react-query';
import {
  getLibraryItemByWork,
  getPersonalRecord,
  getWatchStatus,
  getWorkDetails,
} from '../api/endpoints';

export function useWorkDetails(workId: number | string | undefined) {
  const numericId = typeof workId === 'string' ? parseInt(workId, 10) : workId;
  const isValid = Boolean(numericId && !isNaN(numericId));

  const workQuery = useQuery({
    queryKey: ['work-details', numericId],
    queryFn: () => getWorkDetails(numericId!),
    enabled: isValid,
  });

  const personalQuery = useQuery({
    queryKey: ['personal-record', numericId],
    queryFn: () => getPersonalRecord(numericId!),
    enabled: isValid,
    retry: false,
  });

  const libraryQuery = useQuery({
    queryKey: ['library-item-by-work', numericId],
    queryFn: () => getLibraryItemByWork(numericId!),
    enabled: isValid,
    retry: false,
  });

  const watchStatusQuery = useQuery({
    queryKey: ['watch-status', numericId],
    queryFn: () => getWatchStatus(numericId!),
    enabled: isValid,
    retry: false,
  });

  const isLoading =
    workQuery.isLoading ||
    (personalQuery.isLoading && personalQuery.fetchStatus !== 'idle') ||
    (libraryQuery.isLoading && libraryQuery.fetchStatus !== 'idle');

  return {
    work: workQuery.data,
    personalRecord: personalQuery.data,
    libraryItem: libraryQuery.data,
    mediaFiles: libraryQuery.data?.media_files || [],
    watchStatus: watchStatusQuery.data,
    isLoading,
    isError: workQuery.isError,
    error: workQuery.error,
    refetchAll: () => {
      workQuery.refetch();
      personalQuery.refetch();
      libraryQuery.refetch();
      watchStatusQuery.refetch();
    },
  };
}
