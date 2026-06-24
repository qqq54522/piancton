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

  return (
    <Link
      to={`/image/${image.id}`}
      className="group block overflow-hidden rounded-xl border border-border bg-card shadow-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-md"
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
      <div className="p-3">
        <h3 className="truncate text-sm font-medium text-foreground">
          {image.title}
        </h3>
        <div className="mt-2 flex flex-wrap gap-1">
          {displayTags.slice(0, 3).map((tag) => (
            <Badge
              key={tag.id}
              variant="secondary"
              className="text-[10px] font-normal transition-opacity"
              style={{
                backgroundColor: `${tag.color || '#6B7280'}18`,
                color: tag.color || '#6B7280',
                borderColor: `${tag.color || '#6B7280'}30`,
              }}
            >
              {tag.parentName ? `${tag.parentName} > ${tag.name || '未命名'}` : (tag.name || '未命名')}
            </Badge>
          ))}
          {displayTags.length > 3 && (
            <Badge variant="secondary" className="text-[10px] font-normal">
              +{displayTags.length - 3}
            </Badge>
          )}
        </div>
      </div>
    </Link>
  );
};

export default ImageCard;
