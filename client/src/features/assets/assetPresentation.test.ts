import { describe, expect, it } from 'vitest';

import type { AssetImage, TagWithCount } from '@client/src/types/api';
import { systemFilters, variantLabel } from './assetPresentation';

const image: AssetImage = {
  id: 'image-1',
  title: '竖版图',
  fileName: 'vertical.png',
  thumbnailUrl: '/thumbnail',
  contentUrl: '/content',
  downloadUrl: '/download',
  assetRole: 'derivative',
  width: 1080,
  height: 1920,
  channel: '朋友圈',
  versionNo: 2,
  isCurrent: true,
};

describe('phase 5 asset presentation', () => {
  it('shows the selected variant dimension and channel without exposing scores', () => {
    expect(variantLabel(image)).toBe('延展 · 1080×1920 · 朋友圈');
  });

  it('only exposes stable system tags as optional business filters', () => {
    const tags = [
      tag('concept', '概念', 'image_label', 1),
      tag('system-b', '体系 B', 'system', 2),
      tag('system-a', '体系 A', 'system', 0),
    ];
    expect(systemFilters(tags).map((item) => item.code)).toEqual(['system-a', 'system-b']);
  });
});

function tag(code: string, name: string, nodeType: string, sortOrder: number): TagWithCount {
  return {
    id: code,
    code,
    name,
    color: '#000',
    parentId: null,
    isSecondary: false,
    nodeType,
    assignable: nodeType !== 'system',
    status: 'active',
    sortOrder,
    imageCount: 0,
  };
}
