import { useCallback, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { tagQueryKey } from '@client/src/features/tags/useTags';
import type { TagWithCount } from '@client/src/types/api';

interface UseImageBrowserUiParams {
  parentTagId?: string;
  allTags: TagWithCount[];
  isDesigner: boolean;
  hasActiveFilter: boolean;
}

export function useImageBrowserUi({
  parentTagId,
  allTags,
  isDesigner,
  hasActiveFilter,
}: UseImageBrowserUiParams) {
  const queryClient = useQueryClient();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [tagPanelOpen, setTagPanelOpen] = useState(false);
  const [filterDialogOpen, setFilterDialogOpen] = useState(false);

  const currentTag = useMemo(
    () => parentTagId ? allTags.find((tag) => tag.id === parentTagId) ?? null : null,
    [allTags, parentTagId],
  );
  const childTags = useMemo(
    () => allTags.filter((tag) => parentTagId ? tag.parentId === parentTagId : !tag.parentId),
    [allTags, parentTagId],
  );

  const handleUploadSuccess = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: tagQueryKey });
    queryClient.invalidateQueries({ queryKey: ['images'] });
  }, [queryClient]);

  const isRoot = !parentTagId;
  const showChildTags = childTags.length > 0 && !hasActiveFilter && (!isRoot || isDesigner);
  const showImages = !showChildTags && (Boolean(parentTagId) || hasActiveFilter || isRoot);

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
    breadcrumb,
    childTags,
    currentTag,
    filterDialogOpen,
    handleUploadSuccess,
    isRoot,
    pageTitle: isRoot ? '图片库' : currentTag?.name || '加载中...',
    setFilterDialogOpen,
    setTagPanelOpen,
    setUploadOpen,
    showChildTags,
    showImages,
    tagPanelOpen,
    uploadOpen,
  };
}
