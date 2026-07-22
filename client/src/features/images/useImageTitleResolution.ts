import { useQuery } from '@tanstack/react-query';

import * as imageApi from '@client/src/api/image';

export function useImageTitleResolution(title: string, enabled = true) {
  const normalizedTitle = title.trim();
  return useQuery({
    queryKey: ['image-title-resolution', normalizedTitle],
    queryFn: () => imageApi.resolveImageTitle(normalizedTitle),
    enabled: enabled && Boolean(normalizedTitle),
    staleTime: 5_000,
    retry: false,
  });
}
