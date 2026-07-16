import { describe, expect, it } from 'vitest';

import type { ScoredImageMatch, SearchUnderstanding } from '@client/src/types/api';
import {
  filterResultsByIntent,
  searchIntentOptions,
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
});
