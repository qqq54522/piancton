import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

import { recordSearchInteraction } from '@client/src/api/image';
import { previewUrlFor } from '@client/src/features/images/imagePreview';
import { useImageUrl } from '@client/src/hooks/useImageUrl';
import type {
  ImageDetail,
  ImageItem,
  ImageRecommendationSection,
  SearchInteractionSource,
} from '@client/src/types/api';

interface BusinessImageDetailRecommendationsProps {
  detail: ImageDetail;
}

interface BusinessImageDetailSideRecommendationsProps extends BusinessImageDetailRecommendationsProps {
  maxHeight?: number | null;
}

type RecommendationModule = Pick<
  ImageRecommendationSection,
  'purpose' | 'title' | 'description'
> & {
  browseChannel?: string | null;
  images: ImageItem[];
};

export const BusinessImageDetailSideRecommendations = ({
  detail,
  maxHeight,
}: BusinessImageDetailSideRecommendationsProps) => {
  const modules = recommendationModules(detail).slice(1);
  const scrollStyle = maxHeight ? { maxHeight: `${maxHeight}px` } : undefined;

  if (modules.length === 0) return null;

  return (
    <div
      className="compact-scrollbar space-y-5 xl:max-h-[calc(100vh-5rem)] xl:overflow-y-auto xl:overscroll-contain xl:pr-1"
      style={scrollStyle}
    >
      {modules.map((module) => (
        <RecommendationPanel
          key={module.purpose}
          module={module}
          variant="compact"
        />
      ))}
    </div>
  );
};

const BusinessImageDetailRecommendations = ({
  detail,
}: BusinessImageDetailRecommendationsProps) => {
  const modules = recommendationModules(detail).slice(0, 1);

  if (modules.length === 0) return null;

  return (
    <div>
      {modules.map((module) => (
        <RecommendationPanel
          key={module.purpose}
          module={module}
          variant="wide"
        />
      ))}
    </div>
  );
};

const RecommendationPanel = ({
  module,
  variant,
}: {
  module: RecommendationModule;
  variant: 'compact' | 'wide';
}) => {
  const browseState = module.browseChannel
    ? { browseChannel: module.browseChannel, browseChannelIntent: null }
    : undefined;

  return (
    <section className="rounded-2xl border border-border/80 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-foreground">{module.title}</h2>
          <p className="mt-1 text-sm leading-5 text-muted-foreground">{module.description}</p>
        </div>
        {browseState && (
          <Link
            to="/"
            state={browseState}
            className="inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            更多
            <ChevronRight className="size-3.5" />
          </Link>
        )}
      </div>
      <div className="compact-scrollbar flex gap-4 overflow-x-auto pb-2">
        {module.images.map((image, index) => (
          <RecommendationImageLink
            key={image.id}
            image={image}
            position={index + 1}
            purpose={module.purpose}
            variant={variant}
          />
        ))}
      </div>
    </section>
  );
};

const RecommendationImageLink = ({
  image,
  position,
  purpose,
  variant,
}: {
  image: ImageItem;
  position: number;
  purpose: ImageRecommendationSection['purpose'];
  variant: 'compact' | 'wide';
}) => {
  const imageUrl = useImageUrl(previewUrlFor(image));
  const linkRef = useRef<HTMLAnchorElement | null>(null);
  const source = `detail_${purpose}` as SearchInteractionSource;
  const exposureSent = useRef(false);

  useEffect(() => {
    const element = linkRef.current;
    if (!element || exposureSent.current || typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting || exposureSent.current) return;
      exposureSent.current = true;
      void recordSearchInteraction({
        keyword: '',
        action: 'exposure',
        resultImageId: image.id,
        assetGroupId: image.assetGroupId,
        position,
        source,
      }).catch(() => undefined);
      observer.disconnect();
    }, { threshold: 0.35 });
    observer.observe(element);
    return () => observer.disconnect();
  }, [image.assetGroupId, image.id, position, source]);

  return (
    <Link
      ref={linkRef}
      to={`/image/${image.id}`}
      onClick={() => {
        void recordSearchInteraction({
          keyword: '',
          action: 'open_detail',
          resultImageId: image.id,
          assetGroupId: image.assetGroupId,
          position,
          source,
        }).catch(() => undefined);
      }}
      className={`group block min-w-0 shrink-0 ${variant === 'wide' ? 'w-[220px] sm:w-[260px]' : 'w-[150px]'}`}
    >
      <div
        className={`overflow-hidden rounded-xl bg-muted ${variant === 'wide' ? 'h-[132px] sm:h-[156px]' : 'h-[96px]'}`}
      >
        <img
          src={imageUrl}
          alt={image.title}
          loading="lazy"
          className="size-full object-cover transition-transform duration-300 group-hover:scale-[1.035]"
        />
      </div>
      <p className="mt-1.5 truncate text-sm font-medium text-foreground">{image.title}</p>
    </Link>
  );
};

function recommendationModules(detail: ImageDetail): RecommendationModule[] {
  const sections = detail.recommendationSections ?? [];
  if (sections.length > 0) {
    return sections.map((section) => ({
      ...section,
      images: section.images ?? [],
    }));
  }
  const legacyImages = uniqueImages(detail.relatedImages ?? []).filter(
    (image) => image.id !== detail.id,
  );
  if (legacyImages.length === 0) return [];
  return [
    {
      purpose: 'visual_similar',
      title: '相关素材',
      description: '继续比较与当前图片接近的素材。',
      images: legacyImages,
    },
  ];
}

function uniqueImages(images: ImageItem[]) {
  const seen = new Set<string>();
  return images.filter((image) => {
    if (seen.has(image.id)) return false;
    seen.add(image.id);
    return true;
  });
}

export default BusinessImageDetailRecommendations;
