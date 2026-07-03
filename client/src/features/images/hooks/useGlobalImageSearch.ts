import { useCallback, useDeferredValue, useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import * as imageApi from '@client/src/api/image';
import type {
  ImageItem,
  SearchMode,
  SemanticSearchResponse,
  TagWithCount,
} from '@client/src/types/api';

interface SearchResult {
  semantic: SemanticSearchResponse | null;
  images: ImageItem[];
}

interface UseGlobalImageSearchParams {
  allTags: TagWithCount[];
}

export function useGlobalImageSearch({ allTags }: UseGlobalImageSearchParams) {
  const [globalSearchInput, setGlobalSearchInput] = useState('');
  const [globalSearchKeyword, setGlobalSearchKeyword] = useState('');
  const [globalSearchMode, setGlobalSearchMode] = useState<SearchMode>('precise');
  const deferredGlobalInput = useDeferredValue(globalSearchInput.trim().toLowerCase());

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

  const clearGlobalSearch = useCallback(() => {
    setGlobalSearchInput('');
    setGlobalSearchKeyword('');
    resetSemanticSearch();
  }, [resetSemanticSearch]);

  return {
    clearGlobalSearch,
    executeGlobalSearch,
    globalSearchImages: semanticData?.images ?? [],
    globalSearchInput,
    globalSearchKeyword,
    globalSearchLoading: semanticPending,
    globalSearchMode,
    globalSearchTags,
    semanticResult: semanticData?.semantic ?? null,
    setGlobalSearchInput,
    setGlobalSearchMode,
  };
}
