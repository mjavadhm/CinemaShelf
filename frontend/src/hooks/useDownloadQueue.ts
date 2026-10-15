import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  cancelDownload,
  createDownloadTask,
  getAria2Stats,
  getDownloadTasks,
  pauseDownload,
  resumeDownload,
  setSpeedLimit,
} from '../api/endpoints';

export function useDownloadQueue() {
  const queryClient = useQueryClient();

  const tasksQuery = useQuery({
    queryKey: ['downloads-queue'],
    queryFn: () => getDownloadTasks({ limit: 100 }),
    refetchInterval: 2000,
  });

  const statsQuery = useQuery({
    queryKey: ['downloads-stats'],
    queryFn: () => getAria2Stats(),
    refetchInterval: 2000,
  });

  const pauseMutation = useMutation({
    mutationFn: (id: number) => pauseDownload(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads-queue'] });
      queryClient.invalidateQueries({ queryKey: ['downloads-stats'] });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: (id: number) => resumeDownload(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads-queue'] });
      queryClient.invalidateQueries({ queryKey: ['downloads-stats'] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (id: number) => cancelDownload(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads-queue'] });
      queryClient.invalidateQueries({ queryKey: ['downloads-stats'] });
    },
  });

  const addMutation = useMutation({
    mutationFn: (payload: {
      library_item_id: number;
      release_id?: number;
      episode_id?: number;
      download_url?: string;
      destination_dir?: string;
      file_name?: string;
    }) => createDownloadTask(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads-queue'] });
      queryClient.invalidateQueries({ queryKey: ['downloads-stats'] });
    },
  });

  const speedLimitMutation = useMutation({
    mutationFn: (limitKb: number) => setSpeedLimit(limitKb),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads-stats'] });
    },
  });

  const tasks = tasksQuery.data || [];
  const stats = statsQuery.data;

  // Active speed in MB/s
  const speedMbps = stats ? (stats.download_speed / (1024 * 1024)).toFixed(1) : '0.0';
  const activeCount = stats?.num_active ?? tasks.filter((t) => t.status === 'ACTIVE').length;
  const queuedCount = stats?.num_waiting ?? tasks.filter((t) => t.status === 'QUEUED').length;
  const isOnline = stats?.is_online ?? true;

  return {
    tasks,
    stats,
    speedMbps,
    activeCount,
    queuedCount,
    isOnline,
    isLoading: tasksQuery.isLoading,
    isError: tasksQuery.isError,
    pauseTask: (id: number) => pauseMutation.mutateAsync(id),
    resumeTask: (id: number) => resumeMutation.mutateAsync(id),
    cancelTask: (id: number) => cancelMutation.mutateAsync(id),
    addTask: (payload: any) => addMutation.mutateAsync(payload),
    setSpeedLimit: (limitKb: number) => speedLimitMutation.mutateAsync(limitKb),
    isPausing: pauseMutation.isPending,
    isResuming: resumeMutation.isPending,
    isCancelling: cancelMutation.isPending,
    isAdding: addMutation.isPending,
  };
}
