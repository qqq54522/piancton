import { useQuery } from '@tanstack/react-query';

import { fetchProviderStatus } from '@client/src/api/image';


export function useProviderStatus(enabled: boolean) {
  return useQuery({
    queryKey: ['ai-provider'],
    queryFn: fetchProviderStatus,
    enabled,
    staleTime: 5 * 60_000,
  });
}
