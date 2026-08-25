interface PreviewableImage {
  fileName?: string | null;
  mediaType?: string | null;
  thumbnailUrl?: string | null;
  contentUrl?: string | null;
}

export function isGifImage(image: PreviewableImage): boolean {
  return image.mediaType === 'image/gif' || image.fileName?.toLowerCase().endsWith('.gif') === true;
}

export function previewUrlFor(
  image: PreviewableImage,
  options: { animateGif?: boolean } = {},
): string {
  const animateGif = options.animateGif ?? true;
  if (animateGif && isGifImage(image) && image.contentUrl) return image.contentUrl;
  return image.thumbnailUrl || image.contentUrl || '';
}
