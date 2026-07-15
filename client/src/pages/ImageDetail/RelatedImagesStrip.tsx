import { Link } from 'react-router-dom';

import { useImageUrl } from '@client/src/hooks/useImageUrl';
import type { ImageItem } from '@client/src/types/api';

const RelatedImageItem = ({ image }: { image: ImageItem }) => {
  const imageUrl = useImageUrl(image.contentUrl);
  return (
    <Link
      to={`/image/${image.id}`}
      className="group flex-shrink-0 overflow-hidden rounded-2xl border border-border bg-card shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
      style={{ width: 200 }}
    >
      <div className="aspect-[4/3] overflow-hidden bg-muted">
        <img
          src={imageUrl}
          alt={image.title}
          className="size-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
        />
      </div>
      <div className="p-2">
        <p className="truncate text-xs font-medium text-foreground">
          {image.title}
        </p>
      </div>
    </Link>
  );
};

const RelatedImagesStrip = ({ images }: { images: ImageItem[] }) => {
  if (images.length === 0) return null;

  return (
    <div className="mt-10">
      <p className="section-kicker">Related</p>
      <h2 className="mb-4 mt-1 text-lg font-semibold text-foreground">相关素材</h2>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {images.map((image) => (
          <RelatedImageItem key={image.id} image={image} />
        ))}
      </div>
    </div>
  );
};

export default RelatedImagesStrip;
