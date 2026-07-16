import type { ImageSemanticProfile } from '@client/src/types/api';

export interface VisibleSemanticProfileGroup {
  key: 'visualFacts' | 'scenes' | 'assetSearchPhrases';
  title: '画面事实' | '场景' | '素材独有搜索表达';
  items: string[];
}

export function visibleSemanticProfileGroups(
  profile: ImageSemanticProfile,
): VisibleSemanticProfileGroup[] {
  const groups: VisibleSemanticProfileGroup[] = [
    { key: 'visualFacts', title: '画面事实', items: profile.visualFacts ?? [] },
    { key: 'scenes', title: '场景', items: profile.scenes ?? [] },
    {
      key: 'assetSearchPhrases',
      title: '素材独有搜索表达',
      items: profile.assetSearchPhrases ?? [],
    },
  ];

  return groups.filter((group) => group.items.length > 0);
}
