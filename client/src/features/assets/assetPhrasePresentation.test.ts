import { describe, expect, it } from 'vitest';

import type { AssetSearchPhrase } from '@client/src/types/api';
import { splitAssetSearchPhrases } from './assetPhrasePresentation';

describe('asset phrase presentation', () => {
  it('combines manual and accepted AI phrases while keeping pending AI candidates separate', () => {
    const phrases = [
      {
        id: 'manual-accepted',
        phrase: '人工新增说法',
        origin: 'manual',
        reviewStatus: 'accepted',
      },
      {
        id: 'ai-accepted',
        phrase: '已采纳 AI 说法',
        origin: 'ai',
        reviewStatus: 'accepted',
      },
      {
        id: 'ai-pending',
        phrase: '待审核 AI 说法',
        origin: 'ai',
        reviewStatus: 'pending',
      },
      {
        id: 'ai-rejected',
        phrase: '已拒绝 AI 说法',
        origin: 'ai',
        reviewStatus: 'rejected',
      },
      {
        id: 'duplicate-pending',
        phrase: ' 人工新增说法 ',
        origin: 'ai',
        reviewStatus: 'pending',
      },
    ] as AssetSearchPhrase[];

    const result = splitAssetSearchPhrases(phrases);

    expect(result.accepted.map((item) => item.phrase)).toEqual([
      '人工新增说法',
      '已采纳 AI 说法',
    ]);
    expect(result.pendingAi.map((item) => item.phrase)).toEqual([
      '待审核 AI 说法',
    ]);
  });
});
