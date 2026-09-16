import {
  createContext,
  useContext,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, FolderHeart, Plus } from 'lucide-react';
import { toast } from 'sonner';

import {
  addAssetToBoard,
  createCollectionBoard,
  fetchAssetCollectionSummary,
  fetchAssetMembership,
  likeAsset,
  removeAssetFromBoard,
  unlikeAsset,
} from '@client/src/api/assetCollections';
import { Button } from '@client/src/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@client/src/components/ui/dialog';
import { Input } from '@client/src/components/ui/input';
import { assetCollectionQueryKeys } from '@client/src/features/assets/assetCollectionQueryKeys';
import { useAuth } from '@client/src/lib/auth';
import type { AssetSaveContext } from '@client/src/types/api';

export interface AssetCollectionTarget extends AssetSaveContext {
  assetGroupId: string;
  imageId: string;
  title: string;
}

interface AssetCollectionsContextValue {
  enabled: boolean;
  isLiked: (assetGroupId?: string | null) => boolean;
  toggleLike: (target: AssetCollectionTarget) => void;
  openBoardPicker: (target: AssetCollectionTarget) => void;
}

const EMPTY_VALUE: AssetCollectionsContextValue = {
  enabled: false,
  isLiked: () => false,
  toggleLike: () => undefined,
  openBoardPicker: () => undefined,
};

const AssetCollectionsContext = createContext<AssetCollectionsContextValue>(EMPTY_VALUE);

