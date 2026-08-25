import { describe, expect, it } from 'vitest';

import { isGifImage, previewUrlFor } from './imagePreview';

describe('image preview URL selection', () => {
  it('uses original content for GIF previews so animation is preserved', () => {
    const gif = {
      fileName: 'banner.gif',
      mediaType: 'image/gif',
      thumbnailUrl: '/thumbnail',
      contentUrl: '/content',
    };

    expect(isGifImage(gif)).toBe(true);
    expect(previewUrlFor(gif)).toBe('/content');
  });

  it('keeps static image previews on thumbnails', () => {
    expect(previewUrlFor({
      fileName: 'poster.png',
      mediaType: 'image/png',
      thumbnailUrl: '/thumbnail',
      contentUrl: '/content',
    })).toBe('/thumbnail');
  });

  it('can pause GIF list previews by using the thumbnail', () => {
    expect(previewUrlFor({
      fileName: 'banner.gif',
      mediaType: 'image/gif',
      thumbnailUrl: '/thumbnail',
      contentUrl: '/content',
    }, { animateGif: false })).toBe('/thumbnail');
  });
});
