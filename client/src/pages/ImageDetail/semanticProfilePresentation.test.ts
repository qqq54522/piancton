import { describe, expect, it } from 'vitest';

import { visibleSemanticProfileGroups } from './semanticProfilePresentation';

describe('visibleSemanticProfileGroups', () => {
  it('only exposes the three high-value groups on the image detail page', () => {
    const groups = visibleSemanticProfileGroups({
      schemaVersion: 2,
      visualFacts: ['手机章节与课本目录对应'],
      ocrText: ['数学 八年级 下册'],
      subjects: ['手机学习应用界面'],
      scenes: ['教材章节对照场景'],
      actions: ['切换学习章节'],
      visualStyle: ['左右对照构图'],
      visibleProductFeatures: ['章节切换列表'],
      assetSearchPhrases: ['手机章节切换对照课本目录'],
      negativeVisualConcepts: ['没有人物学习场景'],
    });

    expect(groups).toEqual([
      { key: 'visualFacts', title: '画面事实', items: ['手机章节与课本目录对应'] },
      { key: 'scenes', title: '场景', items: ['教材章节对照场景'] },
      {
        key: 'assetSearchPhrases',
        title: '素材独有搜索表达',
        items: ['手机章节切换对照课本目录'],
      },
    ]);
  });

  it('omits empty visible groups', () => {
    expect(visibleSemanticProfileGroups({ schemaVersion: 2 })).toEqual([]);
  });
});
