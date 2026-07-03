import { useCallback } from 'react';

import { useTags } from '@client/src/features/tags/useTags';
import type { TagWithCount } from '@client/src/types/api';
import { useGlobalImageSearch } from './hooks/useGlobalImageSearch';
import { useImageBrowserUi } from './hooks/useImageBrowserUi';
import { useImageFilters } from './hooks/useImageFilters';
import { useImageListQuery } from './hooks/useImageListQuery';

export function useImageBrowser(parentTagId: string | undefined, isDesigner: boolean) {
  const { data: allTags = [] } = useTags();
  const filters = useImageFilters({ parentTagId, allTags });
  const global = useGlobalImageSearch({ allTags });
  const ui = useImageBrowserUi({
    parentTagId,
    allTags,
    isDesigner,
    hasActiveFilter: filters.hasActiveFilter,
  });
  const list = useImageListQuery({
    parentTagId,
    keyword: filters.keyword,
    filterKeyword: filters.filterKeyword,
    filterTagIds: filters.filterTagIds,
    effectiveTagIds: filters.effectiveTagIds,
    sortBy: filters.sortBy,
    filterCategory: filters.filterCategory,
  });

  const handleFilter = useCallback((tagIds: string[], value: string, category?: string) => {
    filters.handleFilter(tagIds, value, category);
    global.clearGlobalSearch();
  }, [filters, global]);

  const handleTagSuggestClick = useCallback((tag: TagWithCount) => {
    global.setGlobalSearchInput(tag.name);
    handleFilter([tag.id], '', undefined);
  }, [global, handleFilter]);

  return {
    allTags,
    breadcrumb: ui.breadcrumb,
    childTags: ui.childTags,
    clearFilter: filters.clearFilter,
    clearGlobalSearch: global.clearGlobalSearch,
    currentTag: ui.currentTag,
    executeGlobalSearch: global.executeGlobalSearch,
    filterCategory: filters.filterCategory,
    filterDialogOpen: ui.filterDialogOpen,
    filterLabel: filters.filterLabel,
    filterTagIds: filters.filterTagIds,
    filterKeyword: filters.filterKeyword,
    globalSearchImages: global.globalSearchImages,
    globalSearchInput: global.globalSearchInput,
    globalSearchKeyword: global.globalSearchKeyword,
    globalSearchLoading: global.globalSearchLoading,
    globalSearchMode: global.globalSearchMode,
    globalSearchTags: global.globalSearchTags,
    handleFilter,
    handleTagSuggestClick,
    handleUploadSuccess: ui.handleUploadSuccess,
    hasActiveFilter: filters.hasActiveFilter,
    hasMore: list.hasMore,
    images: list.images,
    isRoot: ui.isRoot,
    keyword: filters.keyword,
    loading: list.loading,
    loadingMore: list.loadingMore,
    pageTitle: ui.pageTitle,
    searchInput: filters.searchInput,
    semanticResult: global.semanticResult,
    sentinelRef: list.sentinelRef,
    setFilterCategory: filters.setFilterCategory,
    setFilterDialogOpen: ui.setFilterDialogOpen,
    setGlobalSearchInput: global.setGlobalSearchInput,
    setGlobalSearchMode: global.setGlobalSearchMode,
    setKeyword: filters.setKeyword,
    setSearchInput: filters.setSearchInput,
    setSortBy: filters.setSortBy,
    setTagPanelOpen: ui.setTagPanelOpen,
    setUploadOpen: ui.setUploadOpen,
    showChildTags: ui.showChildTags,
    showImages: ui.showImages,
    sortBy: filters.sortBy,
    tagPanelOpen: ui.tagPanelOpen,
    uploadOpen: ui.uploadOpen,
  };
}
