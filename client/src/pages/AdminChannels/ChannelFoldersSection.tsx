import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ChevronDown, ChevronRight, Copy, FolderClosed, Pencil, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import * as imageApi from '@client/src/api/image';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@client/src/components/ui/alert-dialog';
import { folderPath, orderedChannelFolders, type ChannelFolder } from '@client/src/features/images/channelFolders';

type FolderAction = (action: () => Promise<unknown>, message: string) => Promise<boolean>;
type OrganizeScope = 'current' | 'unfiled' | 'all';

function folderSubtreeSize(folderId: string, folders: ChannelFolder[]): number {
  const childrenByParent = new Map<string, string[]>();
  for (const folder of folders) {
    if (!folder.parentId) continue;
    childrenByParent.set(folder.parentId, [...(childrenByParent.get(folder.parentId) ?? []), folder.id]);
  }
  const included = new Set<string>();
  const pending = [folderId];
  while (pending.length) {
    const current = pending.pop()!;
    if (included.has(current)) continue;
    included.add(current);
    pending.push(...(childrenByParent.get(current) ?? []));
  }
  return included.size;
}

function useFolderActions(channel: string) {
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const run: FolderAction = async (action, message) => {
    setBusy(true);
    try {
      await action();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['channel-folders'] }),
        queryClient.invalidateQueries({ queryKey: ['channel-folder-images'] }),
        queryClient.invalidateQueries({ queryKey: ['images'] }),
      ]);
      toast.success(message);
      return true;
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '操作失败');
      return false;
    } finally {
      setBusy(false);
    }
  };
  const create = (name: string, parentId: string | null) => run(
    () => imageApi.createChannelFolder({ channel, name: name.trim(), parentId }), '分类已创建',
  );
  return { busy, run, create };
}

export function ChannelFolderTree({ channel, folders, selectedFolderId, onSelect, onCopy }: {
  channel: string;
  folders: ChannelFolder[];
  selectedFolderId: string | null;
  onSelect: (id: string | null) => void;
  onCopy?: (id: string) => void;
}) {
  const { busy, run, create } = useFolderActions(channel);
  const [rootName, setRootName] = useState('');
  const [addingRoot, setAddingRoot] = useState(false);
  const ordered = useMemo(() => orderedChannelFolders(folders), [folders]);
  const addRoot = async () => {
    if (!rootName.trim()) return;
    if (await create(rootName, null)) { setRootName(''); setAddingRoot(false); }
  };

  return <div className="ml-3 mt-2 border-l border-border pl-3">
    <div className="mb-2 flex items-center justify-between gap-2 px-1">
      <span className="text-xs font-semibold text-muted-foreground">分类</span>
      <button type="button" aria-label={`在${channel}下新增分类`} onClick={() => setAddingRoot((value) => !value)}
        className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium hover:bg-secondary">
        <Plus className="size-3.5" />新增
      </button>
    </div>
    {addingRoot && <div className="mb-2 flex gap-1">
      <Input autoFocus value={rootName} onChange={(event) => setRootName(event.target.value)}
        onKeyDown={(event) => { if (event.key === 'Enter' && !busy) addRoot(); if (event.key === 'Escape') setAddingRoot(false); }}
        placeholder="例如：北京" maxLength={80} className="h-9 min-w-0 flex-1" />
      <Button size="sm" disabled={busy || !rootName.trim()} onClick={addRoot}>创建</Button>
    </div>}
    <div className="space-y-1">
      {ordered.filter((folder) => !folder.parentId).map((folder) => <FolderBranch key={folder.id}
        folder={folder} folders={folders} selectedFolderId={selectedFolderId} onSelect={onSelect}
        onCopy={onCopy} busy={busy} run={run} create={create} />)}
      {!folders.length && <p className="rounded-lg bg-secondary/50 px-3 py-3 text-xs text-muted-foreground">还没有分类，点“新增”开始。</p>}
    </div>
  </div>;
}

