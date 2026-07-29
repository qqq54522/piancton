import { describe, expect, it } from 'vitest';

import type { ScoredImageMatch } from '@client/src/types/api';
import {
  activeRefinementCount,
  collectSearchRefinementOptions,
  filterResultsByRefinements,
} from './searchResultFilters';

function match(
  id: string,
  isSceneImage: boolean | null,
  channels: string[],
): ScoredImageMatch {
  return {
    image: {
      id,
      channel: channels[0] ?? null,
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
    match('one', true, ['官网小图、公众号']),
    match('two', false, ['朋友圈']),
    match('three', null, []),
  ];

  it('collects fixed channel choices before legacy channel values', () => {
    expect(collectSearchRefinementOptions(items)).toEqual({
      channels: ['PPT', '品牌手册', '手机端大图', '手机端小图', '官网大图', '官网小图', '公众号', '朋友圈'],
      hasKnownSceneType: true,
    });
  });

  it('keeps AI result order while applying exact manual filters', () => {
    expect(filterResultsByRefinements(items, {
      channel: '公众号',
      channelIntent: null,
      scene: 'scene',
    }).map((item) => item.image.id)).toEqual(['one']);
  });

  it('matches each channel inside multi-channel values', () => {
    const multiChannelItems = [
      match('multi', false, ['PPT、手机端大图']),
      match('ppt-only', false, ['PPT']),
    ];

    expect(filterResultsByRefinements(multiChannelItems, {
      channel: '',
      channelIntent: {
        channelFamily: 'mobile',
        channelSize: 'large',
        exactChannel: '手机端大图',
        candidateChannels: ['手机端大图'],
        scenePreference: 'unspecified',
        confidence: 'high',
        evidence: ['手机端大图'],
        recommendation: '已理解为手机端大图',
      },
      scene: 'all',
    }).map((item) => item.image.id)).toEqual(['multi']);
  });

  it('does not treat unmarked assets as non-scene images', () => {
    expect(filterResultsByRefinements(items, {
      channel: '',
      channelIntent: null,
      scene: 'nonScene',
    }).map((item) => item.image.id)).toEqual(['two']);
  });

  it('uses detected channel intent as an exact channel filter', () => {
    expect(filterResultsByRefinements(items, {
      channel: '',
      channelIntent: {
        channelFamily: 'website',
        channelSize: 'small',
        exactChannel: '官网小图',
        candidateChannels: ['官网小图'],
        scenePreference: 'unspecified',
        confidence: 'high',
        evidence: ['官网', '小图'],
        recommendation: '推荐用于官网小图',
      },
      scene: 'all',
    }).map((item) => item.image.id)).toEqual(['one']);

    expect(filterResultsByRefinements(items, {
      channel: '',
      channelIntent: {
        channelFamily: 'mobile',
        channelSize: 'unspecified',
        exactChannel: null,
        candidateChannels: ['手机端大图', '手机端小图'],
        scenePreference: 'unspecified',
        confidence: 'medium',
        evidence: ['手机端'],
        recommendation: '已理解为手机端',
      },
      scene: 'all',
    }).map((item) => item.image.id)).toEqual([]);
  });

  it('counts every highlighted channel candidate in detected intent', () => {
    expect(activeRefinementCount({
      channel: '',
      channelIntent: {
        channelFamily: 'mobile',
        channelSize: 'unspecified',
        exactChannel: null,
        candidateChannels: ['手机端大图', '手机端小图'],
        scenePreference: 'unspecified',
        confidence: 'medium',
        evidence: ['手机端'],
        recommendation: '已理解为手机端',
      },
      scene: 'all',
    })).toBe(2);
  });
});
