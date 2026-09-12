import { useEffect, useMemo, useRef } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { fetchImages, recordSearchInteraction } from '@client/src/api/image';
import { previewUrlFor } from '@client/src/features/images/imagePreview';
import { useImageUrl } from '@client/src/hooks/useImageUrl';
import type {
  ImageDetail,
  ImageItem,
  ImageRecommendationSection,
  SearchInteractionSource,
} from '@client/src/types/api';
import type {
  ChannelFamily,
  ChannelIntentEntry,
  ImageChannelIntent,
} from '../ImageHome/channelIntent';
import { useChannelIntentEntries } from '../ImageHome/channelIntentCatalog';
import { splitChannelValue } from '../ImageHome/channelValue';

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
  eventSource: SearchInteractionSource;
  images: ImageItem[];
  key: string;
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

  if (modules.length === 0) return null;

  return (
    <div
      className="compact-scrollbar space-y-5 xl:max-h-[calc(100vh-5rem)] xl:overflow-y-auto xl:overscroll-contain xl:pr-1"
      style={scrollStyle}
    >
      {modules.map((module) => (
        <RecommendationPanel key={module.key} module={module} variant="compact" />
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
        <RecommendationPanel key={module.key} module={module} variant="wide" />
      ))}
    </div>
  );
};

