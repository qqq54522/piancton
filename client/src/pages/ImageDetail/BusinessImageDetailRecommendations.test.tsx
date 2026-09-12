// @vitest-environment jsdom

import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

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
      purpose: 'personalized',
      title: '为你推荐',
      description: '由火山推荐持续调整。',
      source: 'ai_search',
      images: [image('personalized', '个性化素材')],
    },
  ],
} satisfies ImageDetail;

describe('BusinessImageDetailRecommendations', () => {
  it('keeps recommendation purposes visibly separate', () => {
    render(
      <MemoryRouter>
        <BusinessImageDetailRecommendations detail={detail} />
        <BusinessImageDetailSideRecommendations detail={detail} />
      </MemoryRouter>,
    );

    expect(screen.getByText('同卖点可替换')).toBeTruthy();
    expect(screen.getByText('同卖点素材')).toBeTruthy();
    expect(screen.getByText('为你推荐')).toBeTruthy();
    expect(screen.getByText('个性化素材')).toBeTruthy();
  });
});