function FolderBranch({ folder, folders, selectedFolderId, onSelect, onCopy, busy, run, create }: {
  folder: ChannelFolder;
  folders: ChannelFolder[];
  selectedFolderId: string | null;
  onSelect: (id: string | null) => void;
  onCopy?: (id: string) => void;
  busy: boolean;
  run: FolderAction;
  create: (name: string, parentId: string | null) => Promise<boolean>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [childName, setChildName] = useState('');
  const [name, setName] = useState(folder.name);
  useEffect(() => setName(folder.name), [folder.name]);
  const children = folders.filter((item) => item.parentId === folder.id).sort((a, b) => a.name.localeCompare(b.name, 'zh'));
  const subtreeSize = folderSubtreeSize(folder.id, folders);
  const descendantCount = subtreeSize - 1;
  const active = selectedFolderId === folder.id;
  const addChild = async () => {
    if (!childName.trim()) return;
    if (await create(childName, folder.id)) { setChildName(''); setAdding(false); setExpanded(true); }
  };
  const rename = async () => {
    if (await run(() => imageApi.renameChannelFolder(folder.id, name.trim()), '分类已改名')) setEditing(false);
  };
  const remove = async () => {
    const message = descendantCount
      ? `已删除“${folder.name}”及其 ${descendantCount} 个下级分类，相关图片已移回未归类`
      : `已删除“${folder.name}”，相关图片已移回未归类`;
    if (await run(() => imageApi.deleteChannelFolder(folder.id), message)) {
      setDeleteOpen(false);
      onSelect(null);
    }
  };

  return <div>
    <div className={`group flex items-center rounded-xl transition-colors ${active ? 'bg-foreground text-background' : 'bg-secondary/60 hover:bg-secondary'}`}>
      <button type="button" onClick={() => { onSelect(folder.id); if (children.length) setExpanded(true); }}
        className="flex min-w-0 flex-1 items-center gap-2 px-3 py-2.5 text-left text-sm font-medium">
        <FolderClosed className="size-4 shrink-0 opacity-70" />
        <span className="min-w-0 flex-1 truncate">{folder.name}</span>
      </button>
      {children.length > 0 && <button type="button" aria-label={`${expanded ? '收起' : '展开'}${folder.name}的下级分类`}
        aria-expanded={expanded} onClick={() => setExpanded((value) => !value)} className="mr-2 rounded-lg p-1.5 hover:bg-black/10">
        {expanded ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
      </button>}
      <button type="button" disabled={busy} aria-label={`删除${folder.name}及其下级分类`}
        onClick={() => setDeleteOpen(true)}
        className="mr-1 rounded-lg p-1.5 text-destructive hover:bg-black/10 disabled:opacity-50">
        <Trash2 className="size-4" />
      </button>
    </div>
    {active && <div className="flex flex-wrap gap-1 px-1 py-1">
      <button type="button" onClick={() => { setAdding((value) => !value); setExpanded(true); }}
        className="rounded-lg px-2 py-1 text-xs hover:bg-secondary"><Plus className="mr-1 inline size-3" />新增下级</button>
      <button type="button" onClick={() => setEditing((value) => !value)}
        className="rounded-lg px-2 py-1 text-xs hover:bg-secondary"><Pencil className="mr-1 inline size-3" />改名</button>
      {onCopy && <button type="button" onClick={() => onCopy(folder.id)}
        className="rounded-lg px-2 py-1 text-xs hover:bg-secondary"><Copy className="mr-1 inline size-3" />复制到</button>}
    </div>}
    {adding && <div className="mb-2 flex gap-1 pl-2">
      <Input autoFocus value={childName} onChange={(event) => setChildName(event.target.value)}
        onKeyDown={(event) => { if (event.key === 'Enter' && !busy) addChild(); if (event.key === 'Escape') setAdding(false); }}
        placeholder={`在${folder.name}下新增`} maxLength={80} className="h-9 min-w-0 flex-1" />
      <Button size="sm" disabled={busy || !childName.trim()} onClick={addChild}>创建</Button>
    </div>}
    {editing && <div className="mb-2 flex gap-1 pl-2">
      <Input value={name} onChange={(event) => setName(event.target.value)} maxLength={80}
        onKeyDown={(event) => { if (event.key === 'Enter' && !busy && name.trim() !== folder.name) rename(); if (event.key === 'Escape') setEditing(false); }}
        aria-label={`修改${folder.name}的名称`} className="h-9 min-w-0 flex-1" />
      <Button size="sm" disabled={busy || !name.trim() || name === folder.name} onClick={rename}>保存</Button>
    </div>}
    {children.length > 0 && expanded && <div className="ml-4 mt-1 space-y-1 border-l border-border pl-2">
      {children.map((child) => <FolderBranch key={child.id} folder={child} folders={folders}
        selectedFolderId={selectedFolderId} onSelect={onSelect} onCopy={onCopy}
        busy={busy} run={run} create={create} />)}
    </div>}
    <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>删除“{folder.name}”及其下级分类？</AlertDialogTitle>
          <AlertDialogDescription>
            {descendantCount
              ? `将同时删除 ${descendantCount} 个下级分类。分类中的图片不会被删除，会回到当前渠道的未归类。`
              : '分类中的图片不会被删除，会回到当前渠道的未归类。'}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={busy}>取消</AlertDialogCancel>
          <Button type="button" variant="destructive" disabled={busy} onClick={remove}>
            {busy ? '正在删除...' : '确认删除'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </div>;
}

export function ChannelImagesPane({ channel, folders, selectedFolderId }: {
  channel: string;
  folders: ChannelFolder[];
  selectedFolderId: string | null;
}) {
  const queryClient = useQueryClient();
  const [organizing, setOrganizing] = useState(false);
  const [organizeScope, setOrganizeScope] = useState<OrganizeScope>(
    selectedFolderId ? 'current' : 'unfiled',
  );
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [pageCursor, setPageCursor] = useState<string | undefined>();
  const [previousCursors, setPreviousCursors] = useState<(string | undefined)[]>([]);
  const [busy, setBusy] = useState(false);
  const selectedFolder = folders.find((folder) => folder.id === selectedFolderId);
  const selectedPath = selectedFolder ? folderPath(selectedFolder, folders) : channel;
  const ordered = useMemo(() => orderedChannelFolders(folders), [folders]);
  const [targetFolderId, setTargetFolderId] = useState(selectedFolderId ?? '');

  useEffect(() => {
    setPageCursor(undefined);
    setPreviousCursors([]);
    setSelectedIds([]);
    setTargetFolderId(selectedFolderId ?? '');
    setOrganizeScope(selectedFolderId ? 'current' : 'unfiled');
    setOrganizing(false);
  }, [selectedFolderId]);
  const images = useQuery({
    queryKey: [
      'channel-folder-images',
      channel,
      organizing,
      organizeScope,
      selectedFolderId,
      pageCursor,
    ],
    queryFn: () => imageApi.fetchImages({ channel,
      ...(organizing
        ? organizeScope === 'current' && selectedFolderId
          ? { folderId: selectedFolderId }
          : organizeScope === 'unfiled'
            ? { unfiled: true }
            : {}
        : selectedFolderId
          ? { folderId: selectedFolderId }
          : {}),
      cursor: pageCursor, limit: 50 }),
  });
  const pageImages = images.data?.items ?? [];
  const pageIds = pageImages.map((image) => image.id);
  const changeMode = (value: boolean) => {
    setOrganizing(value);
    if (value) setOrganizeScope(selectedFolderId ? 'current' : 'unfiled');
    setPageCursor(undefined); setPreviousCursors([]); setSelectedIds([]);
  };
  const assign = async () => {
    if (!selectedIds.length) return;
    setBusy(true);
    try {
      await imageApi.assignChannelFolder(channel, selectedIds, targetFolderId || null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['channel-folder-images'] }),
        queryClient.invalidateQueries({ queryKey: ['images'] }),
      ]);
      toast.success(`${selectedIds.length} 张图片的分类已调整`);
      setSelectedIds([]);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '归类失败');
    } finally { setBusy(false); }
  };

  return <main className="surface-card min-w-0 p-5 sm:p-6 lg:flex lg:min-h-0 lg:flex-col lg:overflow-hidden">
    <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-border pb-5">
      <div>
        <p className="mb-1 text-xs text-muted-foreground">{organizing ? '调整图片分类' : '当前分类'}</p>
        <h2 className="text-xl font-semibold tracking-tight">
          {organizing && organizeScope === 'current' ? selectedPath : organizing ? channel : selectedPath}
        </h2>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">当前页 {pageImages.length} 张图片</span>
        <Button size="sm" variant={organizing ? 'default' : 'outline'} onClick={() => changeMode(!organizing)}>
          {organizing ? '完成调整' : selectedFolderId ? '调整当前分类' : '整理渠道图片'}
        </Button>
      </div>
    </div>
    <div className="min-h-0 flex-1 overflow-y-auto compact-scrollbar">
    {organizing && <div className="mt-5 rounded-xl border border-border bg-secondary/30 p-3">
      <div className="flex flex-wrap items-center gap-3">
        <select aria-label="要调整的图片范围" value={organizeScope} onChange={(event) => {
          setOrganizeScope(event.target.value as OrganizeScope);
          setPageCursor(undefined); setPreviousCursors([]); setSelectedIds([]);
        }} className="h-9 rounded-lg border border-border bg-white px-2 text-sm">
          {selectedFolderId && <option value="current">当前分类：{selectedPath}</option>}
          <option value="unfiled">未归类图片</option>
          <option value="all">{channel}全部图片</option>
        </select>
        <select aria-label="图片要归入的分类" value={targetFolderId} onChange={(event) => setTargetFolderId(event.target.value)}
          className="h-9 min-w-44 flex-1 rounded-lg border border-border bg-white px-2 text-sm">
          <option value="">移回未归类</option>
          {ordered.map((folder) => <option key={folder.id} value={folder.id}>{folderPath(folder, folders)}</option>)}
        </select>
        <Button size="sm" disabled={busy || !selectedIds.length} onClick={assign}>归类选中的 {selectedIds.length} 张</Button>
        <Button size="sm" variant="outline" disabled={!pageIds.length} onClick={() => setSelectedIds((current) =>
          pageIds.every((id) => current.includes(id)) ? [] : pageIds)}>当前页全选</Button>
      </div>
    </div>}
    {images.isLoading && <p className="py-14 text-center text-sm text-muted-foreground">正在加载图片...</p>}
    {images.isError && <p className="py-14 text-center text-sm text-destructive">图片加载失败，请稍后重试。</p>}
    {!images.isLoading && !images.isError && !pageImages.length && <p className="py-14 text-center text-sm text-muted-foreground">
      {organizing ? '当前范围没有图片' : '这个分类还没有图片，可在“整理渠道图片”中归入。'}
    </p>}
    <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
      {pageImages.map((image) => organizing ? <label key={image.id}
        className={`cursor-pointer overflow-hidden rounded-xl border ${selectedIds.includes(image.id) ? 'border-foreground ring-2 ring-foreground/20' : 'border-border'}`}>
        <img src={image.thumbnailUrl} alt="" className="aspect-[4/3] w-full bg-secondary object-cover" />
        <span className="flex items-center gap-2 p-3 text-sm"><input type="checkbox" checked={selectedIds.includes(image.id)}
          onChange={() => setSelectedIds((current) => current.includes(image.id)
            ? current.filter((id) => id !== image.id) : [...current, image.id])} />
          <span className="min-w-0 truncate">{image.title}</span></span>
      </label> : <Link key={image.id} to={`/image/${image.id}`}
        className="group overflow-hidden rounded-xl border border-border transition-shadow hover:shadow-md">
        <img src={image.thumbnailUrl} alt="" className="aspect-[4/3] w-full bg-secondary object-cover" />
        <span className="block truncate p-3 text-sm font-medium group-hover:underline">{image.title}</span>
      </Link>)}
    </div>
    <div className="mt-5 flex gap-2">
      <Button size="sm" variant="outline" disabled={!previousCursors.length} onClick={() => {
        setPageCursor(previousCursors.at(-1)); setPreviousCursors((items) => items.slice(0, -1)); setSelectedIds([]);
      }}>上一页</Button>
      <Button size="sm" variant="outline" disabled={!images.data?.hasMore || !images.data.nextCursor} onClick={() => {
        setPreviousCursors((items) => [...items, pageCursor]); setPageCursor(images.data!.nextCursor!); setSelectedIds([]);
      }}>下一页</Button>
    </div>
    </div>
  </main>;
}
