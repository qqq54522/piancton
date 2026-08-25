import { useState } from 'react';
import { Download, FolderOpen, X } from 'lucide-react';

import { exportAssetGroups } from '@client/src/api/asset';
import { Button } from '@client/src/components/ui/button';
import type { ProjectBasketItem } from '@client/src/features/assets/useProjectBasket';

interface ProjectBasketPanelProps {
  items: ProjectBasketItem[];
  onRemove: (assetGroupId: string) => void;
  onClear: () => void;
}

function ProjectBasketPanel({ items, onRemove, onClear }: ProjectBasketPanelProps) {
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (items.length === 0) return null;

  const exportBasket = async () => {
    setExporting(true);
    setError(null);
    try {
      const blob = await exportAssetGroups(items.map((item) => item.assetGroupId));
      downloadBlob(blob, 'asset-bundles.zip');
    } catch {
      setError('导出失败，请稍后再试');
    } finally {
      setExporting(false);
    }
  };

  return (
    <section className="mb-4 rounded-xl border border-border/80 bg-white px-4 py-3 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[#f1f1ef] text-foreground">
            <FolderOpen className="size-4" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-foreground">项目夹</p>
            <p className="text-xs text-muted-foreground">已选 {items.length} 组素材，可批量导出</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button type="button" variant="outline" size="sm" className="rounded-full bg-white" onClick={onClear}>
            清空
          </Button>
          <Button
            type="button"
            size="sm"
            className="rounded-full bg-foreground text-background hover:bg-foreground/88"
            disabled={exporting}
            onClick={exportBasket}
          >
            <Download className="size-4" />
            {exporting ? '导出中' : '导出'}
          </Button>
        </div>
      </div>
      <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
        {items.map((item) => (
          <button
            key={item.assetGroupId}
            type="button"
            className="inline-flex max-w-[220px] shrink-0 items-center gap-1.5 rounded-full border border-border bg-[#f7f7f5] px-3 py-1.5 text-xs text-foreground"
            onClick={() => onRemove(item.assetGroupId)}
            title="从项目夹移除"
          >
            <span className="truncate">{item.title}</span>
            <X className="size-3 shrink-0 text-muted-foreground" />
          </button>
        ))}
      </div>
      {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
    </section>
  );
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export default ProjectBasketPanel;
