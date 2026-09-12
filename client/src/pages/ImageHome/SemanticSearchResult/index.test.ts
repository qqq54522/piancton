import { describe, expect, it } from 'vitest';

import { buildRouteSummary } from './index';

describe('buildRouteSummary', () => {
  it('uses the fresh model judgment returned for this search', () => {
    const summary = buildRouteSummary({
      matchedSellingPoints: ['动画精讲'],
      routeExplanation: '这次需求强调把抽象知识讲清楚，因此命中动画精讲。',
    });

    expect(summary?.judgment).toBe(
      '这次需求强调把抽象知识讲清楚，因此命中动画精讲。',
    );
  });

  it('does not present a static template as a completed real-time judgment', () => {
    const summary = buildRouteSummary({
      matchedSellingPoints: ['动画精讲'],
      routeExplanation: null,
    });

    expect(summary?.judgment).toBe('实时判断暂未完成，请重新搜索。');
  });
});
