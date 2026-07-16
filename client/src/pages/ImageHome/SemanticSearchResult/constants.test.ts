import { describe, expect, it } from 'vitest';

import { FEEDBACK_OPTIONS } from './constants';

describe('search feedback copy', () => {
  it('keeps the overall relevance option and explains why to submit a request', () => {
    expect(FEEDBACK_OPTIONS).toContainEqual({
      type: 'not_relevant',
      label: '结果不相关',
    });
    expect(FEEDBACK_OPTIONS).toContainEqual({
      type: 'asset_request',
      label: '没有合适素材提交需求',
    });
  });
});
