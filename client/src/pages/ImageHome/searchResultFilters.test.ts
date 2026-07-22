import { describe, expect, it } from 'vitest';

import type { ScoredImageMatch } from '@client/src/types/api';
import {
  collectSearchRefinementOptions,
  filterResultsByRefinements,
} from './searchResultFilters';

function match(
  id: string,
  styleLabel: string | null,
  isSceneImage: boolean | null,
  channels: string[],
): ScoredImageMatch {
  return {
    image: {
      id,
      channel: channels[0] ?? null,
      styleLabel,
      isSceneImage,
    },
    availableVariants: channels.map((channel, index) => ({
      id: `${id}-${index}`,
      channel,
    })),
  } as unknown as ScoredImageMatch;
}

describe('search result refinements', () => {
  const items = [
    match('one', '官网风格', true, ['官网', '公众号']),
    match('two', '朋友圈风格', false, ['朋友圈']),
    match('three', null, null, []),
  ];

  it('collects manual metadata from ranked result groups', () => {
    expect(collectSearchRefinementOptions(items)).toEqual({
      channels: ['公众号', '官网', '朋友圈'],
      styles: ['官网风格', '朋友圈风格'],
      hasKnownSceneType: true,
    });
  });

  it('keeps AI result order while applying exact manual filters', () => {
    expect(filterResultsByRefinements(items, {
      channel: '公众号',
      style: '官网风格',
      scene: 'scene',
    }).map((item) => item.image.id)).toEqual(['one']);
  });

  it('does not treat unmarked assets as non-scene images', () => {
    expect(filterResultsByRefinements(items, {
      channel: '',
      style: '',
      scene: 'nonScene',
    }).map((item) => item.image.id)).toEqual(['two']);
  });
});
