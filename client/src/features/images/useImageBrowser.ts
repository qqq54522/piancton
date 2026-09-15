import { useCallback, useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { useTags } from '@client/src/features/tags/useTags';
import { useGlobalImageSearch } from './hooks/useGlobalImageSearch';
import { useImageListQuery } from './hooks/useImageListQuery';
import { useChannelFolderCatalog } from './channelFolders';

export function useImageBrowser() {
  const queryClient = useQueryClient();
  const { data: allTags = [] } = useTags();
  const [keyword, setKeyword] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [sortBy, setSortBy] = useState<'createdAt' | 'downloadCount'>('createdAt');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [unfiledOnly, setUnfiledOnly] = useState(false);
  const global = useGlobalImageSearch({ allTags });
  const changeGlobalChannel = global.setSelectedChannel;
  const folderCatalog = useChannelFolderCatalog();
  const list = useImageListQuery(keyword, sortBy, global.searchRefinements.channel, selectedFolderId, unfiledOnly, global.searchRefinements.scene);
  const setSelectedChannel = useCallback((channel: string) => {
    setSelectedFolderId(null);
    setUnfiledOnly(false);
    changeGlobalChannel(channel);
  }, [changeGlobalChannel]);
  useEffect(() => {
    setSelectedFolderId(null);
    setUnfiledOnly(false);
  }, [global.searchRefinements.channel]);
  const refinementOptions = useMemo(() => ({
    ...global.refinementOptions,
    channels: uniqueChannels([
      ...global.refinementOptions.channels,
      ...list.availableChannels,
      ...(folderCatalog.data?.map((item) => item.name) ?? []),
    ]),
  }), [global.refinementOptions, list.availableChannels, folderCatalog.data]);
  const handleUploadSuccess = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['images'] });
  }, [queryClient]);

  return {
    ...global,
    setSelectedChannel,
    ...list,
    folderCatalog: folderCatalog.data ?? [],
    selectedFolderId,
    setSelectedFolderId,
    unfiledOnly,
    setUnfiledOnly,
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
