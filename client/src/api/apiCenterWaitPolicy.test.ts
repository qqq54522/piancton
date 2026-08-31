import { describe, expect, it } from 'vitest';

import {
  apiCenterRequestWaitMs,
  recommendedApiCallLimitSeconds,
} from './apiCenterWaitPolicy';

describe('API Center wait policy', () => {
  it('keeps the page wait longer than a single provider call', () => {
    expect(apiCenterRequestWaitMs(60)).toBe(75_000);
  });

  it('accounts for parallel rounds when checking all credentials', () => {
    expect(apiCenterRequestWaitMs(60, 20, 4)).toBe(315_000);
  });

  it('derives a guarded call limit from the slowest successful probe', () => {
    expect(recommendedApiCallLimitSeconds([2200])).toBe(20);
    expect(recommendedApiCallLimitSeconds([18_400])).toBe(47);
    expect(recommendedApiCallLimitSeconds([45_000])).toBe(60);
  });
});
