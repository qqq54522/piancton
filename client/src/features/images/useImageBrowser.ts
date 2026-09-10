import { useCallback, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { useTags } from '@client/src/features/tags/useTags';
import { useGlobalImageSearch } from './hooks/useGlobalImageSearch';
import { useImageListQuery } from './hooks/useImageListQuery';

export function useImageBrowser() {
  const queryClient = useQueryClient();
  const { data: allTags = [] } = useTags();
  const [keyword, setKeyword] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [sortBy, setSortBy] = useState<'createdAt' | 'downloadCount'>('createdAt');
  const [uploadOpen, setUploadOpen] = useState(false);
  const global = useGlobalImageSearch({ allTags });
  const list = useImageListQuery(keyword, sortBy, global.searchRefinements.channel);
  const refinementOptions = useMemo(() => ({
    ...global.refinementOptions,
    channels: uniqueChannels([
      ...global.refinementOptions.channels,
      ...list.availableChannels,
    ]),
  }), [global.refinementOptions, list.availableChannels]);
  const handleUploadSuccess = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['images'] });
  }, [queryClient]);

  return {
    ...global,
    ...list,
    refinementOptions,
    handleUploadSuccess,
    keyword,
    searchInput,
    setKeyword,
    setSearchInput,
    setSortBy,
    setUploadOpen,
    sortBy,
    uploadOpen,
  };
}

function uniqueChannels(values: string[]) {
  const seen = new Set<string>();
  const result: string[] = [];
  values.forEach((value) => {
    const channel = value.trim();
    if (!channel || seen.has(channel)) return;
    seen.add(channel);
    result.push(channel);
  });
  return result;
}
