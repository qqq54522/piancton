// @vitest-environment jsdom

import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@client/src/api/image', () => ({
  fetchImages: vi.fn().mockResolvedValue({ items: [], hasMore: false }),
  recordSearchInteraction: vi.fn().mockResolvedValue(undefined),
}));

import type { ImageDetail, ImageItem } from '@client/src/types/api';
import BusinessImageDetailRecommendations, {
  BusinessImageDetailSideRecommendations,
} from './BusinessImageDetailRecommendations';

const image = (id: string, title: string): ImageItem => ({
  id,
  title,
  fileName: `${id}.png`,
  contentUrl: `/api/images/${id}/content`,
  thumbnailUrl: `/api/images/${id}/thumbnail`,
  downloadUrl: `/api/images/${id}/download`,
  mediaType: 'image/png',
  sizeBytes: 100,
  uploader: 'designer',
  downloadCount: 0,
  createdAt: '2026-09-12T00:00:00Z',
  assetRole: 'primary',
  versionNo: 1,
  isCurrent: true,
  variantCount: 1,
});

const detail = {
  ...image('source', '当前图片'),
  channel: 'PPT',
  relatedImages: [],
  analysisRuns: [],
  recommendationSections: [
    {
      purpose: 'same_selling_point',
      title: '同卖点可替换',
      description: '与当前素材支撑同一卖点，适合换一种表达。',
      source: 'business_relations',
      images: [image('same-point', '同卖点素材')],
    },
    {
      purpose: 'visual_similar',
      title: '相似画面与主题',
      description: '画面接近。',
      source: 'semantic_profile',
      images: [image('visual', '相似画面素材')],
    },
    {
      purpose: 'personalized',
      title: '为你推荐',
      description: '由火山推荐持续调整。',
      source: 'ai_search',
      images: [image('personalized', '个性化素材')],
    },
  ],
} satisfies ImageDetail;

describe('BusinessImageDetailRecommendations', () => {
  it('keeps the original business entrances and the new recommendation purposes separate', () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <BusinessImageDetailRecommendations detail={detail} />
          <BusinessImageDetailSideRecommendations detail={detail} />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('相关素材推荐')).toBeTruthy();
    expect(screen.getByText('同卖点素材')).toBeTruthy();
    expect(screen.getByText('PPT素材')).toBeTruthy();
    expect(screen.getByText('手机端大图素材')).toBeTruthy();
    expect(screen.getByText('手机端小图素材')).toBeTruthy();
    expect(screen.getByText('品牌手册渠道')).toBeTruthy();
    expect(screen.getByText('官网渠道素材')).toBeTruthy();
    expect(screen.getByText('PPT 渠道素材')).toBeTruthy();
    expect(screen.getByText('相似画面与主题')).toBeTruthy();
    expect(screen.getByText('为你推荐')).toBeTruthy();
    expect(screen.getByText('个性化素材')).toBeTruthy();
  });
});
