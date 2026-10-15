import { useMutation, useQueryClient } from '@tanstack/react-query';
import { openDirectory, openFileLocation, openMediaFile, openWork } from '../api/endpoints';

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

  const openDirectoryMutation = useMutation({
    mutationFn: (path: string) => openDirectory(path),
  });

  return {
    openMediaFile: (mediaFileId: number) => openFileMutation.mutateAsync(mediaFileId),
    openWork: (workId: number, episodeId?: number) =>
      openWorkMutation.mutateAsync({ workId, episodeId }),
    openFileLocation: (mediaFileId: number) => openLocationMutation.mutateAsync(mediaFileId),
    openDirectoryPath: (path: string) => openDirectoryMutation.mutateAsync(path),
    isOpening: openFileMutation.isPending || openWorkMutation.isPending,
    isOpeningLocation: openLocationMutation.isPending,
  };
}
