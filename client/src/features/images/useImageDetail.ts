import { useQuery } from '@tanstack/react-query';

import { fetchImageDetail } from '@client/src/api/image';
import type { ImageDetail } from '@client/src/types/api';


export function imageDetailQueryKey(id: string) {
  return ['image-detail', id] as const;
}

export function useImageDetail(id?: string) {
  return useQuery({
    queryKey: imageDetailQueryKey(id ?? ''),
    queryFn: () => fetchImageDetail(id!),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const detail = query.state.data as ImageDetail | undefined;
      const latest = detail?.analysisRuns?.[0];
      return latest?.status === 'queued' || latest?.status === 'running' ? 2000 : false;
    },
  });
}
