import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  addLibraryRoot,
  browseServerDirectories,
  createLibrary,
  deleteLibrary,
  getLibraries,
  getLibraryScanJobs,
  removeLibraryRoot,
  triggerLibraryScan,
} from '../api/endpoints';

export function useLibraries() {
  const queryClient = useQueryClient();

  const librariesQuery = useQuery({
    queryKey: ['libraries'],
    queryFn: () => getLibraries(),
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; content_type?: string; preferred_language?: string }) =>
      createLibrary(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['libraries'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteLibrary(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['libraries'] });
    },
  });

  const addRootMutation = useMutation({
    mutationFn: ({ libraryId, data }: { libraryId: number; data: { label: string; mount_path: string } }) =>
      addLibraryRoot(libraryId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['libraries'] });
      queryClient.invalidateQueries({ queryKey: ['storage-volumes'] });
    },
  });

  const removeRootMutation = useMutation({
    mutationFn: (rootId: number) => removeLibraryRoot(rootId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['libraries'] });
      queryClient.invalidateQueries({ queryKey: ['storage-volumes'] });
    },
  });

  const scanMutation = useMutation({
    mutationFn: ({ libraryId, rootId }: { libraryId: number; rootId?: number }) =>
      triggerLibraryScan(libraryId, rootId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['libraries'] });
      queryClient.invalidateQueries({ queryKey: ['library-items'] });
      queryClient.invalidateQueries({ queryKey: ['scan-jobs', variables.libraryId] });
      queryClient.invalidateQueries({ queryKey: ['storage-volumes'] });
    },
  });

  return {
    libraries: librariesQuery.data || [],
    isLoading: librariesQuery.isLoading,
    isError: librariesQuery.isError,
    createLibrary: (data: { name: string; content_type?: string; preferred_language?: string }) =>
      createMutation.mutateAsync(data),
    deleteLibrary: (id: number) => deleteMutation.mutateAsync(id),
    addRoot: (libraryId: number, data: { label: string; mount_path: string }) =>
      addRootMutation.mutateAsync({ libraryId, data }),
    removeRoot: (rootId: number) => removeRootMutation.mutateAsync(rootId),
    triggerScan: (libraryId: number, rootId?: number) =>
      scanMutation.mutateAsync({ libraryId, rootId }),
    isCreating: createMutation.isPending,
    isScanning: scanMutation.isPending,
    isAddingRoot: addRootMutation.isPending,
  };
}

export function useDirectoryBrowser(initialPath?: string) {
  return useQuery({
    queryKey: ['server-directories', initialPath],
    queryFn: () => browseServerDirectories(initialPath),
  });
}

export function useLibraryScanJobs(libraryId?: number) {
  return useQuery({
    queryKey: ['scan-jobs', libraryId],
    queryFn: () => getLibraryScanJobs(libraryId!),
    enabled: Boolean(libraryId),
  });
}
