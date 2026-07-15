import { useCallback, useState } from 'react';
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
  const list = useImageListQuery(keyword, sortBy);
  const handleUploadSuccess = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['images'] });
  }, [queryClient]);

  return {
    ...global,
    ...list,
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
