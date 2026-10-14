import { useQuery } from '@tanstack/react-query';
import { getPersonDetails } from '../api/endpoints';

export function usePersonDetails(personId: number | string | undefined) {
  const numericId = typeof personId === 'string' ? parseInt(personId, 10) : personId;
  const isValid = Boolean(numericId && !isNaN(numericId));

  const query = useQuery({
    queryKey: ['person-details', numericId],
    queryFn: () => getPersonDetails(numericId!),
    enabled: isValid,
  });

  return {
    ...query,
    person: query.data,
    castWorks: query.data?.cast || [],
    crewWorks: query.data?.crew || [],
  };
}
