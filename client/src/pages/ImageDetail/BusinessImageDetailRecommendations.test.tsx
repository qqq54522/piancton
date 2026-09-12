// @vitest-environment jsdom

import { render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@client/src/api/image', () => ({
  fetchImages: vi.fn().mockResolvedValue({ items: [], hasMore: false }),
  recordSearchInteraction: vi.fn().mockResolvedValue(undefined),
}));

import type { ImageDetail, ImageItem } from '@client/src/types/api';
import { fetchImages } from '@client/src/api/image';
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
      images: [{ ...image('personalized', '个性化素材'), channel: 'PPT' }],
    },
  ],
} satisfies ImageDetail;

describe('BusinessImageDetailRecommendations', () => {
  it('shows selling-point similarity and distributes personalization into channel entrances', async () => {
    vi.mocked(fetchImages).mockResolvedValue({
      items: [{ ...image('regular-ppt', '普通 PPT 素材'), channel: 'PPT' }],
      hasMore: false,
    });
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

    expect(screen.getByText('相似素材')).toBeTruthy();
    expect(screen.getByText('同卖点素材')).toBeTruthy();
    expect(screen.getByText('PPT素材')).toBeTruthy();
    expect(screen.getByText('手机端大图素材')).toBeTruthy();
    expect(screen.getByText('手机端小图素材')).toBeTruthy();
    expect(screen.getByText('品牌手册渠道')).toBeTruthy();
    expect(screen.getByText('官网渠道素材')).toBeTruthy();
    expect(screen.getByText('PPT 渠道素材')).toBeTruthy();
    expect(screen.queryByText('相似画面与主题')).toBeNull();
    expect(screen.queryByText('为你推荐')).toBeNull();
    expect(screen.getAllByText('个性化素材')).toHaveLength(2);
    await screen.findAllByText('普通 PPT 素材');

    const pptSection = screen.getByRole('heading', { name: 'PPT 渠道素材' }).closest('section');
    expect(pptSection).toBeTruthy();
    const pptImageLinks = within(pptSection as HTMLElement)
      .getAllByRole('link')
      .filter((link) => link.getAttribute('href')?.startsWith('/image/'));
    expect(pptImageLinks[0]?.getAttribute('href')).toBe('/image/personalized');
  });
});
