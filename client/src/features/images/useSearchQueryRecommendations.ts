import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { fetchSearchQueryRecommendations } from '@client/src/api/image';

const FALLBACK_PLACEHOLDER = '搜索素材，或粘贴图片身份码';

export function useSearchQueryRecommendations(input: string) {
  const [index, setIndex] = useState(0);
  const query = useQuery({
    queryKey: ['images', 'query-recommendations'],
    queryFn: () => fetchSearchQueryRecommendations(8),
    staleTime: 5 * 60_000,
    retry: 1,
  });
  const recommendations = useMemo(
    () => query.data?.queries.filter((item) => item.trim()).slice(0, 8) ?? [],
    [query.data?.queries],
  );

  useEffect(() => {
    setIndex(0);
  }, [recommendations.length]);

  useEffect(() => {
    if (input || recommendations.length < 2) return undefined;
    const timer = window.setInterval(() => {
      setIndex((current) => (current + 1) % recommendations.length);
    }, 3600);
    return () => window.clearInterval(timer);
  }, [input, recommendations.length]);

  return {
    placeholder: recommendations.length > 0
      ? `试试搜：${recommendations[index % recommendations.length]}`
      : FALLBACK_PLACEHOLDER,
    recommendation: recommendations[index % recommendations.length] ?? '',
  };
}
