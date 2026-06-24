import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import * as imageApi from '@client/src/api/image';
import { getApiError } from '@client/src/api/client';
import { imageDetailQueryKey } from '@client/src/features/images/useImageDetail';
import { tagQueryKey } from '@client/src/features/tags/useTags';
import type {
  ImageDetail,
} from '@client/src/types/api';


export function useImageDetailActions(
  detail: ImageDetail | null,
) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editingTags, setEditingTags] = useState(false);
  const [editTagIds, setEditTagIds] = useState<string[]>([]);
  const [editingTitle, setEditingTitle] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const refresh = async () => {
    if (!detail) return;
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: imageDetailQueryKey(detail.id) }),
      queryClient.invalidateQueries({ queryKey: tagQueryKey }),
      queryClient.invalidateQueries({ queryKey: ['images'] }),
    ]);
  };

  const titleMutation = useMutation({
    mutationFn: (title: string) => imageApi.updateImageTitle(detail!.id, { title }),
    onSuccess: async () => {
      setEditingTitle(false);
      await refresh();
      toast.success('图片名称已更新');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });

  const tagMutation = useMutation({
    mutationFn: () => {
      const currentPrimary = detail?.businessLabels.find(
        (label) => label.origin === 'manual' && label.role === 'primary',
      )?.tagId;
      const primaryTagId =
        currentPrimary && editTagIds.includes(currentPrimary)
          ? currentPrimary
          : editTagIds[0] ?? null;
      return imageApi.updateImageTags(detail!.id, { tagIds: editTagIds, primaryTagId });
    },
    onSuccess: async () => {
      setEditingTags(false);
      await refresh();
      toast.success('标签已更新');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });

  const deleteMutation = useMutation({
    mutationFn: () => imageApi.deleteImage(detail!.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['images'] });
      toast.success('图片已删除');
      navigate('/');
    },
    onError: (error) => toast.error(getApiError(error).message),
    onSettled: () => setShowDeleteDialog(false),
  });

  const analyzeMutation = useMutation({
    mutationFn: () => imageApi.analyzeContentTags(detail!.id),
    onSuccess: async () => {
      await refresh();
      toast.success('分析完成');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });

  const reviewBusinessLabelMutation = useMutation({
    mutationFn: ({
      labelId,
      reviewStatus,
    }: {
      labelId: string;
      reviewStatus: 'accepted' | 'pending' | 'rejected';
    }) => imageApi.reviewBusinessLabel(detail!.id, labelId, reviewStatus),
    onSuccess: async () => {
      await refresh();
      toast.success('AI 建议状态已更新');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });

  const toggleEditTag = (tagId: string) => {
    setEditTagIds((current) => {
      if (current.includes(tagId)) {
        return current.filter((id) => id !== tagId);
      }
      return [...current, tagId];
    });
  };

  const beginTagEditing = () => {
    setEditTagIds(detail?.tags.map((tag) => tag.id) ?? []);
    setEditingTags(true);
  };

  const cancelTagEditing = () => {
    setEditTagIds(detail?.tags.map((tag) => tag.id) ?? []);
    setEditingTags(false);
  };

  const beginTitleEditing = () => {
    setEditTitle(detail?.title ?? '');
    setEditingTitle(true);
  };

  const saveTitle = () => {
    const title = editTitle.trim();
    if (!detail || !title) return;
    if (title === detail.title) {
      setEditingTitle(false);
      return;
    }
    titleMutation.mutate(title);
  };

  const download = async () => {
    if (!detail) return;
    try {
      const response = await fetch(detail.downloadUrl, { credentials: 'include' });
      if (!response.ok) throw new Error(String(response.status));
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = detail.fileName || detail.title;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast.success('下载开始');
      queryClient.invalidateQueries({ queryKey: imageDetailQueryKey(detail.id) });
    } catch {
      toast.error('下载失败，请稍后重试');
    }
  };

  const flatDisplayTags = useMemo(() => {
    const childParentIds = new Set(
      detail?.tags.filter((tag) => tag.parentId).map((tag) => tag.parentId!) ?? [],
    );
    return (detail?.tags ?? [])
      .filter((tag) => tag.parentId || !childParentIds.has(tag.id))
      .map((tag) => ({
        ...tag,
        imageCount: 0,
        children: [],
        depth: 0,
      }));
  }, [detail?.tags]);

  return {
    analyze: analyzeMutation.mutate,
    analyzing: analyzeMutation.isPending,
    beginTagEditing,
    beginTitleEditing,
    cancelTagEditing,
    deleting: deleteMutation.isPending,
    download,
    editTagIds,
    editTitle,
    editingTags,
    editingTitle,
    flatDisplayTags,
    saveTags: tagMutation.mutate,
    saveTitle,
    savingTags: tagMutation.isPending,
    savingTitle: titleMutation.isPending,
    setEditTitle,
    setEditingTitle,
    setShowDeleteDialog,
    showDeleteDialog,
    remove: deleteMutation.mutate,
    reviewBusinessLabel: reviewBusinessLabelMutation.mutate,
    reviewingBusinessLabel: reviewBusinessLabelMutation.isPending,
    toggleEditTag,
  };
}
