import type { ScoredImageMatch } from '@client/src/types/api';
import type { ImageChannelIntent } from './channelIntent';
import { channelValueIncludes, splitChannelValue } from './channelValue';
import { CHANNEL_VALUES } from './channelRecommendations';

export type SceneImageFilter = 'all' | 'scene' | 'nonScene';

export interface SearchRefinements {
  channel: string;
  channelIntent: ImageChannelIntent | null;
  scene: SceneImageFilter;
}

export interface SearchRefinementOptions {
  channels: string[];
  hasKnownSceneType: boolean;
}

export const EMPTY_SEARCH_REFINEMENTS: SearchRefinements = {
  channel: '',
  channelIntent: null,
  scene: 'all',
};

export function collectSearchRefinementOptions(
  items: ScoredImageMatch[],
): SearchRefinementOptions {
  const channels = new Set<string>();
  let hasKnownSceneType = false;

  items.forEach((item) => {
    item.availableVariants.forEach((variant) => {
      splitChannelValue(variant.channel).forEach((channel) => channels.add(channel));
    });
    splitChannelValue(item.image.channel).forEach((channel) => channels.add(channel));
    if (typeof item.image.isSceneImage === 'boolean') hasKnownSceneType = true;
  });

  return {
    channels: [
      ...CHANNEL_VALUES,
      ...[...channels]
        .filter((channel) => !CHANNEL_VALUES.includes(channel))
        .sort((left, right) => left.localeCompare(right, 'zh-CN')),
    ],
    hasKnownSceneType,
  };
}

export function filterResultsByRefinements(
  items: ScoredImageMatch[],
  refinements: SearchRefinements,
): ScoredImageMatch[] {
  const intentChannels = refinements.channel
    ? []
    : refinements.channelIntent?.candidateChannels ?? [];

  return items.filter((item) => {
    const variants = item.availableVariants.length > 0
      ? item.availableVariants
      : [{ channel: item.image.channel }];
    if (
      refinements.channel
      && !variants.some((variant) => channelValueIncludes(variant.channel, refinements.channel))
    ) return false;
    if (intentChannels.length > 0 && !matchHasAnyChannel(item, intentChannels)) return false;
    if (refinements.scene === 'scene' && item.image.isSceneImage !== true) return false;
    if (refinements.scene === 'nonScene' && item.image.isSceneImage !== false) return false;
    return true;
  });
}

export function activeRefinementCount(refinements: SearchRefinements): number {
  return Number(Boolean(refinements.channel))
    + (!refinements.channel ? refinements.channelIntent?.candidateChannels.length ?? 0 : 0)
    + Number(refinements.scene !== 'all');
}

function matchHasAnyChannel(item: ScoredImageMatch, channels: string[]): boolean {
  const variants = item.availableVariants.length > 0
    ? item.availableVariants
    : [{ channel: item.image.channel }];
  return variants.some((variant) => {
    return channels.some((channel) => channelValueIncludes(variant.channel, channel));
  });
}
