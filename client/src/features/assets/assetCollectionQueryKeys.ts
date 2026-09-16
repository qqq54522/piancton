export const assetCollectionQueryKeys = {
  all: ['asset-collections'] as const,
  summary: ['asset-collections', 'summary'] as const,
  boards: ['asset-collections', 'boards'] as const,
  likes: ['asset-collections', 'likes'] as const,
  membership: (assetGroupId?: string) => (
    ['asset-collections', 'membership', assetGroupId] as const
  ),
  boardItems: (boardId: string) => (
    ['asset-collections', 'board-items', boardId] as const
  ),
};
