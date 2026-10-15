import { useQuery } from '@tanstack/react-query';
import { getLibraryItems } from '../api/endpoints';
import { LibraryItem } from '../types/api';

export interface LibraryFilters {
  status?: string;
  libraryId?: number | null;
  search?: string;
  genre?: string;
  resolution?: string;
  onlineOnly?: boolean;
  page?: number;
  pageSize?: number;
}

export function useLibraryItems(filters: LibraryFilters = {}) {
  const page = filters.page || 1;
  const pageSize = filters.pageSize || 48;
  const searchTrimmed = filters.search?.trim() || undefined;
  const genreParam = filters.genre && filters.genre !== 'ALL' ? filters.genre : undefined;

  const query = useQuery({
    queryKey: [
      'library-items',
      filters.status,
      filters.libraryId,
      searchTrimmed,
      genreParam,
      page,
      pageSize,
    ],
    queryFn: () =>
      getLibraryItems({
        status: filters.status,
        library_id: filters.libraryId || undefined,
        search: searchTrimmed,
        genre: genreParam,
        limit: pageSize,
        page: page,
      }),
  });

  const items = query.data?.items || [];
  const totalCount = query.data?.totalCount || 0;
  const totalPages = query.data?.totalPages || 1;

  // Extract all distinct genres across the fetched items
  const allGenres = Array.from(
    new Set(
      items.flatMap((item) =>
        (item.work.genres || []).map((g) => g.persian_name || g.name)
      )
    )
  ).filter(Boolean);

  // Compute filtered items
  const filteredItems = items.filter((item) => {
    const files = item.media_files || [];

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
    allItems: items,
    allGenres,
    totalCount,
    totalPages,
    currentPage: page,
    pageSize,
    filteredCount: filteredItems.length,
  };
}
