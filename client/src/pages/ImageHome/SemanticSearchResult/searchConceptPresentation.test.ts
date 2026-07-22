import { describe, expect, it } from 'vitest';

import type { ScoredImageMatch, SearchUnderstanding } from '@client/src/types/api';
import {
  filterResultsByIntent,
  resultMatchExplanation,
  searchEvidencePointOptions,
  searchIntentOptions,
  searchIntentTitle,
  searchProofPointOptions,
} from './searchConceptPresentation';

describe('search concept presentation', () => {
  it('deduplicates system-prefixed concepts and keeps multiple weighted intentions', () => {
    const understanding = {
      matchedBusinessConcepts: [
        { concept: '同步自学体系 > AI拍题精学', weight: 0.95 },
        { concept: 'AI拍题精学', weight: 0.9 },
        { concept: 'AI私教答疑', weight: 0.91 },
        { concept: '极速预习复习', weight: 0.88 },
      ],
    } as SearchUnderstanding;

    expect(searchIntentOptions(understanding)).toEqual([
      { name: 'AI拍题精学', weight: 0.95 },
      { name: 'AI私教答疑', weight: 0.91 },
      { name: '极速预习复习', weight: 0.88 },
    ]);
  });

  it('filters cards by this query match instead of every asset relation', () => {
    const first = {
      matchedQueryConcepts: [
        { conceptCode: 'photo', conceptName: 'AI拍题精学', relationRole: 'expresses' },
      ],
      expressedConcepts: ['AI拍题精学', 'AI私教答疑'],
    } as ScoredImageMatch;
    const second = {
      matchedQueryConcepts: [
        { conceptCode: 'tutor', conceptName: 'AI私教答疑', relationRole: 'supports' },
      ],
      expressedConcepts: ['AI私教答疑'],
    } as ScoredImageMatch;

    expect(filterResultsByIntent([first, second], 'AI私教答疑')).toEqual([second]);
    expect(filterResultsByIntent([first, second], null)).toEqual([first, second]);
  });

  it('does not present unresolved alternatives as simultaneous selling points', () => {
    const understanding = {
      queryType: 'ambiguous_business_intent_search',
      matchedBusinessConcepts: [
        { concept: '学习规划', weight: 0.74 },
        { concept: '专家规划', weight: 0.74 },
      ],
    } as SearchUnderstanding;

    expect(searchIntentOptions(understanding)).toEqual([]);
  });

  it('keeps exploratory options but distinguishes the wording from confirmed multi intent', () => {
    const understanding = {
      queryType: 'exploratory_business_intent_search',
      matchedBusinessConcepts: [
        { concept: '同步自学体系 > AI拍题精学', weight: 0.95 },
        { concept: '同步自学体系 > 极速预习复习', weight: 0.95 },
      ],
    } as SearchUnderstanding;

    expect(searchIntentOptions(understanding)).toHaveLength(2);
    expect(searchIntentTitle('exploratory_business_intent_search')).toBe('你可能在找');
    expect(searchIntentTitle('multi_business_intent_search')).toBe('本次需求同时涉及');
    expect(searchIntentTitle('business_intent_search')).toBe('本次识别到的卖点');
  });

  it('shows reviewed business and asset-phrase evidence instead of internal recall sources', () => {
    const scored = {
      matchedQueryConcepts: [
        { conceptCode: 'tutor', conceptName: 'AI私教答疑', relationRole: 'expresses' },
      ],
      matchReasons: [
        '概念搜索表达命中：AI私教',
        '语义扩展匹配：AI私教答疑',
        'Embedding 语义召回',
        '多路召回一致：3 路',
      ],
    } as ScoredImageMatch;

    expect(resultMatchExplanation(scored)).toBe(
      '主要表达“AI私教答疑”；卖点表达命中：AI私教',
    );
    expect(resultMatchExplanation(scored)).not.toContain('Embedding');
    expect(resultMatchExplanation(scored)).not.toContain('语义扩展');
  });

  it('uses accepted asset-specific language as the within-selling-point explanation', () => {
    const scored = {
      matchedQueryConcepts: [
        { conceptCode: 'school', conceptName: '同步校内', relationRole: 'supports' },
      ],
      matchReasons: [
        '概念搜索表达命中：教材同步',
        '卖点内素材独有话术命中：学校学到哪课程就讲到哪',
      ],
    } as ScoredImageMatch;

    expect(resultMatchExplanation(scored)).toBe(
      '可以支持“同步校内”；素材独有话术命中：学校学到哪课程就讲到哪',
    );
  });

  it('presents proof-point confidence and includes it in the result explanation', () => {
    const understanding = {
      matchedProofPoints: [
        {
          code: 'pp_selfstudy_error_photo_capture',
          conceptCode: 'ai_error_book',
          name: '线下错题拍照上传与归档',
          weight: 0.97,
        },
      ],
    } as SearchUnderstanding;
    const scored = {
      matchedQueryConcepts: [
        { conceptName: 'AI错题本', relationRole: 'expresses' },
      ],
      matchReasons: [
        '证明点匹配：线下错题拍照上传与归档（100%）',
      ],
    } as ScoredImageMatch;

    expect(searchProofPointOptions(understanding)).toEqual([
      { name: '线下错题拍照上传与归档', weight: 0.97 },
    ]);
    expect(resultMatchExplanation(scored)).toBe(
      '主要表达“AI错题本”；证明点：线下错题拍照上传与归档（100%）',
    );
  });

  it('presents the recognized green-source evidence expression', () => {
    const understanding = {
      matchedEvidencePoints: [
        {
          code: 'ep_exam_variant_expansion',
          proofPointCode: 'pp_exam_transfer_variant_practice',
          conceptCode: 'transfer_practice',
          name: '讲完例题后进行同类变式拓展',
          weight: 0.96,
        },
      ],
    } as SearchUnderstanding;

    expect(searchEvidencePointOptions(understanding)).toEqual([
      { name: '讲完例题后进行同类变式拓展', weight: 0.96 },
    ]);
  });
});
