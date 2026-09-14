// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook } from '@testing-library/react';
import type { PropsWithChildren } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useGlobalImageSearch } from './useGlobalImageSearch';

vi.mock('@client/src/features/assets/useBusinessConcepts', () => ({
  useBusinessConcepts: () => ({ data: [] }),
}));

vi.mock('@client/src/features/assets/useBusinessFacets', () => ({
  useBusinessFacets: () => ({ data: { proofPoints: [], evidencePoints: [] } }),
}));

vi.mock('@client/src/pages/ImageHome/channelIntentCatalog', () => ({
  isChannelIntentInCatalog: () => false,
  useChannelIntentEntries: () => [],
}));

describe('useGlobalImageSearch channel browsing', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it('leaves a persisted manual selling-point result before browsing a channel', () => {
    window.sessionStorage.setItem('piancton:image-search-state:v2', JSON.stringify({
      input: '',
      keyword: '',
      systemCode: 'sync_companion',
      conceptCode: 'learning_report',
      proofPointCode: null,
      evidencePointCode: null,
      channel: '',
      channelIntent: null,
      scene: 'all',
      result: {
        semantic: null,
        images: [{ id: 'stale-search-image' }],
        source: 'manual',
      },
    }));
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(
      () => useGlobalImageSearch({ allTags: [] }),
      { wrapper },
    );

    expect(result.current.hasManualSearchResult).toBe(true);
    act(() => result.current.setSelectedChannel('PPT'));

    expect(result.current.hasManualSearchResult).toBe(false);
    expect(result.current.globalSearchImages).toEqual([]);
    expect(result.current.selectedConceptCode).toBeNull();
    expect(result.current.selectedSystemCode).toBeNull();
    expect(result.current.searchRefinements.channel).toBe('PPT');
  });
});
