import { describe, expect, it } from 'vitest';

import { clearLegacyAssetAgentStorage } from './assetAgentStorage';

describe('clearLegacyAssetAgentStorage', () => {
  it('removes legacy browser-persisted Agent records without touching other settings', () => {
    const removed: string[] = [];

    clearLegacyAssetAgentStorage({
      removeItem: (key) => removed.push(key),
    });

    expect(removed).toEqual([
      'piancton.assetAgent.sessions.v1',
      'piancton.assetAgent.session.v1',
      'piancton.assetAgent.chat.v1',
      'piancton.assetAgent.state.v1',
    ]);
  });
});
