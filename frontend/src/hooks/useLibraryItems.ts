import { useQuery } from '@tanstack/react-query';
import { getLibraryItems } from '../api/endpoints';
import { LibraryItem } from '../types/api';

export interface LibraryFilters {
  status?: string;
  search?: string;
  genre?: string;
  resolution?: string;
  onlineOnly?: boolean;
}

export function useLibraryItems(filters: LibraryFilters = {}) {
  const query = useQuery({
    queryKey: ['library-items', filters.status],
    queryFn: () => getLibraryItems({ status: filters.status, limit: 100 }),
  });

  const allItems: LibraryItem[] = query.data || [];

  // Extract all distinct genres across the fetched items
  const allGenres = Array.from(
    new Set(
      allItems.flatMap((item) =>
        (item.work.genres || []).map((g) => g.persian_name || g.name)
      )
    )
  ).filter(Boolean);

  // Compute filtered items
  const filteredItems = allItems.filter((item) => {
    const movie = item.work;
    const files = item.media_files || [];

    // Search filter
    if (filters.search) {
      const q = filters.search.toLowerCase();
      const titleMatch = movie.title.toLowerCase().includes(q);
      const persianMatch = movie.persian_title?.toLowerCase().includes(q);
      const imdbMatch = movie.imdb_id?.toLowerCase().includes(q);
      if (!titleMatch && !persianMatch && !imdbMatch) {
        return false;
      }
    }

    // Genre filter
    if (filters.genre && filters.genre !== 'ALL') {
      const hasGenre = (movie.genres || []).some(
        (g) => (g.persian_name || g.name) === filters.genre
      );
      if (!hasGenre) return false;
    }

    // Resolution filter
    if (filters.resolution && filters.resolution !== 'ALL') {
      const targetRes = filters.resolution.toLowerCase();
      const hasRes = files.some(
        (f) =>
          f.resolution?.toLowerCase().includes(targetRes) ||
          (targetRes === '4k' && (f.resolution?.includes('2160') || f.source_type?.includes('4K')))
      );
      if (!hasRes) return false;
    }

    // Online drives only
    if (filters.onlineOnly) {
      const hasOnlineFile = files.some((f) => f.is_online);
      if (!hasOnlineFile) return false;
    }

    return true;
  });

  return {
    ...query,
    items: filteredItems,
    allItems,
    allGenres,
    totalCount: allItems.length,
    filteredCount: filteredItems.length,
  };
}
