import { Link } from 'react-router-dom';
import { Download, Images } from 'lucide-react';
import { toast } from 'sonner';

import { useAuth, ROLE_SUBJECT } from '@client/src/lib/auth';
import type { ImageItem } from '@client/src/types/api';
import { Badge } from '@client/src/components/ui/badge';
import { sendImageToAssetAgent } from '@client/src/features/assets/assetAgentEvents';
import { previewUrlFor } from '@client/src/features/images/imagePreview';
import { useImageUrl } from '@client/src/hooks/useImageUrl';
import { rememberImageHomeScroll } from '@client/src/features/images/searchNavigationState';
import { copyTextToClipboard } from '@client/src/lib/clipboard';
import RadialActionMenu from './RadialActionMenu';

interface ImageCardProps {
  image: ImageItem;
  animateGifPreview?: boolean;
  overlay?: React.ReactNode;
  onImageLoad?: () => void;
  variant?: 'grid' | 'masonry';
}

const imageAspectRatio = (image: ImageItem) => {
  if (image.aspectRatio && image.aspectRatio > 0) return String(image.aspectRatio);
  if (image.width && image.height) return `${image.width} / ${image.height}`;
  return '4 / 3';
};

const ImageCard = ({
  image,
  animateGifPreview = true,
  overlay,
  onImageLoad,
  variant = 'grid',
}: ImageCardProps) => {
  const imageUrl = useImageUrl(previewUrlFor(image, { animateGif: animateGifPreview }));
  const { ability, isLoading } = useAuth();
  const isDesigner = !isLoading && ability.can('designer', ROLE_SUBJECT);
  const identityCode = image.identityCode;

  const copyIdentity = async () => {
    if (!identityCode) return;
    if (await copyTextToClipboard(identityCode)) {
      toast.success('身份码已复制');
      return;
    }
    toast.error('复制失败，请进入图片详情手动选择身份码');
  };

  const actionMenu = (
    <RadialActionMenu
      identityCode={identityCode}
      onCopyIdentity={identityCode ? copyIdentity : undefined}
      onSendToAgent={() => {
        sendImageToAssetAgent({
          imageId: image.id,
          assetGroupId: image.assetGroupId,
          title: image.title,
          imageUrl: previewUrlFor(image, { animateGif: animateGifPreview }),
        });
      }}
      downloadHref={image.downloadUrl}
      downloadLabel="下载当前图片"
    />
  );

  if (variant === 'masonry') {
    return (
      <div className="group relative break-inside-avoid">
        <Link
          to={`/image/${image.id}`}
          state={{ from: '/' }}
          onClick={rememberImageHomeScroll}
          className="block overflow-hidden rounded-2xl bg-transparent transition duration-200 hover:-translate-y-0.5"
        >
          <div
            className="relative overflow-hidden rounded-2xl bg-muted shadow-sm ring-1 ring-border/50 transition group-hover:shadow-lg group-hover:ring-foreground/20"
            style={{ aspectRatio: imageAspectRatio(image) }}
          >
            <img
              src={imageUrl}
              alt={image.title}
              className="size-full object-cover transition-transform duration-500 group-hover:scale-[1.025]"
              loading="lazy"
              decoding="async"
              onLoad={onImageLoad}
            />
            {overlay && <div className="absolute inset-0 overflow-hidden">{overlay}</div>}
          </div>
          <div className="mt-2 px-1">
            <div className="min-w-0">
              <h3 className="line-clamp-2 text-sm font-semibold leading-5 text-foreground">{image.title}</h3>
              {image.width && image.height ? (
                <p className="mt-0.5 text-xs text-muted-foreground">{image.width}×{image.height}</p>
              ) : null}
            </div>
          </div>
        </Link>
        {actionMenu}
        {isDesigner && (
          <div className="pointer-events-none absolute bottom-11 right-2 flex items-center gap-1.5 rounded-full bg-black/55 px-2 py-1 text-[11px] font-medium text-white opacity-90 backdrop-blur-sm transition group-hover:bg-black/70">
            {image.variantCount > 1 && (
              <span className="flex items-center gap-1">
                <Images className="size-3" />
                {image.variantCount}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Download className="size-3" />
              {image.downloadCount}
            </span>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="group relative flex h-full flex-col">
      <Link
        to={`/image/${image.id}`}
        state={{ from: '/' }}
        onClick={rememberImageHomeScroll}
        className="group flex h-full flex-col overflow-hidden rounded-2xl border border-border/80 bg-card shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-foreground/20 hover:shadow-md"
      >
        <div className="relative aspect-[4/3] overflow-hidden bg-muted">
          <img
            src={imageUrl}
            alt={image.title}
            className="size-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
            loading="lazy"
            decoding="async"
            onLoad={onImageLoad}
          />
          {overlay && <div className="absolute inset-0 overflow-hidden">{overlay}</div>}
        </div>
        <div className="flex min-h-[88px] flex-1 flex-col p-3.5">
          <h3 className="truncate text-sm font-semibold text-foreground">{image.title}</h3>
          <div className="mt-2 flex min-h-6 items-center gap-1.5">
            {image.channel && <Badge variant="outline" className="text-[10px] font-normal">{image.channel}</Badge>}
            {image.width && image.height ? (
              <span className="text-[10px] text-muted-foreground">{image.width}×{image.height}</span>
            ) : null}
          </div>
        </div>
      </Link>
      {actionMenu}
      {isDesigner && (
        <div className="pointer-events-none absolute bottom-2 right-2 flex items-center gap-2 rounded-md bg-black/50 px-1.5 py-0.5 text-[10px] text-white backdrop-blur-sm">
          {image.variantCount > 1 && (
            <span className="flex items-center gap-1">
              <Images className="size-3" />
              {image.variantCount}
            </span>
          )}
          <span className="flex items-center gap-1">
            <Download className="size-3" />
            {image.downloadCount}
          </span>
        </div>
      )}
    </div>
  );
};

export default ImageCard;
