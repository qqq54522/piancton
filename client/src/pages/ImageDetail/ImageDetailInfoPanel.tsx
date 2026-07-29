import { Check, Loader2, Trash2 } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { CanRole } from '@client/src/lib/auth';
import type { useProviderStatus } from '@client/src/features/ai/useProviderStatus';
import type { useImageDetailActions } from '@client/src/features/images/useImageDetailActions';
import type { AssetImage, ImageDetail } from '@client/src/types/api';
import ImageAiAnalysisPanel from './ImageAiAnalysisPanel';
import ImageDownloadMenu from './ImageDownloadMenu';

type ImageDetailActions = ReturnType<typeof useImageDetailActions>;
type ProviderStatusQuery = ReturnType<typeof useProviderStatus>;

const ImageDetailInfoPanel = ({
  detail,
  embedded = false,
  isDesigner,
  provider,
  actions,
  panelHeight,
  variants,
}: {
  detail: ImageDetail;
  embedded?: boolean;
  isDesigner: boolean;
  provider: ProviderStatusQuery;
  actions: ImageDetailActions;
  panelHeight: number | null;
  variants?: AssetImage[];
}) => {
  const panelStyle = panelHeight ? { height: panelHeight } : undefined;
  const panelClassName = embedded
    ? 'compact-scrollbar overflow-y-auto overflow-x-hidden p-5 sm:p-6'
    : 'compact-scrollbar surface-card overflow-y-auto overflow-x-hidden p-5 sm:p-6';

  if (!isDesigner) {
    return (
      <div className={panelClassName} style={panelStyle}>
        <div className="flex flex-col gap-4">
          <h1 className="text-2xl font-semibold tracking-tight">
            {detail.title}
          </h1>
          <ImageDownloadMenu detail={detail} variants={variants} actions={actions} />
        </div>

        <div className="mt-6">
          <span className="text-sm font-medium">语义总结</span>
          <p className="mt-2 rounded-xl border border-border/80 bg-[#f7f7f5] px-4 py-3 text-sm leading-7 text-foreground/85">
            {detail.imageSummary || '这张素材暂时还没有语义总结。'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={panelClassName} style={panelStyle}>
      <div className="flex flex-col gap-4">
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
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
                <Button
                  size="sm"
                  onClick={actions.saveTitle}
                  disabled={actions.savingTitle || !actions.editTitle.trim()}
                >
                  {actions.savingTitle ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <Check className="size-3.5" />
                  )}
                </Button>
              </div>
            ) : (
              <h1
                className={`text-2xl font-semibold tracking-tight ${isDesigner ? 'cursor-pointer transition-colors hover:text-foreground/65' : ''}`}
                onClick={isDesigner ? actions.beginTitleEditing : undefined}
              >
                {detail.title}
              </h1>
            )}
          </div>
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
        <ImageDownloadMenu detail={detail} variants={variants} actions={actions} />
      </div>

      <div className="mt-5 grid grid-cols-2 gap-2 rounded-xl bg-secondary/55 p-3 text-xs">
        <div>
          <span className="block text-muted-foreground">上传日期</span>
          <span className="mt-1 block font-medium">
            {new Date(detail.createdAt).toLocaleDateString('zh-CN')}
          </span>
        </div>
        <div>
          <span className="block text-muted-foreground">图片尺寸</span>
          <span className="mt-1 block font-medium">
            {detail.width && detail.height ? `${detail.width}×${detail.height}` : '待识别'}
          </span>
        </div>
        {detail.channel && (
          <div className="col-span-2">
            <span className="text-muted-foreground">使用渠道</span>
            <span className="ml-2 font-medium">{detail.channel}</span>
          </div>
        )}
        {detail.styleLabel && (
          <div className="col-span-2">
            <span className="text-muted-foreground">画面风格</span>
            <span className="ml-2 font-medium">{detail.styleLabel}</span>
          </div>
        )}
        {typeof detail.isSceneImage === 'boolean' && (
          <div className="col-span-2">
            <span className="text-muted-foreground">图片类型</span>
            <span className="ml-2 font-medium">{detail.isSceneImage ? '场景图' : '非场景图'}</span>
          </div>
        )}
      </div>

      <ImageAiAnalysisPanel detail={detail} provider={provider} actions={actions} />
    </div>
  );
};

export default ImageDetailInfoPanel;
