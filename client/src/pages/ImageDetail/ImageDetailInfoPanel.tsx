import { Check, Download, Loader2, Trash2 } from 'lucide-react';

import { Avatar, AvatarFallback } from '@client/src/components/ui/avatar';
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
  <div className="rounded-xl border border-border bg-card p-5">
    <div className="flex items-center justify-between">
      {isDesigner && actions.editingTitle ? (
        <div className="mr-3 flex flex-1 items-center gap-2">
          <Input
            value={actions.editTitle}
            onChange={(event) => actions.setEditTitle(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') actions.saveTitle();
              if (event.key === 'Escape') actions.setEditingTitle(false);
            }}
            className="h-8 text-base"
            autoFocus
          />
          <Button size="sm" onClick={actions.saveTitle} disabled={actions.savingTitle || !actions.editTitle.trim()}>
            {actions.savingTitle ? <Loader2 className="size-3.5 animate-spin" /> : <Check className="size-3.5" />}
          </Button>
        </div>
      ) : (
        <h1
          className={`mr-3 flex-1 text-xl font-semibold ${isDesigner ? 'cursor-pointer hover:text-primary' : ''}`}
          onClick={isDesigner ? actions.beginTitleEditing : undefined}
        >
          {detail.title}
        </h1>
      )}
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={actions.download}>
          <Download className="mr-1.5 size-4" />下载
        </Button>
        <CanRole roles={['designer']}>
          <Button
            variant="outline"
            size="sm"
            className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
            onClick={() => actions.setShowDeleteDialog(true)}
          >
            <Trash2 className="mr-1.5 size-4" />删除
          </Button>
        </CanRole>
      </div>
    </div>

    <div className="mt-4 flex items-center gap-3">
      <Avatar className="size-7"><AvatarFallback className="text-[10px]">U</AvatarFallback></Avatar>
      <span className="text-xs text-muted-foreground">
        {new Date(detail.createdAt).toLocaleDateString('zh-CN')}
        {detail.channel ? ` · ${detail.channel}` : ''}
        {detail.width && detail.height ? ` · ${detail.width}×${detail.height}` : ''}
      </span>
    </div>

    <ImageAiAnalysisPanel detail={detail} provider={provider} actions={actions} />
  </div>
);

export default ImageDetailInfoPanel;