function useBusinessDetailRecommendationModules(detail: ImageDetail) {
  const channelEntries = useChannelIntentEntries();
  const imageQuery = useQuery({
    queryKey: ['images', 'detail-recommendations'],
    queryFn: () => fetchImages({ limit: MAX_POOL_SIZE, sortBy: 'createdAt' }),
    staleTime: 30_000,
  });
  const sections = useMemo(
    () => detail.recommendationSections ?? [],
    [detail.recommendationSections],
  );
  const imagePool = useMemo(
    () => uniqueImages([
      ...sections.flatMap((section) => section.images ?? []),
      ...(detail.relatedImages ?? []),
      ...(imageQuery.data?.items ?? []),
    ]).filter((image) => image.id !== detail.id),
    [detail.id, detail.relatedImages, imageQuery.data?.items, sections],
  );
  const currentChannels = splitChannelValue(detail.channel);
  const currentPrimaryChannel = currentChannels[0] ?? '';
  const sameSellingPoint = findSection(sections, 'same_selling_point');
  const visualSimilar = findSection(sections, 'visual_similar');
  const personalized = findSection(sections, 'personalized');
  const serverSameChannel = findSection(sections, 'same_channel');
  const currentChannelImages = uniqueImages([
    ...(serverSameChannel?.images ?? []),
    ...filterByChannels(imagePool, currentChannels),
  ]).slice(0, 4);
  const brandChannels = channelsFor(channelEntries, 'brand_manual');
  const mobileLargeChannels = channelsFor(channelEntries, 'mobile', 'large');
  const mobileSmallChannels = channelsFor(channelEntries, 'mobile', 'small');
  const websiteChannels = channelsFor(channelEntries, 'website');
  const pptChannels = channelsFor(channelEntries, 'ppt');

  const mobileLargeModule = buildChannelModule({
    key: 'mobile-large',
    eventSource: 'detail_mobile_large',
    family: 'mobile',
    channels: mobileLargeChannels,
    channelEntries,
    currentPrimaryChannel,
    description: '适合手机端首屏、朋友圈长图或重点宣传位继续挑选。',
    imagePool,
    title: '手机端大图素材',
  });
  const mobileSmallModule = buildChannelModule({
    key: 'mobile-small',
    eventSource: 'detail_mobile_small',
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
      key: 'current-channel',
      eventSource: 'detail_current_channel',
      title: currentChannels.length > 0 ? `${currentChannels[0]}素材` : '同渠道素材',
      description: '同一使用位置下继续找，适合快速替换当前版位素材。',
      images: currentChannelImages,
    },
    ...(personalized ? [sectionModule(personalized, 'detail_personalized')] : []),
    ...(mobileLargeModule ? [mobileLargeModule] : []),
    ...(mobileSmallModule ? [mobileSmallModule] : []),
    {
      browseChannelIntent: buildBrowseChannelIntent(
        'brand_manual',
        brandChannels,
        channelEntries,
      ),
      key: 'brand-manual',
      eventSource: 'detail_brand_manual',
      title: '品牌手册渠道',
      description: '适合沉淀标准口径和长期复用的规范素材。',
      images: filterByChannels(imagePool, brandChannels).slice(0, 4),
    },
  ];

  const hasPurposeSections = sections.length > 0;
  const legacyRelatedImages = uniqueImages(detail.relatedImages ?? [])
    .filter((image) => image.id !== detail.id);
  const primaryRelatedModule: RecommendationModule = hasPurposeSections
    ? {
        key: 'same-selling-point',
        eventSource: 'detail_same_selling_point',
        title: '相关素材推荐',
        description: sameSellingPoint?.description
          ?? '优先推荐支撑同一卖点的其它表达，适合直接替换或继续比较。',
        images: sameSellingPoint?.images ?? [],
      }
    : {
        key: 'legacy-related',
        eventSource: 'detail_visual_similar',
        title: '相关素材推荐',
        description: '和当前素材业务关系更近，适合继续比较表达方式。',
        images: legacyRelatedImages.slice(0, 8),
      };

  const lowerModules: RecommendationModule[] = [
    primaryRelatedModule,
    ...(visualSimilar ? [sectionModule(visualSimilar, 'detail_visual_similar')] : []),
    {
      browseChannelIntent: buildBrowseChannelIntent('website', websiteChannels, channelEntries),
      key: 'website',
      eventSource: 'detail_website',
      title: '官网渠道素材',
      description: '适合官网首屏、模块、列表或功能入口继续挑选。',
      images: filterByChannels(imagePool, websiteChannels).slice(0, 6),
    },
    {
      browseChannelIntent: buildBrowseChannelIntent('ppt', pptChannels, channelEntries),
      key: 'ppt',
      eventSource: 'detail_ppt',
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
      {module.images.length > 0 ? (
        <div className="compact-scrollbar flex gap-4 overflow-x-auto pb-2">
          {module.images.map((image, index) => (
            <RecommendationImageLink
              key={image.id}
              image={image}
              position={index + 1}
              source={module.eventSource}
              variant={variant}
            />
          ))}
        </div>
      ) : (
        <div className="flex h-20 items-center justify-center rounded-xl bg-secondary/45 text-sm text-muted-foreground">
          暂无可推荐素材
        </div>
      )}
    </section>
  );
};

const RecommendationImageLink = ({
  image,
  position,
  source,
  variant,
}: {
  image: ImageItem;
  position: number;
  source: SearchInteractionSource;
  variant: 'compact' | 'wide';
}) => {
  const imageUrl = useImageUrl(previewUrlFor(image));
  const linkRef = useRef<HTMLAnchorElement | null>(null);
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

function findSection(
  sections: ImageRecommendationSection[],
  purpose: ImageRecommendationSection['purpose'],
) {
  return sections.find((section) => section.purpose === purpose);
}

function sectionModule(
  section: ImageRecommendationSection,
  eventSource: SearchInteractionSource,
): RecommendationModule {
  return {
    key: section.purpose,
    eventSource,
    title: section.title,
    description: section.description,
    images: section.images ?? [],
  };
}

function channelsFor(
  entries: ChannelIntentEntry[],
  family: Exclude<ChannelFamily, 'unknown'>,
  size?: 'large' | 'small',
) {
  return entries
    .filter((entry) => entry.family === family && (!size || entry.size === size))
    .map((entry) => entry.value);
}

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
  key,
  eventSource,
  family,
  channels,
  channelEntries,
  currentPrimaryChannel,
  description,
  imagePool,
  title,
}: {
  key: string;
  eventSource: SearchInteractionSource;
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
    key,
    eventSource,
    browseChannelIntent: buildBrowseChannelIntent(family, channels, channelEntries),
    title,
    description,
    images: filterByChannels(imagePool, channels).slice(0, 4),
  };
}

export default BusinessImageDetailRecommendations;
