import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Download } from 'lucide-react';
import { useAuth, ROLE_SUBJECT } from '@client/src/lib/auth';
import type { ImageItem } from '@client/src/types/api';
import { Badge } from '@client/src/components/ui/badge';
import { useImageUrl } from '@client/src/hooks/useImageUrl';

interface ImageCardProps {
  image: ImageItem;
  overlay?: React.ReactNode;
}

const ImageCard = ({ image, overlay }: ImageCardProps) => {
  const imageUrl = useImageUrl(image.thumbnailUrl);
  const { ability, isLoading } = useAuth();
  const isDesigner = !isLoading && ability.can('designer', ROLE_SUBJECT);

  const displayTags = useMemo(() => {
    const childParentIds = new Set(
      image.tags.filter((t) => t.parentId).map((t) => t.parentId!),
    );
    return image.tags
      .filter((t) => t.parentId || !childParentIds.has(t.id))
      .sort((a, b) => Number(a.isSecondary) - Number(b.isSecondary));
  }, [image.tags]);
  const primaryTag = displayTags[0];
  const hiddenTagCount = Math.max(displayTags.length - 1, 0);
  const tagSummary = displayTags
    .map((tag) => (tag.parentName ? `${tag.parentName} > ${tag.name || '未命名'}` : (tag.name || '未命名')))
    .join('\n');

  return (
    <Link
      to={`/image/${image.id}`}
      className="group flex h-full flex-col overflow-hidden rounded-xl border border-border bg-card shadow-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-md"
    >
      <div className="relative aspect-[4/3] overflow-hidden bg-muted">
        <img
          src={imageUrl}
          alt={image.title}
          className="size-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
        />
        {overlay && (
          <div className="absolute inset-0 overflow-hidden">
            {overlay}
          </div>
        )}
        {isDesigner && image.downloadCount != null && (
          <div className="absolute bottom-1.5 right-1.5 flex items-center gap-1 rounded-md bg-black/50 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
            <Download className="size-3" />
            {image.downloadCount}
          </div>
        )}
      </div>
      <div className="flex min-h-[86px] flex-1 flex-col p-3">
        <h3 className="truncate text-sm font-medium text-foreground">
          {image.title}
        </h3>
        <div className="mt-2 flex min-h-6 items-center gap-1.5" title={tagSummary || undefined}>
          {primaryTag ? (
            <Badge
              key={primaryTag.id}
              variant="secondary"
              className="max-w-[calc(100%-3rem)] truncate text-[10px] font-normal transition-opacity"
              style={{
                backgroundColor: `${primaryTag.color || '#6B7280'}18`,
                color: primaryTag.color || '#6B7280',
                borderColor: `${primaryTag.color || '#6B7280'}30`,
              }}
            >
              {primaryTag.parentName ? `${primaryTag.parentName} > ${primaryTag.name || '未命名'}` : (primaryTag.name || '未命名')}
            </Badge>
          ) : (
            <span className="text-xs text-muted-foreground/60">未归类</span>
          )}
          {hiddenTagCount > 0 && (
            <Badge variant="outline" className="shrink-0 bg-background text-[10px] font-normal text-muted-foreground">
              +{hiddenTagCount}
            </Badge>
          )}
        </div>
      </div>
    </Link>
  );
};

export default ImageCard;
