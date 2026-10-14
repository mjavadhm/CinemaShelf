import { useQuery } from '@tanstack/react-query';
import { getStorageVolumes } from '../api/endpoints';

export function useStorageVolumes() {
  const query = useQuery({
    queryKey: ['storage-volumes'],
    queryFn: () => getStorageVolumes(),
    refetchInterval: 10000,
  });

  const volumes = query.data || [];
  const disconnectedVolumes = volumes.filter((v) => !v.is_online);

  return {
    ...query,
    volumes,
    disconnectedVolumes,
    hasDisconnectedVolumes: disconnectedVolumes.length > 0,
  };
}
