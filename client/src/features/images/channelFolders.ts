import { useQuery } from '@tanstack/react-query';
import * as imageApi from '@client/src/api/image';

export interface ChannelFolder {
  id: string;
  name: string;
  parentId: string | null;
}

export interface ManagedChannel {
  name: string;
  folders: ChannelFolder[];
}

export function useChannelFolderCatalog(enabled = true) {
  return useQuery({
    queryKey: ['channel-folders'],
    queryFn: imageApi.fetchChannelFolderCatalog,
    enabled,
    staleTime: 30_000,
  });
}

export function folderPath(folder: ChannelFolder, folders: ChannelFolder[]): string {
  const byId = new Map(folders.map((item) => [item.id, item]));
  const names = [folder.name];
  let current = folder;
  while (current.parentId && byId.has(current.parentId)) {
    current = byId.get(current.parentId)!;
    names.unshift(current.name);
  }
  return names.join(' / ');
}

export function orderedChannelFolders(folders: ChannelFolder[]): ChannelFolder[] {
  const children = new Map<string | null, ChannelFolder[]>();
  for (const folder of folders) children.set(folder.parentId, [...(children.get(folder.parentId) ?? []), folder]);
  const output: ChannelFolder[] = [];
  const walk = (parentId: string | null) => {
    for (const folder of (children.get(parentId) ?? []).sort((a, b) => a.name.localeCompare(b.name, 'zh'))) {
      output.push(folder);
      walk(folder.id);
    }
  };
  walk(null);
  return output;
}
