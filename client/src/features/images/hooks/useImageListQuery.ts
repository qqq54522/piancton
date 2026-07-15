import { useEffect, useMemo, useRef } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';

import * as imageApi from '@client/src/api/image';

export function useImageListQuery(
  keyword: string,
  sortBy: 'createdAt' | 'downloadCount',
) {
  const sentinelRef = useRef<HTMLDivElement>(null);
  const imageQuery = useInfiniteQuery({
    queryKey: ['images', keyword, sortBy],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => imageApi.fetchImages({
      keyword: keyword || undefined,
      cursor: pageParam,
      limit: 12,
      sortBy,
    }),
    getNextPageParam: (page) => page.hasMore ? page.nextCursor : undefined,
  });
  const images = useMemo(
    () => imageQuery.data?.pages.flatMap((page) => page.items) ?? [],
    [imageQuery.data],
  );
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = imageQuery;

  useEffect(() => {
    const element = sentinelRef.current;
    if (!element) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { rootMargin: '200px' },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  return {
    hasMore: Boolean(hasNextPage),
    images,
    loading: imageQuery.isLoading,
    loadingMore: isFetchingNextPage,
    sentinelRef,
  };
}
