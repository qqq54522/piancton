import type { ScoredImageMatch } from '@client/src/types/api';

export type SceneImageFilter = 'all' | 'scene' | 'nonScene';

export interface SearchRefinements {
  channel: string;
  style: string;
  scene: SceneImageFilter;
}

export interface SearchRefinementOptions {
  channels: string[];
  styles: string[];
  hasKnownSceneType: boolean;
}

export const EMPTY_SEARCH_REFINEMENTS: SearchRefinements = {
  channel: '',
  style: '',
  scene: 'all',
};

export function collectSearchRefinementOptions(
  items: ScoredImageMatch[],
): SearchRefinementOptions {
  const channels = new Set<string>();
  const styles = new Set<string>();
  let hasKnownSceneType = false;

  items.forEach((item) => {
    item.availableVariants.forEach((variant) => {
      if (variant.channel?.trim()) channels.add(variant.channel.trim());
    });
    if (item.image.channel?.trim()) channels.add(item.image.channel.trim());
    if (item.image.styleLabel?.trim()) styles.add(item.image.styleLabel.trim());
    if (typeof item.image.isSceneImage === 'boolean') hasKnownSceneType = true;
  });

  return {
    channels: [...channels].sort((left, right) => left.localeCompare(right, 'zh-CN')),
    styles: [...styles].sort((left, right) => left.localeCompare(right, 'zh-CN')),
    hasKnownSceneType,
  };
}

export function filterResultsByRefinements(
  items: ScoredImageMatch[],
  refinements: SearchRefinements,
): ScoredImageMatch[] {
  return items.filter((item) => {
    const variants = item.availableVariants.length > 0
      ? item.availableVariants
      : [{ channel: item.image.channel }];
    if (
      refinements.channel
      && !variants.some((variant) => variant.channel?.trim() === refinements.channel)
    ) return false;
    if (refinements.style && item.image.styleLabel?.trim() !== refinements.style) return false;
    if (refinements.scene === 'scene' && item.image.isSceneImage !== true) return false;
    if (refinements.scene === 'nonScene' && item.image.isSceneImage !== false) return false;
    return true;
  });
}

export function activeRefinementCount(refinements: SearchRefinements): number {
  return Number(Boolean(refinements.channel))
    + Number(Boolean(refinements.style))
    + Number(refinements.scene !== 'all');
}
