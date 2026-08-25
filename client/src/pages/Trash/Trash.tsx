import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RotateCcw, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import * as imageApi from '@client/src/api/image';
import { getApiError } from '@client/src/api/client';
import { Button } from '@client/src/components/ui/button';
import EmptyState from '@client/src/components/EmptyState';
import PageHeader from '@client/src/components/PageHeader';
import { previewUrlFor } from '@client/src/features/images/imagePreview';
import { useImageUrl } from '@client/src/hooks/useImageUrl';
import type { ImageItem } from '@client/src/types/api';


function TrashItem({
  image,
  onRestore,
  onPurge,
}: {
  image: ImageItem;
  onRestore: () => void;
  onPurge: () => void;
}) {
  const preview = useImageUrl(previewUrlFor(image));
  return (
    <article className="overflow-hidden rounded-2xl border border-border/80 bg-card shadow-sm">
      <img src={preview} alt={image.title} className="aspect-[4/3] w-full object-cover opacity-75" />
      <div className="p-3">
        <h2 className="truncate text-sm font-medium">{image.title}</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          删除于 {image.deletedAt ? new Date(image.deletedAt).toLocaleString('zh-CN') : '未知时间'}
        </p>
        <div className="mt-3 flex gap-2">
          <Button size="sm" variant="outline" onClick={onRestore}>
            <RotateCcw className="mr-1 size-3.5" />
            恢复
          </Button>
          <Button size="sm" variant="destructive" onClick={onPurge}>
            <Trash2 className="mr-1 size-3.5" />
            永久删除
          </Button>
        </div>
      </div>
    </article>
  );
}

export default function Trash() {
  const client = useQueryClient();
  const trash = useQuery({ queryKey: ['image-trash'], queryFn: imageApi.fetchTrash });
  const refresh = async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: ['image-trash'] }),
      client.invalidateQueries({ queryKey: ['images'] }),
      client.invalidateQueries({ queryKey: ['tags'] }),
    ]);
  };
  const restore = useMutation({
    mutationFn: imageApi.restoreImage,
    onSuccess: async () => {
      await refresh();
      toast.success('图片已恢复');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });
  const purge = useMutation({
    mutationFn: imageApi.purgeImage,
    onSuccess: async () => {
      await refresh();
      toast.success('图片已永久删除');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });

  return (
    <div className="page-shell">
      <PageHeader
        eyebrow="Recovery"
        title="素材回收站"
        description="误删素材可以恢复；只有确认不再需要时才执行永久删除。"
      />
      {trash.isLoading ? (
        <p className="mt-8 text-sm text-muted-foreground">正在加载...</p>
      ) : trash.isError ? (
        <p className="mt-8 text-sm text-destructive">{getApiError(trash.error).message}</p>
      ) : trash.data?.length ? (
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {trash.data.map((image) => (
            <TrashItem
              key={image.id}
              image={image}
              onRestore={() => restore.mutate(image.id)}
              onPurge={() => {
                if (window.confirm(`永久删除「${image.title}」？此操作无法恢复。`)) {
                  purge.mutate(image.id);
                }
              }}
            />
          ))}
        </div>
      ) : (
        <div className="mt-7">
          <EmptyState
            icon={<Trash2 className="size-5" />}
            title="回收站是空的"
            description="删除的素材会暂存在这里，方便在误操作后恢复。"
          />
        </div>
      )}
    </div>
  );
}
