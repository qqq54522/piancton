import { useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { toast } from 'sonner';

import * as imageApi from '@client/src/api/image';
import PageHeader from '@client/src/components/PageHeader';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { addChannelIntentEntry, useChannelIntentEntries } from '@client/src/pages/ImageHome/channelIntentCatalog';
import { useChannelFolderCatalog } from '@client/src/features/images/channelFolders';
import { ChannelFolderTree, ChannelImagesPane } from './ChannelFoldersSection';

export default function AdminChannels() {
  const queryClient = useQueryClient();
  const catalog = useChannelFolderCatalog();
  const entries = useChannelIntentEntries();
  const [selectedValue, setSelectedValue] = useState(entries[0]?.value ?? '');
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [draftChannel, setDraftChannel] = useState('');
  const channelNames = useMemo(
    () => [...new Set([...entries.map((entry) => entry.value), ...(catalog.data?.map((item) => item.name) ?? [])])],
    [entries, catalog.data],
  );
  const selectedName = channelNames.includes(selectedValue) ? selectedValue : channelNames[0];
  const folders = catalog.data?.find((item) => item.name === selectedName)?.folders ?? [];

  const addChannel = async () => {
    const name = draftChannel.trim();
    if (!name) return;
    if (channelNames.includes(name)) {
      setSelectedValue(name);
      setSelectedFolderId(null);
      setDraftChannel('');
      return;
    }
    try {
      await imageApi.createManagedChannel(name);
      addChannelIntentEntry(name);
      await queryClient.invalidateQueries({ queryKey: ['channel-folders'] });
      setDraftChannel('');
      setSelectedValue(name);
      setSelectedFolderId(null);
      toast.success('渠道已创建');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '创建渠道失败');
    }
  };

  return (
    <div className="page-shell flex lg:h-screen lg:flex-col lg:overflow-hidden">
      <PageHeader title="场景与渠道管理" />
      <div className="mt-6 grid gap-5 lg:min-h-0 lg:flex-1 lg:grid-cols-[340px_minmax(0,1fr)]">
        <aside className="surface-card min-w-0 p-3 sm:p-4 lg:min-h-0 lg:overflow-y-auto compact-scrollbar">
          <h2 className="mb-3 px-2 text-base font-semibold">渠道与分类</h2>
          <div className="mb-4 flex gap-2">
            <Input value={draftChannel} onChange={(event) => setDraftChannel(event.target.value)}
              onKeyDown={(event) => { if (event.key === 'Enter') addChannel(); }}
              placeholder="新建渠道" maxLength={24} className="h-9" />
            <Button size="icon" aria-label="新建渠道" onClick={addChannel} disabled={!draftChannel.trim()}>
              <Plus className="size-4" />
            </Button>
          </div>
          <div className="space-y-1">
            {channelNames.map((name) => (
              <div key={name}>
                <button type="button" onClick={() => { setSelectedValue(name); setSelectedFolderId(null); }}
                  className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-sm font-semibold transition-colors ${selectedName === name ? 'bg-foreground text-background' : 'text-muted-foreground hover:bg-secondary hover:text-foreground'}`}>
                  <span>{name}</span>
                  <span className="text-xs opacity-70">{catalog.data?.find((item) => item.name === name)?.folders.length ?? 0}</span>
                </button>
                {selectedName === name && <ChannelFolderTree key={name} channel={name} folders={folders}
                  selectedFolderId={selectedFolderId} onSelect={setSelectedFolderId} />}
              </div>
            ))}
          </div>
        </aside>
        {selectedName ? <ChannelImagesPane key={selectedName} channel={selectedName} folders={folders}
          selectedFolderId={selectedFolderId} /> : (
          <main className="surface-card grid min-h-80 place-items-center text-sm text-muted-foreground">暂无渠道</main>
        )}
      </div>
    </div>
  );
}
