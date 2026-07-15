import { useQuery } from '@tanstack/react-query';

import * as assetApi from '@client/src/api/asset';

export const businessConceptsKey = ['business-concepts'] as const;

export function useBusinessConcepts(enabled = true) {
  return useQuery({
    queryKey: businessConceptsKey,
    queryFn: assetApi.fetchBusinessConcepts,
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}