export function AssetCollectionsProvider({ children }: PropsWithChildren) {
  const { user } = useAuth();
  const enabled = user?.role === 'business';
  const queryClient = useQueryClient();
  const [pickerTarget, setPickerTarget] = useState<AssetCollectionTarget | null>(null);
  const [newBoardName, setNewBoardName] = useState('');
  const [selectedBoardId, setSelectedBoardId] = useState<string | null>(null);
  const summaryQuery = useQuery({
    queryKey: assetCollectionQueryKeys.summary,
    queryFn: fetchAssetCollectionSummary,
    enabled,
  });
  const membershipQuery = useQuery({
    queryKey: assetCollectionQueryKeys.membership(pickerTarget?.assetGroupId),
    queryFn: () => fetchAssetMembership(pickerTarget!.assetGroupId),
    enabled: enabled && Boolean(pickerTarget),
  });
  const invalidate = async (assetGroupId?: string, boardId?: string) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: assetCollectionQueryKeys.summary }),
      queryClient.invalidateQueries({ queryKey: assetCollectionQueryKeys.boards }),
      queryClient.invalidateQueries({
        queryKey: assetCollectionQueryKeys.membership(assetGroupId),
      }),
      queryClient.invalidateQueries({ queryKey: assetCollectionQueryKeys.likes }),
      ...(boardId
        ? [queryClient.invalidateQueries({
          queryKey: assetCollectionQueryKeys.boardItems(boardId),
        })]
        : []),
    ]);
  };
  const likeMutation = useMutation({
    mutationFn: async (target: AssetCollectionTarget) => {
      const liked = summaryQuery.data
        ? summaryQuery.data.likedAssetGroupIds.includes(target.assetGroupId)
        : (await fetchAssetMembership(target.assetGroupId)).liked;
      const context = saveContext(target);
      return liked
        ? unlikeAsset(target.assetGroupId, context)
        : likeAsset(target.assetGroupId, context);
    },
    onSuccess: async (membership, target) => {
      await invalidate(target.assetGroupId);
      toast.success(membership.liked ? '已加入我的喜欢' : '已从我的喜欢移除');
    },
    onError: () => toast.error('喜欢状态保存失败，请稍后再试'),
  });
  const saveToBoardMutation = useMutation({
    mutationFn: async ({
      boardId,
      remove,
      target,
    }: {
      boardId: string;
      remove: boolean;
      target: AssetCollectionTarget;
    }) => {
      const context = saveContext(target);
      return remove
        ? removeAssetFromBoard(boardId, target.assetGroupId, context)
        : addAssetToBoard(boardId, target.assetGroupId, context);
    },
    onSuccess: async (_membership, { boardId, remove, target }) => {
      const boardName = summaryQuery.data?.boards.find((board) => board.id === boardId)?.name;
      await invalidate(target.assetGroupId, boardId);
      setPickerTarget(null);
      setSelectedBoardId(null);
      setNewBoardName('');
      if (remove) {
        toast.success(boardName ? `已从「${boardName}」移除` : '已从画板移除');
      } else {
        toast.success(boardName ? `已收藏到「${boardName}」` : '已收藏到画板');
      }
    },
    onError: () => toast.error('画板保存失败，请稍后再试'),
  });
  const createMutation = useMutation({
    mutationFn: async () => {
      if (!newBoardName.trim()) throw new Error('missing board name');
      return createCollectionBoard(newBoardName.trim());
    },
    onSuccess: async (board) => {
      setNewBoardName('');
      setSelectedBoardId(board.id);
      await invalidate(pickerTarget?.assetGroupId);
      toast.success(`画板「${board.name}」已创建，请点击确定收藏`);
    },
    onError: () => toast.error('新建画板失败，请检查名称是否重复'),
  });
  const likedIds = useMemo(
    () => new Set(summaryQuery.data?.likedAssetGroupIds ?? []),
    [summaryQuery.data?.likedAssetGroupIds],
  );
  const value = useMemo<AssetCollectionsContextValue>(() => ({
    enabled,
    isLiked: (assetGroupId) => Boolean(assetGroupId && likedIds.has(assetGroupId)),
    toggleLike: (target) => likeMutation.mutate(target),
    openBoardPicker: (target) => {
      setPickerTarget(target);
      setSelectedBoardId(null);
      setNewBoardName('');
    },
  }), [enabled, likedIds, likeMutation]);

  return (
    <AssetCollectionsContext.Provider value={value}>
      {children}
      <Dialog
        open={Boolean(pickerTarget)}
        onOpenChange={(open) => {
          if (!open) {
            setPickerTarget(null);
            setNewBoardName('');
            setSelectedBoardId(null);
          }
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>收藏到画板</DialogTitle>
            <DialogDescription className="line-clamp-1">
              {pickerTarget?.title}
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-xl border border-border bg-secondary/25 p-3">
            <label htmlFor="new-collection-board" className="mb-2 block text-sm font-medium">
              新建画板
            </label>
            <div className="flex gap-2">
              <Input
                id="new-collection-board"
                aria-label="新画板名称"
                value={newBoardName}
                maxLength={80}
                placeholder="例如：秋季家长会"
                onChange={(event) => setNewBoardName(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && newBoardName.trim()) createMutation.mutate();
                }}
              />
              <Button
                type="button"
                variant="outline"
                className="shrink-0 bg-white"
                disabled={!newBoardName.trim() || createMutation.isPending}
                onClick={() => createMutation.mutate()}
              >
                <Plus className="size-4" />新建
              </Button>
            </div>
          </div>
          <p className="text-sm font-medium">选择一个画板</p>
          <div className="max-h-64 space-y-2 overflow-y-auto py-1">
            {summaryQuery.data?.boards.length ? summaryQuery.data.boards.map((board) => {
              const selected = selectedBoardId === board.id;
              const alreadySaved = membershipQuery.data?.boardIds.includes(board.id) ?? false;
              return (
                <button
                  key={board.id}
                  type="button"
                  aria-pressed={selected}
                  className={`flex w-full items-center justify-between rounded-xl border px-3 py-3 text-left transition ${selected ? 'border-foreground bg-foreground text-background' : 'border-border bg-white hover:bg-secondary/60'}`}
                  disabled={saveToBoardMutation.isPending}
                  onClick={() => setSelectedBoardId(board.id)}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <FolderHeart className="size-4 shrink-0" />
                    <span className="truncate text-sm font-medium">{board.name}</span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2 text-xs opacity-75">
                    {alreadySaved ? '已收藏' : `${board.itemCount} 张`}
                    {selected && <Check className="size-4" />}
                  </span>
                </button>
              );
            }) : (
              <div className="rounded-xl border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
                还没有画板，请先在上方新建一个
              </div>
            )}
          </div>
          <DialogFooter className="border-t border-border pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => setPickerTarget(null)}
            >
              取消
            </Button>
            <Button
              type="button"
              disabled={!selectedBoardId || saveToBoardMutation.isPending}
              onClick={() => {
                if (selectedBoardId && pickerTarget) {
                  saveToBoardMutation.mutate({
                    boardId: selectedBoardId,
                    remove: membershipQuery.data?.boardIds.includes(selectedBoardId) ?? false,
                    target: pickerTarget,
                  });
                }
              }}
            >
              {saveToBoardMutation.isPending
                ? '正在保存...'
                : selectedBoardId && membershipQuery.data?.boardIds.includes(selectedBoardId)
                  ? '从该画板移除'
                  : '确定收藏'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AssetCollectionsContext.Provider>
  );
}

export function useAssetCollections() {
  return useContext(AssetCollectionsContext);
}

function saveContext(target: AssetCollectionTarget): AssetSaveContext {
  return {
    imageId: target.imageId,
    source: target.source || 'library_browse',
    position: target.position,
    searchLogId: target.searchLogId,
    keyword: target.keyword,
  };
}
