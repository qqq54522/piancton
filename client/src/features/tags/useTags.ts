import { useQuery } from '@tanstack/react-query';

import { fetchTags } from '@client/src/api/image';


export const tagQueryKey = ['tags'] as const;

export function useTags() {
  return useQuery({ queryKey: tagQueryKey, queryFn: fetchTags });
}
