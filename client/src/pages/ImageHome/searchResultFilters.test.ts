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
  conceptNames: string[] = [],
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
    matchedQueryConcepts: conceptNames.map((conceptName) => ({
      conceptCode: conceptName,
      conceptName,
      relationRole: 'expresses',
    })),
    expressedConcepts: conceptNames,
    supportedConcepts: [],
    matchedBusinessConcepts: conceptNames,
  } as unknown as ScoredImageMatch;
}

describe('search result refinements', () => {
  const items = [
    match('one', true, ['官网小图、公众号']),
    match('two', false, ['朋友圈']),
    match('mobile-large', false, ['手机端大图']),
    match('mobile-small', false, ['手机端小图']),
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

  it('does not apply channel filtering when the query has no channel wording', () => {
    expect(filterResultsByRefinements(items, {
      channel: '',
      channelIntent: null,
      scene: 'all',
    }).map((item) => item.image.id)).toEqual([
      'one',
      'two',
      'mobile-large',
      'mobile-small',
      'three',
    ]);
  });

  it('keeps all matched selling point results when no channel is specified', () => {
    const multiConceptItems = [
      match('photo-mobile', false, ['手机端大图'], ['AI拍题精学']),
      match('transfer-website', false, ['官网大图'], ['举一反三']),
      match('photo-small', false, ['手机端小图'], ['AI拍题精学']),
    ];

    expect(filterResultsByRefinements(
      multiConceptItems,
      {
        channel: '',
        channelIntent: null,
        scene: 'all',
      },
      { preserveConceptNames: ['AI拍题精学', '举一反三'] },
    ).map((item) => item.image.id)).toEqual([
      'photo-mobile',
      'transfer-website',
      'photo-small',
    ]);
  });

  it('keeps explicit manual channel filters strict even when preserving selling points', () => {
    const multiConceptItems = [
      match('photo-mobile', false, ['手机端大图'], ['AI拍题精学']),
      match('transfer-website', false, ['官网大图'], ['举一反三']),
    ];

    expect(filterResultsByRefinements(
      multiConceptItems,
      {
        channel: '手机端大图',
        channelIntent: null,
        scene: 'all',
      },
      { preserveConceptNames: ['AI拍题精学', '举一反三'] },
    ).map((item) => item.image.id)).toEqual(['photo-mobile']);
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
    }).map((item) => item.image.id)).toEqual(['two', 'mobile-large', 'mobile-small']);
  });

  it('uses detected scene preference when no manual scene filter is selected', () => {
    expect(filterResultsByRefinements(items, {
      channel: '',
      channelIntent: {
        channelFamily: 'mobile',
        channelSize: 'unspecified',
        exactChannel: null,
        candidateChannels: ['手机端大图', '手机端小图'],
        scenePreference: 'non_scene',
        confidence: 'high',
        evidence: ['功能图'],
        recommendation: '已理解为功能图',
      },
      scene: 'all',
    }).map((item) => item.image.id)).toEqual(['mobile-large', 'mobile-small']);

    expect(filterResultsByRefinements(items, {
      channel: '',
      channelIntent: {
        channelFamily: 'mobile',
        channelSize: 'unspecified',
        exactChannel: null,
        candidateChannels: ['手机端大图', '手机端小图'],
        scenePreference: 'scene',
        confidence: 'high',
        evidence: ['场景图'],
        recommendation: '已理解为场景图',
      },
      scene: 'all',
    }).map((item) => item.image.id)).toEqual([]);
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
    }).map((item) => item.image.id)).toEqual(['mobile-large', 'mobile-small']);
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
