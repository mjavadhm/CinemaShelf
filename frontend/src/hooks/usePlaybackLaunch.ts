import { useMutation, useQueryClient } from '@tanstack/react-query';
import { openFileLocation, openMediaFile, openWork } from '../api/endpoints';

export function usePlaybackLaunch() {
  const queryClient = useQueryClient();

  const openFileMutation = useMutation({
    mutationFn: (mediaFileId: number) => openMediaFile(mediaFileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watch-status'] });
      queryClient.invalidateQueries({ queryKey: ['personal-record'] });
    },
  });

  const openWorkMutation = useMutation({
    mutationFn: ({ workId, episodeId }: { workId: number; episodeId?: number }) =>
      openWork(workId, episodeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watch-status'] });
      queryClient.invalidateQueries({ queryKey: ['personal-record'] });
    },
  });

  const openLocationMutation = useMutation({
    mutationFn: (mediaFileId: number) => openFileLocation(mediaFileId),
  });

  return {
    openMediaFile: (mediaFileId: number) => openFileMutation.mutateAsync(mediaFileId),
    openWork: (workId: number, episodeId?: number) =>
      openWorkMutation.mutateAsync({ workId, episodeId }),
    openFileLocation: (mediaFileId: number) => openLocationMutation.mutateAsync(mediaFileId),
    isOpening: openFileMutation.isPending || openWorkMutation.isPending,
    isOpeningLocation: openLocationMutation.isPending,
  };
}
