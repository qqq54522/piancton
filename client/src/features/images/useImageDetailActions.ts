import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import * as imageApi from '@client/src/api/image';
import { getApiError } from '@client/src/api/client';
import { imageDetailQueryKey } from '@client/src/features/images/useImageDetail';
import type { ImageDetail } from '@client/src/types/api';

export function useImageDetailActions(detail: ImageDetail | null) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editingTitle, setEditingTitle] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const refresh = async () => {
    if (!detail) return;
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: imageDetailQueryKey(detail.id) }),
      queryClient.invalidateQueries({ queryKey: ['images'] }),
      detail.assetGroupId
        ? queryClient.invalidateQueries({ queryKey: ['asset-group', detail.assetGroupId] })
        : Promise.resolve(),
    ]);
  };
  const titleMutation = useMutation({
    mutationFn: (title: string) => imageApi.updateImageTitle(detail!.id, { title }),
    onSuccess: async () => { setEditingTitle(false); await refresh(); toast.success('图片名称已更新'); },
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
    onSuccess: async () => { await refresh(); toast.success('分析完成'); },
    onError: (error) => toast.error(getApiError(error).message),
  });

  const beginTitleEditing = () => {
    setEditTitle(detail?.title ?? '');
    setEditingTitle(true);
  };
  const saveTitle = () => {
    const title = editTitle.trim();
    if (!detail || !title) return;
    if (title === detail.title) return setEditingTitle(false);
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

  return {
    analyze: analyzeMutation.mutate,
    analyzing: analyzeMutation.isPending,
    beginTitleEditing,
    deleting: deleteMutation.isPending,
    download,
    editTitle,
    editingTitle,
    remove: deleteMutation.mutate,
    saveTitle,
    savingTitle: titleMutation.isPending,
    setEditTitle,
    setEditingTitle,
    setShowDeleteDialog,
    showDeleteDialog,
  };
}
