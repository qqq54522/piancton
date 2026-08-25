import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { fetchImages } from '@client/src/api/image';
import { previewUrlFor } from '@client/src/features/images/imagePreview';
import { useImageUrl } from '@client/src/hooks/useImageUrl';
import type { ImageDetail, ImageItem } from '@client/src/types/api';
import type { ChannelFamily, ChannelIntentEntry, ImageChannelIntent } from '../ImageHome/channelIntent';
import { splitChannelValue } from '../ImageHome/channelValue';
import { useChannelIntentEntries } from '../ImageHome/channelIntentCatalog';

interface BusinessImageDetailRecommendationsProps {
  detail: ImageDetail;
}

interface BusinessImageDetailSideRecommendationsProps extends BusinessImageDetailRecommendationsProps {
  maxHeight?: number | null;
}

type RecommendationModule = {
  browseChannel?: string;
  browseChannelIntent?: ImageChannelIntent | null;
  description: string;
  images: ImageItem[];
  title: string;
};

const MAX_POOL_SIZE = 50;

export const BusinessImageDetailSideRecommendations = ({
  detail,
  maxHeight,
}: BusinessImageDetailSideRecommendationsProps) => {
  const { lowerModules, sideModules } = useBusinessDetailRecommendationModules(detail);
  const modules = [...sideModules, ...lowerModules.slice(1)];
  const scrollStyle = maxHeight ? { maxHeight: `${maxHeight}px` } : undefined;

  return (
    <div
      className="compact-scrollbar space-y-5 xl:max-h-[calc(100vh-5rem)] xl:overflow-y-auto xl:overscroll-contain xl:pr-1"
      style={scrollStyle}
    >
      {modules.map((module) => (
        <RecommendationPanel
          key={module.title}
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
  const { lowerModules } = useBusinessDetailRecommendationModules(detail);

  return (
    <div>
      {lowerModules.slice(0, 1).map((module) => (
        <RecommendationPanel
          key={module.title}
          module={module}
          variant="wide"
        />
      ))}
    </div>
  );
};

function useBusinessDetailRecommendationModules(detail: ImageDetail) {
  const channelEntries = useChannelIntentEntries();
  const imageQuery = useQuery({
    queryKey: ['images', 'detail-recommendations'],
    queryFn: () => fetchImages({ limit: MAX_POOL_SIZE, sortBy: 'downloadCount' }),
    staleTime: 30_000,
  });
  const imagePool = useMemo(
    () => uniqueImages([...(detail.relatedImages ?? []), ...(imageQuery.data?.items ?? [])])
      .filter((image) => image.id !== detail.id),
    [detail.id, detail.relatedImages, imageQuery.data?.items],
  );
  const currentChannels = splitChannelValue(detail.channel);
  const currentChannelImages = filterByChannels(imagePool, currentChannels);
  const brandChannels = channelEntries
    .filter((entry) => entry.family === 'brand_manual')
    .map((entry) => entry.value);
  const mobileLargeChannels = channelEntries
    .filter((entry) => entry.family === 'mobile' && entry.size === 'large')
    .map((entry) => entry.value);
  const mobileSmallChannels = channelEntries
    .filter((entry) => entry.family === 'mobile' && entry.size === 'small')
    .map((entry) => entry.value);
  const websiteChannels = channelEntries
    .filter((entry) => entry.family === 'website')
    .map((entry) => entry.value);
  const pptChannels = channelEntries
    .filter((entry) => entry.family === 'ppt')
    .map((entry) => entry.value);
  const relatedImages = uniqueImages(detail.relatedImages ?? [])
    .filter((image) => image.id !== detail.id);
  const currentPrimaryChannel = currentChannels[0] ?? '';
  const mobileLargeModule = buildChannelModule({
    family: 'mobile',
    channels: mobileLargeChannels,
    channelEntries,
    currentPrimaryChannel,
    description: '适合手机端首屏、朋友圈长图或重点宣传位继续挑选。',
    imagePool,
    title: '手机端大图素材',
  });
  const mobileSmallModule = buildChannelModule({
    family: 'mobile',
    channels: mobileSmallChannels,
    channelEntries,
    currentPrimaryChannel,
    description: '适合手机端入口、列表小卡片或信息流位置继续挑选。',
    imagePool,
    title: '手机端小图素材',
  });

  const sideModules: RecommendationModule[] = [
    {
      browseChannel: currentPrimaryChannel,
      title: currentChannels.length > 0 ? `${currentChannels[0]}素材` : '同渠道素材',
      description: '同一使用位置下继续找，适合快速替换相近画面。',
      images: currentChannelImages.slice(0, 4),
    },
    ...(mobileLargeModule ? [mobileLargeModule] : []),
    ...(mobileSmallModule ? [mobileSmallModule] : []),
    {
      browseChannelIntent: buildBrowseChannelIntent('brand_manual', brandChannels, channelEntries),
      title: '品牌手册渠道',
      description: '适合沉淀标准口径和长期复用的规范素材。',
      images: filterByChannels(imagePool, brandChannels).slice(0, 4),
    },
  ];

  const lowerModules: RecommendationModule[] = [
    {
      title: '相关素材推荐',
      description: '和当前素材业务关系更近，适合继续比较表达方式。',
      images: relatedImages.slice(0, 8),
    },
    {
      browseChannelIntent: buildBrowseChannelIntent('website', websiteChannels, channelEntries),
      title: '官网渠道素材',
      description: '适合官网首屏、模块、列表或功能入口继续挑选。',
      images: filterByChannels(imagePool, websiteChannels).slice(0, 6),
    },
    {
      browseChannelIntent: buildBrowseChannelIntent('ppt', pptChannels, channelEntries),
      title: 'PPT 渠道素材',
      description: '适合汇报、讲解或销售材料中承接一页表达。',
      images: filterByChannels(imagePool, pptChannels).slice(0, 6),
    },
  ];

  return { lowerModules, sideModules };
}

const RecommendationPanel = ({
  module,
  variant,
}: {
  module: RecommendationModule;
  variant: 'compact' | 'wide';
}) => {
  const browseState = module.browseChannel || module.browseChannelIntent
    ? {
        browseChannel: module.browseChannel,
        browseChannelIntent: module.browseChannel ? null : module.browseChannelIntent,
      }
    : undefined;

  return (
    <section className="rounded-2xl border border-border/80 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-foreground">{module.title}</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">{module.description}</p>
        </div>
        <Link
          to="/"
          state={browseState}
          className="inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        >
          更多
          <ChevronRight className="size-3.5" />
        </Link>
      </div>
      {module.images.length > 0 ? (
        <div className="compact-scrollbar flex gap-4 overflow-x-auto pb-2">
          {module.images.map((image) => (
            <RecommendationImageLink key={image.id} image={image} variant={variant} />
          ))}
        </div>
      ) : (
        <div className="flex h-20 items-center justify-center rounded-xl bg-secondary/45 text-xs text-muted-foreground">
          暂无可推荐素材
        </div>
      )}
    </section>
  );
};

const RecommendationImageLink = ({
  image,
  variant,
}: {
  image: ImageItem;
  variant: 'compact' | 'wide';
}) => {
  const imageUrl = useImageUrl(previewUrlFor(image));
  return (
    <Link
      to={`/image/${image.id}`}
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
      <p className="mt-1.5 truncate text-xs font-medium text-foreground">{image.title}</p>
    </Link>
  );
};

function filterByChannels(images: ImageItem[], channels: string[]) {
  if (channels.length === 0) return [];
  return images.filter((image) => {
    const imageChannels = splitChannelValue(image.channel);
    return channels.some((channel) => imageChannels.includes(channel));
  });
}

function uniqueImages(images: ImageItem[]) {
  const seen = new Set<string>();
  const result: ImageItem[] = [];
  images.forEach((image) => {
    if (seen.has(image.id)) return;
    seen.add(image.id);
    result.push(image);
  });
  return result;
}

function buildBrowseChannelIntent(
  family: Exclude<ChannelFamily, 'unknown'>,
  channels: string[],
  entries: ChannelIntentEntry[],
): ImageChannelIntent | null {
  const candidateChannels = channels.filter((channel) => {
    return entries.some((entry) => entry.value === channel);
  });
  if (candidateChannels.length === 0) return null;
  const exactChannel = candidateChannels.length === 1 ? candidateChannels[0] : null;
  return {
    channelFamily: family,
    channelSize: 'unspecified',
    exactChannel,
    candidateChannels,
    scenePreference: 'unspecified',
    confidence: 'medium',
    evidence: candidateChannels,
    recommendation: exactChannel
      ? `已切换到${exactChannel}渠道素材。`
      : `已切换到${candidateChannels.join('、')}渠道素材。`,
  };
}

function buildChannelModule({
  family,
  channels,
  channelEntries,
  currentPrimaryChannel,
  description,
  imagePool,
  title,
}: {
  family: Exclude<ChannelFamily, 'unknown'>;
  channels: string[];
  channelEntries: ChannelIntentEntry[];
  currentPrimaryChannel: string;
  description: string;
  imagePool: ImageItem[];
  title: string;
}): RecommendationModule | null {
  if (channels.length === 0 || channels.includes(currentPrimaryChannel)) return null;
  return {
    browseChannelIntent: buildBrowseChannelIntent(family, channels, channelEntries),
    title,
    description,
    images: filterByChannels(imagePool, channels).slice(0, 4),
  };
}

export default BusinessImageDetailRecommendations;
