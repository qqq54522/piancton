import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import * as imageApi from '@client/src/api/image';
import { getApiError } from '@client/src/api/client';
import { imageDetailQueryKey } from '@client/src/features/images/useImageDetail';
import type { AssetImage, ImageDetail } from '@client/src/types/api';

type DownloadTarget = Pick<AssetImage, 'id' | 'downloadUrl' | 'fileName' | 'title'>;

export function useImageDetailActions(detail: ImageDetail | null) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editingTitle, setEditingTitle] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [downloading, setDownloading] = useState(false);

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
    onSuccess: async (image, requestedTitle) => {
      setEditingTitle(false);
      await refresh();
      toast.success(
        image.title === requestedTitle.trim()
          ? '图片名称已更新'
          : `名称已存在，已自动更新为“${image.title}”`,
      );
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
  const saveBlob = async (target: DownloadTarget) => {
    const response = await fetch(target.downloadUrl, { credentials: 'include' });
    if (!response.ok) throw new Error(String(response.status));
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = target.fileName || target.title;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const invalidateAfterDownload = async (targets: DownloadTarget[]) => {
    if (!detail) return;
    const targetIds = new Set(targets.map((target) => target.id));
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['images'] }),
      targetIds.has(detail.id)
        ? queryClient.invalidateQueries({ queryKey: imageDetailQueryKey(detail.id) })
        : Promise.resolve(),
      detail.assetGroupId
        ? queryClient.invalidateQueries({ queryKey: ['asset-group', detail.assetGroupId] })
        : Promise.resolve(),
    ]);
  };
  const downloadTarget = async (target: DownloadTarget) => {
    try {
      setDownloading(true);
      await saveBlob(target);
      toast.success('下载开始');
      await invalidateAfterDownload([target]);
    } catch {
      toast.error('下载失败，请稍后重试');
    } finally {
      setDownloading(false);
    }
  };
  const download = async () => {
    if (!detail) return;
    await downloadTarget(detail);
  };
  const downloadAll = async (targets: DownloadTarget[]) => {
    const uniqueTargets = Array.from(
      new Map(targets.map((target) => [target.id, target])).values(),
    );
    if (!uniqueTargets.length) return;
    try {
      setDownloading(true);
      for (const target of uniqueTargets) {
        await saveBlob(target);
      }
      toast.success(`已开始下载 ${uniqueTargets.length} 个尺寸`);
      await invalidateAfterDownload(uniqueTargets);
    } catch {
      toast.error('部分尺寸下载失败，请稍后重试');
    } finally {
      setDownloading(false);
    }
  };

  return {
    analyze: analyzeMutation.mutate,
    analyzing: analyzeMutation.isPending,
    beginTitleEditing,
    deleting: deleteMutation.isPending,
    download,
    downloadAll,
    downloading,
    downloadTarget,
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
