import {
  useCallback,
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query';

import * as imageApi from '@client/src/api/image';
import { tagQueryKey, useTags } from '@client/src/features/tags/useTags';
import type {
  ImageItem,
  SemanticSearchResponse,
  SearchMode,
  TagWithCount,
} from '@client/src/types/api';


interface SearchResult {
  semantic: SemanticSearchResponse | null;
  images: ImageItem[];
}

export function useImageBrowser(parentTagId: string | undefined, isDesigner: boolean) {
  const queryClient = useQueryClient();
  const { data: allTags = [] } = useTags();
  const [keyword, setKeyword] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [filterTagIds, setFilterTagIds] = useState<string[]>([]);
  const [filterKeyword, setFilterKeyword] = useState('');
  const [sortBy, setSortBy] = useState<'createdAt' | 'downloadCount'>('createdAt');
  const [filterCategory, setFilterCategory] = useState<string | undefined>();
  const [globalSearchInput, setGlobalSearchInput] = useState('');
  const [globalSearchKeyword, setGlobalSearchKeyword] = useState('');
  const [globalSearchMode, setGlobalSearchMode] = useState<SearchMode>('precise');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [tagPanelOpen, setTagPanelOpen] = useState(false);
  const [filterDialogOpen, setFilterDialogOpen] = useState(false);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const deferredGlobalInput = useDeferredValue(globalSearchInput.trim().toLowerCase());

  const currentTag = useMemo(
    () => parentTagId ? allTags.find((tag) => tag.id === parentTagId) ?? null : null,
    [allTags, parentTagId],
  );
  const childTags = useMemo(
    () => allTags.filter((tag) => parentTagId ? tag.parentId === parentTagId : !tag.parentId),
    [allTags, parentTagId],
  );
  const effectiveTagIds = filterTagIds.length
    ? filterTagIds
    : parentTagId && !keyword && !filterKeyword
      ? [parentTagId]
      : undefined;

  const imageQuery = useInfiniteQuery({
    queryKey: [
      'images',
      parentTagId ?? '',
      keyword,
      filterTagIds,
      filterKeyword,
      sortBy,
      filterCategory ?? '',
    ],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => imageApi.fetchImages({
      keyword: filterKeyword || keyword || undefined,
      tagIds: effectiveTagIds,
      cursor: pageParam,
      limit: 12,
      sortBy,
      category: filterCategory,
    }),
    getNextPageParam: (page) => page.hasMore ? page.nextCursor : undefined,
  });

  const images = useMemo(
    () => imageQuery.data?.pages.flatMap((page) => page.items) ?? [],
    [imageQuery.data],
  );
  const {
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = imageQuery;

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

  const semanticSearch = useMutation({
    mutationFn: async (
      payload: { keyword: string; searchMode: SearchMode },
    ): Promise<SearchResult> => {
      try {
        const semantic = await imageApi.semanticSearch({
          keyword: payload.keyword,
          limit: 12,
          searchMode: payload.searchMode,
        });
        return { semantic, images: semantic.results.map((result) => result.image) };
      } catch {
        const fallback = await imageApi.fetchImages({ keyword: payload.keyword, limit: 12 });
        return { semantic: null, images: fallback.items };
      }
    },
  });
  const {
    data: semanticData,
    isPending: semanticPending,
    mutate: runSemanticSearch,
    reset: resetSemanticSearch,
  } = semanticSearch;

  const globalSearchTags = useMemo(() => {
    if (!deferredGlobalInput || globalSearchKeyword) return [];
    return allTags
      .filter((tag) => tag.name.toLowerCase().includes(deferredGlobalInput))
      .slice(0, 8);
  }, [allTags, deferredGlobalInput, globalSearchKeyword]);

  const executeGlobalSearch = useCallback((value?: string) => {
    const nextKeyword = (value ?? globalSearchInput).trim();
    if (!nextKeyword) return;
    setGlobalSearchInput(nextKeyword);
    setGlobalSearchKeyword(nextKeyword);
    runSemanticSearch({ keyword: nextKeyword, searchMode: globalSearchMode });
  }, [globalSearchInput, globalSearchMode, runSemanticSearch]);

  const handleFilter = useCallback((tagIds: string[], value: string, category?: string) => {
    setFilterTagIds(tagIds);
    setFilterKeyword(value);
    setFilterCategory(category);
    setGlobalSearchKeyword('');
    setGlobalSearchInput('');
    resetSemanticSearch();
  }, [resetSemanticSearch]);

  const handleTagSuggestClick = useCallback((tag: TagWithCount) => {
    setGlobalSearchInput(tag.name);
    handleFilter([tag.id], '', undefined);
  }, [handleFilter]);

  const clearFilter = useCallback(() => {
    setFilterTagIds([]);
    setFilterKeyword('');
    setFilterCategory(undefined);
    setKeyword('');
    setSearchInput('');
  }, []);

  const clearGlobalSearch = useCallback(() => {
    setGlobalSearchInput('');
    setGlobalSearchKeyword('');
    resetSemanticSearch();
  }, [resetSemanticSearch]);

  const handleUploadSuccess = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: tagQueryKey });
    queryClient.invalidateQueries({ queryKey: ['images'] });
  }, [queryClient]);

  const hasActiveFilter = filterTagIds.length > 0 || Boolean(filterKeyword || filterCategory);
  const isRoot = !parentTagId;
  const showChildTags = childTags.length > 0 && !hasActiveFilter && (!isRoot || isDesigner);
  const showImages = !showChildTags && (Boolean(parentTagId) || hasActiveFilter || isRoot);
  const filterLabel = useMemo(() => {
    if (!hasActiveFilter) return '';
    const parts = filterTagIds
      .map((id) => allTags.find((tag) => tag.id === id)?.name)
      .filter((name): name is string => Boolean(name));
    if (filterKeyword) parts.push(`"${filterKeyword}"`);
    if (filterCategory === 'scene') parts.push('场景');
    if (filterCategory === 'function') parts.push('功能');
    return parts.join(' + ');
  }, [allTags, filterCategory, filterKeyword, filterTagIds, hasActiveFilter]);

  const breadcrumb = useMemo(() => {
    const trail: Array<{ id: string | null; name: string }> = [{ id: null, name: '图片库' }];
    if (!currentTag) return trail;
    const path: Array<{ id: string; name: string }> = [];
    const seen = new Set<string>();
    let tag: TagWithCount | undefined = currentTag;
    while (tag && !seen.has(tag.id)) {
      seen.add(tag.id);
      path.unshift({ id: tag.id, name: tag.name || '未命名' });
      tag = tag.parentId ? allTags.find((item) => item.id === tag?.parentId) : undefined;
    }
    return [...trail, ...path];
  }, [allTags, currentTag]);

  return {
    allTags,
    breadcrumb,
    childTags,
    clearFilter,
    clearGlobalSearch,
    currentTag,
    executeGlobalSearch,
    filterCategory,
    filterDialogOpen,
    filterLabel,
    filterTagIds,
    filterKeyword,
    globalSearchImages: semanticData?.images ?? [],
    globalSearchInput,
    globalSearchKeyword,
    globalSearchLoading: semanticPending,
    globalSearchMode,
    globalSearchTags,
    handleFilter,
    handleTagSuggestClick,
    handleUploadSuccess,
    hasActiveFilter,
    hasMore: Boolean(hasNextPage),
    images,
    isRoot,
    keyword,
    loading: imageQuery.isLoading,
    loadingMore: isFetchingNextPage,
    pageTitle: isRoot ? '图片库' : currentTag?.name || '加载中...',
    searchInput,
    semanticResult: semanticData?.semantic ?? null,
    sentinelRef,
    setFilterCategory,
    setFilterDialogOpen,
    setGlobalSearchInput,
    setGlobalSearchMode,
    setKeyword,
    setSearchInput,
    setSortBy,
    setTagPanelOpen,
    setUploadOpen,
    showChildTags,
    showImages,
    sortBy,
    tagPanelOpen,
    uploadOpen,
  };
}
