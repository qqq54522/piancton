import { useQuery } from '@tanstack/react-query';

import { fetchForYouImages } from '@client/src/api/image';

export function useForYouImages(enabled: boolean) {
  return useQuery({
    queryKey: ['images', 'for-you'],
    queryFn: () => fetchForYouImages(48),
    enabled,
    staleTime: 30_000,
  });
}
