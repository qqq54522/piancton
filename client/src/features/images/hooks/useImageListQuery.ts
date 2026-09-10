import { useEffect, useMemo, useRef } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';

import * as imageApi from '@client/src/api/image';

export function useImageListQuery(
  keyword: string,
  sortBy: 'createdAt' | 'downloadCount',
  channel: string,
) {
  const sentinelRef = useRef<HTMLDivElement>(null);
  const imageQuery = useInfiniteQuery({
    queryKey: ['images', keyword, sortBy, channel],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => imageApi.fetchImages({
      keyword: keyword || undefined,
      channel: channel || undefined,
      cursor: pageParam,
      limit: 12,
      sortBy,
    }),
    getNextPageParam: (page) => page.hasMore ? page.nextCursor : undefined,
  });
  const channelQuery = useQuery({
    queryKey: ['images', 'channels'],
    queryFn: () => imageApi.fetchImageChannels(),
    staleTime: 30_000,
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
    availableChannels: channelQuery.data?.channels ?? [],
    images,
    loading: imageQuery.isLoading,
    loadingMore: isFetchingNextPage,
    sentinelRef,
  };
}
