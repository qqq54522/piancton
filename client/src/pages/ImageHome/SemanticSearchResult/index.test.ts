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

  it('falls back to the governed route instead of asking the user to retry', () => {
    const summary = buildRouteSummary({
      matchedSellingPoints: ['动画精讲'],
      routeExplanation: null,
    });

    expect(summary?.judgment).toBe(
      '本次需求命中动画精讲，结果已按该卖点的人工确认关系进行准入。',
    );
  });
});
