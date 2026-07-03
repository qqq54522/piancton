import { useCallback, useMemo, useState } from 'react';
import type { TagWithCount } from '@client/src/types/api';

interface UseImageFiltersParams {
  parentTagId?: string;
  allTags: TagWithCount[];
}

export function useImageFilters({ parentTagId, allTags }: UseImageFiltersParams) {
  const [keyword, setKeyword] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [filterTagIds, setFilterTagIds] = useState<string[]>([]);
  const [filterKeyword, setFilterKeyword] = useState('');
  const [sortBy, setSortBy] = useState<'createdAt' | 'downloadCount'>('createdAt');
  const [filterCategory, setFilterCategory] = useState<string | undefined>();

  const effectiveTagIds = useMemo(
    () => filterTagIds.length
      ? filterTagIds
      : parentTagId && !keyword && !filterKeyword
        ? [parentTagId]
        : undefined,
    [filterKeyword, filterTagIds, keyword, parentTagId],
  );

  const handleFilter = useCallback((tagIds: string[], value: string, category?: string) => {
    setFilterTagIds(tagIds);
    setFilterKeyword(value);
    setFilterCategory(category);
  }, []);

  const clearFilter = useCallback(() => {
    setFilterTagIds([]);
    setFilterKeyword('');
    setFilterCategory(undefined);
    setKeyword('');
    setSearchInput('');
  }, []);

  const hasActiveFilter = filterTagIds.length > 0 || Boolean(filterKeyword || filterCategory);
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

  return {
    clearFilter,
    effectiveTagIds,
    filterCategory,
    filterLabel,
    filterTagIds,
    filterKeyword,
    handleFilter,
    hasActiveFilter,
    keyword,
    searchInput,
    setFilterCategory,
    setKeyword,
    setSearchInput,
    setSortBy,
    sortBy,
  };
}
