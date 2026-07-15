import { Link } from 'react-router-dom';
import { Download, Images } from 'lucide-react';

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

  return (
    <Link
      to={`/image/${image.id}`}
      className="group flex h-full flex-col overflow-hidden rounded-2xl border border-border/80 bg-card shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/20 hover:shadow-md"
    >
      <div className="relative aspect-[4/3] overflow-hidden bg-muted">
        <img
          src={imageUrl}
          alt={image.title}
        className="size-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
          loading="lazy"
        />
        {overlay && <div className="absolute inset-0 overflow-hidden">{overlay}</div>}
        {isDesigner && (
          <div className="absolute bottom-1.5 right-1.5 flex items-center gap-2 rounded-md bg-black/50 px-1.5 py-0.5 text-[10px] text-white backdrop-blur-sm">
            {image.variantCount > 1 && <span className="flex items-center gap-1"><Images className="size-3" />{image.variantCount}</span>}
            <span className="flex items-center gap-1"><Download className="size-3" />{image.downloadCount}</span>
          </div>
        )}
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
  );
};

export default ImageCard;
