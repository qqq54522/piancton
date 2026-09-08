import { Check, Copy, Link2, Loader2, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { CanRole } from '@client/src/lib/auth';
import type { useImageDetailActions } from '@client/src/features/images/useImageDetailActions';
import type { AssetImage, ImageDetail } from '@client/src/types/api';
import ImageDownloadMenu from './ImageDownloadMenu';

type ImageDetailActions = ReturnType<typeof useImageDetailActions>;

const ImageDetailInfoPanel = ({
  detail,
  embedded = false,
  isDesigner,
  actions,
  panelHeight,
  variants,
}: {
  detail: ImageDetail;
  embedded?: boolean;
  isDesigner: boolean;
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
          <IdentityCodePanel detail={detail} />
          <ImageDownloadMenu detail={detail} variants={variants} actions={actions} />
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

      <IdentityCodePanel detail={detail} />
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

    </div>
  );
};

function IdentityCodePanel({ detail }: { detail: ImageDetail }) {
  const assetCode = detail.assetCode;
  const versionCode = detail.versionCode;
  const sharePath = detail.sharePath;
  if (!assetCode && !versionCode) return null;

  const copy = async (value: string, message: string) => {
    try {
      await navigator.clipboard.writeText(value);
      toast.success(message);
    } catch {
      toast.error('复制失败，请手动选择编码');
    }
  };

  const shareUrl = sharePath
    ? `${window.location.origin}${sharePath}`
    : null;

  return (
    <div className="mt-5 rounded-xl border border-border/80 bg-[#f7f7f5] p-3.5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-foreground">素材身份</p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">用于分享和精准查找，不随标题变化</p>
        </div>
        {shareUrl && (
          <button
            type="button"
            aria-label="复制分享链接"
            title="复制分享链接"
            className="inline-flex size-8 shrink-0 items-center justify-center rounded-full border border-border bg-white text-foreground transition hover:bg-foreground hover:text-background"
            onClick={() => copy(shareUrl, '分享链接已复制')}
          >
            <Link2 className="size-4" />
          </button>
        )}
      </div>
      <div className="mt-3 space-y-2">
        {assetCode && (
          <IdentityCodeRow label="素材码" value={assetCode} onCopy={() => copy(assetCode, '素材码已复制')} />
        )}
        {versionCode && (
          <IdentityCodeRow label="版本码" value={versionCode} onCopy={() => copy(versionCode, '版本码已复制')} />
        )}
      </div>
    </div>
  );
}

function IdentityCodeRow({
  label,
  value,
  onCopy,
}: {
  label: string;
  value: string;
  onCopy: () => void;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border/70 bg-white px-3 py-2">
      <span className="w-12 shrink-0 text-[11px] text-muted-foreground">{label}</span>
      <code className="min-w-0 flex-1 truncate text-xs font-semibold tracking-[0.04em] text-foreground">
        {value}
      </code>
      <button
        type="button"
        aria-label={`复制${label}`}
        title={`复制${label}`}
        className="inline-flex size-7 shrink-0 items-center justify-center rounded-md text-muted-foreground transition hover:bg-secondary hover:text-foreground"
        onClick={onCopy}
      >
        <Copy className="size-3.5" />
      </button>
    </div>
  );
}

export default ImageDetailInfoPanel;
