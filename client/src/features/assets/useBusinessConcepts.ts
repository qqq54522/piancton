import { useQuery } from '@tanstack/react-query';

import * as assetApi from '@client/src/api/asset';

export function useBusinessConcepts(enabled = true) {
  return useQuery({
    queryKey: ['business-concepts'],
    queryFn: assetApi.fetchBusinessConcepts,
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}
