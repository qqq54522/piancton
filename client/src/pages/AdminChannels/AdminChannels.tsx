import { useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Copy, Plus } from 'lucide-react';
import { toast } from 'sonner';

import * as imageApi from '@client/src/api/image';
import PageHeader from '@client/src/components/PageHeader';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { addChannelIntentEntry, useChannelIntentEntries } from '@client/src/pages/ImageHome/channelIntentCatalog';
import {
  folderPath,
  orderedChannelFolders,
  useChannelFolderCatalog,
} from '@client/src/features/images/channelFolders';
import { ChannelFolderTree, ChannelImagesPane } from './ChannelFoldersSection';

export default function AdminChannels() {
  const queryClient = useQueryClient();
  const catalog = useChannelFolderCatalog();
  const entries = useChannelIntentEntries();
  const [selectedValue, setSelectedValue] = useState(entries[0]?.value ?? '');
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [draftChannel, setDraftChannel] = useState('');
  const [copyOpen, setCopyOpen] = useState(false);
  const [copySourceFolderId, setCopySourceFolderId] = useState<string | null>(null);
  const [copyTarget, setCopyTarget] = useState('');
  const [copyTargetParentId, setCopyTargetParentId] = useState('');
  const [copying, setCopying] = useState(false);
  const channelNames = useMemo(
    () => [...new Set([...entries.map((entry) => entry.value), ...(catalog.data?.map((item) => item.name) ?? [])])],
    [entries, catalog.data],
  );
  const selectedName = channelNames.includes(selectedValue) ? selectedValue : channelNames[0];
  const folders = catalog.data?.find((item) => item.name === selectedName)?.folders ?? [];
  const selectedFolder = folders.find((folder) => folder.id === selectedFolderId);
  const selectedSourceLabel = selectedFolder ? folderPath(selectedFolder, folders) : selectedName;
  const copySourceFolder = folders.find((folder) => folder.id === copySourceFolderId);
  const copySourceLabel = copySourceFolder ? folderPath(copySourceFolder, folders) : selectedName;
  const copyTargets = channelNames.filter((name) => name !== selectedName);
  const targetFolders = catalog.data?.find((item) => item.name === copyTarget)?.folders ?? [];
  const orderedTargetFolders = orderedChannelFolders(targetFolders);

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

  const openCopyTool = (sourceFolderId: string | null = selectedFolderId) => {
    setCopySourceFolderId(sourceFolderId);
    setCopyTarget(copyTargets[0] ?? '');
    setCopyTargetParentId('');
    setCopyOpen(true);
  };

  const copyFolderTree = async () => {
    if (!selectedName || !copyTarget) return;
    setCopying(true);
    try {
      const result = await imageApi.copyChannelFolderTree(
        selectedName,
        copyTarget,
        copySourceFolderId,
        copyTargetParentId || null,
      );
      await queryClient.invalidateQueries({ queryKey: ['channel-folders'] });
      toast.success(
        result.created
          ? `已把 ${result.created} 个分类复制到${copyTarget}${result.skipped ? `，跳过 ${result.skipped} 个同名分类` : ''}`
          : `${copyTarget}已经有相同的分类结构`,
      );
      setCopyOpen(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '复制分类结构失败');
    } finally {
      setCopying(false);
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
          {selectedName && <div className="mb-4 rounded-xl border border-border bg-secondary/35 p-3">
            {!copyOpen ? <>
              <Button type="button" size="sm" variant="outline" className="w-full justify-start"
                disabled={!folders.length || !copyTargets.length} onClick={() => openCopyTool(selectedFolderId)}>
                <Copy className="mr-2 size-4" />复制“{selectedSourceLabel}”的分类结构
              </Button>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">
                {selectedFolder ? '复制当前分类及其全部下级，' : '复制当前渠道的完整分类，'}不会复制、移动或绑定图片。
              </p>
            </> : <div className="space-y-2">
              <p className="text-xs font-semibold">
                把“{copySourceLabel}”复制到
              </p>
              <select aria-label="分类结构目标渠道" value={copyTarget}
                onChange={(event) => { setCopyTarget(event.target.value); setCopyTargetParentId(''); }}
                className="h-9 w-full rounded-lg border border-border bg-white px-2 text-sm">
                {copyTargets.map((name) => <option key={name} value={name}>{name}</option>)}
              </select>
              <select aria-label="目标上级分类" value={copyTargetParentId}
                onChange={(event) => setCopyTargetParentId(event.target.value)}
                className="h-9 w-full rounded-lg border border-border bg-white px-2 text-sm">
                <option value="">放在“{copyTarget}”最外层</option>
                {orderedTargetFolders.map((folder) => (
                  <option key={folder.id} value={folder.id}>放在：{folderPath(folder, targetFolders)}</option>
                ))}
              </select>
              <p className="text-xs leading-5 text-muted-foreground">已有同名目录会保留并跳过，图片不会跟随复制。</p>
              <div className="flex gap-2">
                <Button type="button" size="sm" disabled={copying || !copyTarget} onClick={copyFolderTree}>
                  {copying ? '正在复制...' : '确认复制'}
                </Button>
                <Button type="button" size="sm" variant="ghost" disabled={copying}
                  onClick={() => setCopyOpen(false)}>取消</Button>
              </div>
            </div>}
          </div>}
          <div className="space-y-1">
            {channelNames.map((name) => (
              <div key={name}>
                <button type="button" onClick={() => { setSelectedValue(name); setSelectedFolderId(null); setCopySourceFolderId(null); setCopyOpen(false); }}
                  className={`flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-sm font-semibold transition-colors ${selectedName === name ? 'bg-foreground text-background' : 'text-muted-foreground hover:bg-secondary hover:text-foreground'}`}>
                  <span>{name}</span>
                  <span className="text-xs opacity-70">{catalog.data?.find((item) => item.name === name)?.folders.length ?? 0}</span>
                </button>
                {selectedName === name && <ChannelFolderTree key={name} channel={name} folders={folders}
                  selectedFolderId={selectedFolderId} onSelect={(id) => { setSelectedFolderId(id); setCopyOpen(false); }}
                  onCopy={(id) => { setSelectedFolderId(id); openCopyTool(id); }} />}
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
