import type { AssetImage, TagWithCount } from '@client/src/types/api';

export function variantLabel(variant: AssetImage): string {
  const size = variant.width && variant.height
    ? `${variant.width}×${variant.height}`
    : '尺寸待识别';
  const channel = variant.channel ? ` · ${variant.channel}` : '';
  const role = variant.assetRole === 'primary' ? '主图' : '延展';
  return `${role} · ${size}${channel}`;
}

export function systemFilters(tags: TagWithCount[]): TagWithCount[] {
  return tags
    .filter((tag) => tag.nodeType === 'system' && Boolean(tag.code))
    .sort((a, b) => a.sortOrder - b.sortOrder);
}
