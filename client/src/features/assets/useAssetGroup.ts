import { useQuery } from '@tanstack/react-query';

import * as assetApi from '@client/src/api/asset';

export const assetGroupKey = (groupId: string) => ['asset-group', groupId] as const;

export function useAssetGroup(groupId?: string | null) {
  return useQuery({
    queryKey: assetGroupKey(groupId ?? ''),
    queryFn: () => assetApi.fetchAssetGroup(groupId!),
    enabled: Boolean(groupId),
  });
}
