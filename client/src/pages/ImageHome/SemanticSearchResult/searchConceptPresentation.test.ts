import { describe, expect, it } from 'vitest';

import type { ScoredImageMatch, SearchUnderstanding } from '@client/src/types/api';
import {
  filterResultsByIntent,
  resultMatchExplanation,
  resultRecommendationCopy,
  searchEvidencePointOptions,
  searchIntentOptions,
  searchIntentTitle,
  searchProofPointOptions,
  resultRecommendedPoint,
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
    } as unknown as ScoredImageMatch;
    const second = {
      matchedQueryConcepts: [
        { conceptCode: 'tutor', conceptName: 'AI私教答疑', relationRole: 'supports' },
      ],
      expressedConcepts: ['AI私教答疑'],
    } as unknown as ScoredImageMatch;

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

  it('shows clean business language instead of internal recall sources', () => {
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

    expect(resultMatchExplanation(scored)).toBe('AI私教');
    expect(resultMatchExplanation(scored)).not.toContain('Embedding');
    expect(resultMatchExplanation(scored)).not.toContain('语义扩展');
  });

  it('uses the dynamic result recommendation reason before old manual recommendation text', () => {
    const scored = {
      resultRecommendationReason: '推荐这张图，因为它结合本次搜索和素材画面说明了课后小测价值',
      matchedQueryConcepts: [
        {
          conceptCode: 'instant_quiz',
          conceptName: '课后小测',
          relationRole: 'expresses',
          recommendationText: '有没有能体现课后小测后当天会不会一眼看出来的图',
        },
        {
          conceptCode: 'learning_report',
          conceptName: '学情报告反馈',
          relationRole: 'supports',
          recommendationText: '这张图也可以讲报告，但本次搜索没有命中它',
        },
      ],
      primaryProofPointName: '课后数据反馈',
      primaryProofPointClaim: '旧的证明点兜底文案',
      matchReasons: [
        '卖点内素材独有话术命中：旧素材话术',
      ],
    } as ScoredImageMatch;

    expect(resultRecommendedPoint(scored)).toBe('课后小测');
    expect(resultMatchExplanation(scored)).toBe(
      '推荐这张图，因为它结合本次搜索和素材画面说明了课后小测价值',
    );
  });

  it('splits dynamic recommendation text into primary and secondary display levels', () => {
    const scored = ({
      resultRecommendationReason: '推荐这张「教材同步」\n因为它能说明学校课程同步',
      matchReasons: [],
    } as unknown) as ScoredImageMatch;

    expect(resultRecommendationCopy(scored)).toEqual({
      primary: '推荐这张「教材同步」',
      secondary: ['因为它能说明学校课程同步'],
    });
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
      '学校学到哪课程就讲到哪',
    );
  });

  it('presents proof-point confidence and keeps the query selling point as recommendation point', () => {
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
      primaryProofPointName: '线下错题拍照上传与归档',
      primaryProofPointClaim: '把学生线下错题拍照保存，自动整理成个人错题本，后续可以反复复练。',
      matchReasons: [
        '证明点匹配：线下错题拍照上传与归档（100%）',
      ],
    } as ScoredImageMatch;

    expect(searchProofPointOptions(understanding)).toEqual([
      { name: '线下错题拍照上传与归档', weight: 0.97 },
    ]);
    expect(resultRecommendedPoint(scored)).toBe('AI错题本');
    expect(resultMatchExplanation(scored)).toBe('把学生线下错题拍照保存，自动整理成个人错题本，后续可以反复复练。');
  });

  it('keeps cards with the same proof point on the same recommendation copy', () => {
    const scored = {
      primaryProofPointName: '全网与群体高频易错题功能',
      matchReasons: [
        '证明点匹配：全网与群体高频易错题功能（92%）',
        '卖点内素材独有话术命中：找一张能体现专门练全网高频错题、集中突破难题的图',
      ],
    } as ScoredImageMatch;

    expect(resultRecommendedPoint(scored)).toBe('全网与群体高频易错题功能');
    expect(resultMatchExplanation(scored)).toBe(
      '依托上亿学生答题数据，系统自动标记全学科高频易错题，区分共性易错坑点；同时内置个人专属错题本，自动收录孩子自身错题。',
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
