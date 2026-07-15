import { useCallback, useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import * as imageApi from '@client/src/api/image';
import { systemFilters } from '@client/src/features/assets/assetPresentation';
import type { ImageItem, SemanticSearchResponse, TagWithCount } from '@client/src/types/api';

interface SearchResult {
  semantic: SemanticSearchResponse | null;
  images: ImageItem[];
}

export function useGlobalImageSearch({ allTags }: { allTags: TagWithCount[] }) {
  const [globalSearchInput, setGlobalSearchInput] = useState('');
  const [globalSearchKeyword, setGlobalSearchKeyword] = useState('');
  const [selectedSystemCode, setSelectedSystemCode] = useState<string | null>(null);
  const systems = useMemo(
    () => systemFilters(allTags),
    [allTags],
  );

  const semanticSearch = useMutation({
    mutationFn: async (payload: {
      keyword: string;
      systemCode: string | null;
    }): Promise<SearchResult> => {
      try {
        const semantic = await imageApi.semanticSearch({
          keyword: payload.keyword,
          limit: 12,
          systemCode: payload.systemCode,
        });
        return { semantic, images: semantic.results.map((result) => result.image) };
      } catch {
        const fallback = await imageApi.fetchImages({
          keyword: payload.keyword,
          limit: 12,
        });
        return { semantic: null, images: fallback.items };
      }
    },
  });

  const executeGlobalSearch = useCallback((value?: string, systemCode?: string | null) => {
    const nextKeyword = (value ?? globalSearchInput).trim();
    if (!nextKeyword) return;
    const nextSystem = systemCode === undefined ? selectedSystemCode : systemCode;
    setGlobalSearchInput(nextKeyword);
    setGlobalSearchKeyword(nextKeyword);
    semanticSearch.mutate({ keyword: nextKeyword, systemCode: nextSystem });
  }, [globalSearchInput, selectedSystemCode, semanticSearch]);

  const selectSystem = useCallback((systemCode: string | null) => {
    setSelectedSystemCode(systemCode);
    if (globalSearchKeyword) executeGlobalSearch(globalSearchKeyword, systemCode);
  }, [executeGlobalSearch, globalSearchKeyword]);

  const clearGlobalSearch = useCallback(() => {
    setGlobalSearchInput('');
    setGlobalSearchKeyword('');
    semanticSearch.reset();
  }, [semanticSearch]);

  return {
    clearGlobalSearch,
    executeGlobalSearch,
    globalSearchImages: semanticSearch.data?.images ?? [],
    globalSearchInput,
    globalSearchKeyword,
    globalSearchLoading: semanticSearch.isPending,
    selectedSystemCode,
    semanticResult: semanticSearch.data?.semantic ?? null,
    setGlobalSearchInput,
    selectSystem,
    systems,
  };
}
