import { useQuery } from '@tanstack/react-query';

import * as assetApi from '@client/src/api/asset';

export const businessFacetsKey = ['business-facets'] as const;

export function useBusinessFacets(enabled = true) {
  return useQuery({
    queryKey: businessFacetsKey,
    queryFn: assetApi.fetchBusinessFacets,
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}
