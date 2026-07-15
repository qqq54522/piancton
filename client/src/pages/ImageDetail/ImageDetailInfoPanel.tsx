import { Check, Download, Loader2, Trash2 } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { CanRole } from '@client/src/lib/auth';
import type { useProviderStatus } from '@client/src/features/ai/useProviderStatus';
import type { useImageDetailActions } from '@client/src/features/images/useImageDetailActions';
import type { ImageDetail } from '@client/src/types/api';
import ImageAiAnalysisPanel from './ImageAiAnalysisPanel';

type ImageDetailActions = ReturnType<typeof useImageDetailActions>;
type ProviderStatusQuery = ReturnType<typeof useProviderStatus>;

const ImageDetailInfoPanel = ({
  detail,
  isDesigner,
  provider,
  actions,
}: {
  detail: ImageDetail;
  isDesigner: boolean;
  provider: ProviderStatusQuery;
  actions: ImageDetailActions;
}) => (
  <div className="surface-card p-5 sm:p-6">
    <div className="flex flex-col gap-4">
      {isDesigner && actions.editingTitle ? (
        <div className="flex items-center gap-2">
          <Input
            value={actions.editTitle}
            onChange={(event) => actions.setEditTitle(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') actions.saveTitle();
              if (event.key === 'Escape') actions.setEditingTitle(false);
            }}
            className="text-base font-semibold"
            autoFocus
          />
          <Button size="sm" onClick={actions.saveTitle} disabled={actions.savingTitle || !actions.editTitle.trim()}>
            {actions.savingTitle ? <Loader2 className="size-3.5 animate-spin" /> : <Check className="size-3.5" />}
          </Button>
        </div>
      ) : (
        <h1
          className={`text-2xl font-semibold tracking-tight ${isDesigner ? 'cursor-pointer transition-colors hover:text-primary' : ''}`}
          onClick={isDesigner ? actions.beginTitleEditing : undefined}
        >
          {detail.title}
        </h1>
      )}
      <div className="flex items-center gap-2">
        <Button className="flex-1" onClick={actions.download}>
          <Download className="size-4" />下载当前版本
        </Button>
        <CanRole roles={['designer']}>
          <Button
            variant="outline"
            size="icon"
            className="shrink-0 text-destructive hover:border-destructive/30 hover:bg-destructive/5"
            aria-label="删除图片"
            onClick={() => actions.setShowDeleteDialog(true)}
          >
            <Trash2 className="size-4" />
          </Button>
        </CanRole>
      </div>
    </div>

    <div className="mt-5 grid grid-cols-2 gap-2 rounded-xl bg-secondary/55 p-3 text-xs">
      <div><span className="block text-muted-foreground">上传日期</span><span className="mt-1 block font-medium">{new Date(detail.createdAt).toLocaleDateString('zh-CN')}</span></div>
      <div><span className="block text-muted-foreground">图片尺寸</span><span className="mt-1 block font-medium">{detail.width && detail.height ? `${detail.width}×${detail.height}` : '待识别'}</span></div>
      {detail.channel && <div className="col-span-2"><span className="text-muted-foreground">使用渠道</span><span className="ml-2 font-medium">{detail.channel}</span></div>}
    </div>

    <ImageAiAnalysisPanel detail={detail} provider={provider} actions={actions} />
  </div>
);

export default ImageDetailInfoPanel;
