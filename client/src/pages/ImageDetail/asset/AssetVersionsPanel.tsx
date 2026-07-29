import { useState } from 'react';
import { ImagePlus, RefreshCw, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { getApiError } from '@client/src/api/client';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import type { AssetGroup } from '@client/src/types/api';
import type { useAssetActions } from '@client/src/features/assets/useAssetActions';
import AssetVariantDeleteDialog from './AssetVariantDeleteDialog';
import AssetVersionDialog from './AssetVersionDialog';

type AssetActions = ReturnType<typeof useAssetActions>;
type AssetImage = AssetGroup['images'][number];

interface AssetVersionsPanelProps {
  group: AssetGroup;
  editable: boolean;
  actions: AssetActions;
  onPrimaryChanged: (imageId: string) => void;
}

function AssetVersionsPanel({ group, editable, actions, onPrimaryChanged }: AssetVersionsPanelProps) {
  const [dialogMode, setDialogMode] = useState<'variant' | 'replace' | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AssetImage | null>(null);
  const pending = actions.addVariant.isPending || actions.replacePrimary.isPending;

  const submit = async (input: {
    file: File;
    title?: string;
    channel?: string;
    role: 'derivative' | 'alternative';
  }) => {
    try {
      if (dialogMode === 'replace') {
        const updated = await actions.replacePrimary.mutateAsync(input);
        toast.success('主图已替换，旧主图已保留为历史版本');
        setDialogMode(null);
        if (updated.primaryImageId) onPrimaryChanged(updated.primaryImageId);
        return;
      }
      await actions.addVariant.mutateAsync(input);
      toast.success(
        input.role === 'derivative'
          ? '延展版本已添加，已继承主图业务信息'
          : '备选版本已添加，正在后台分析画面',
      );
      setDialogMode(null);
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  const removeVariant = async () => {
    if (!deleteTarget) return;
    try {
      await actions.deleteVariant.mutateAsync(deleteTarget.id);
      toast.success('延展版本已移入回收站');
      setDeleteTarget(null);
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  return (
    <section className="surface-card p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="font-semibold">版本与尺寸</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">同组版本共享业务关系，搜索结果只占一个位置。</p>
        </div>
        {editable && (
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setDialogMode('variant')}>
              <ImagePlus className="mr-1.5 size-3.5" />添加延展版本
            </Button>
            <Button variant="outline" size="sm" onClick={() => setDialogMode('replace')}>
              <RefreshCw className="mr-1.5 size-3.5" />替换主图
            </Button>
          </div>
        )}
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {group.images.map((image) => (
          <div key={image.id} className={`overflow-hidden rounded-xl border ${image.isCurrent ? 'border-border' : 'border-dashed opacity-60'}`}>
            <img src={image.thumbnailUrl} alt={image.title} className="aspect-[4/3] w-full object-cover" />
            <div className="space-y-1 p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-xs font-medium">{image.title}</p>
                <div className="flex shrink-0 items-center gap-1">
                  <Badge
                    variant={image.id === group.primaryImageId ? 'default' : 'outline'}
                    className={`text-[10px] ${image.id === group.primaryImageId ? 'bg-foreground text-background' : ''}`}
                  >
                    {image.id === group.primaryImageId ? '正式主图' : image.isCurrent ? '可用版本' : '历史版本'}
                  </Badge>
                  {editable && image.id !== group.primaryImageId && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-7 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                      aria-label={`删除版本“${image.title}”`}
                      title="删除这个版本"
                      onClick={() => setDeleteTarget(image)}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  )}
                </div>
              </div>
              <p className="text-[11px] text-muted-foreground">
                {image.width && image.height ? `${image.width} × ${image.height}` : '尺寸待识别'}
                {image.channel ? ` · ${image.channel}` : ''}
              </p>
            </div>
          </div>
        ))}
      </div>
      <AssetVersionDialog
        open={dialogMode !== null}
        mode={dialogMode === 'replace' ? 'replace' : 'variant'}
        pending={pending}
        onOpenChange={(open) => !open && setDialogMode(null)}
        onSubmit={submit}
      />
      <AssetVariantDeleteDialog
        title={deleteTarget?.title ?? ''}
        open={Boolean(deleteTarget)}
        deleting={actions.deleteVariant.isPending}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        onConfirm={removeVariant}
      />
    </section>
  );
}

export default AssetVersionsPanel;
