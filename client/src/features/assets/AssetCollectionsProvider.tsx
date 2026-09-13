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
  DialogHeader,
  DialogTitle,
} from '@client/src/components/ui/dialog';
import { Input } from '@client/src/components/ui/input';
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
  const summaryQuery = useQuery({
    queryKey: ['asset-collections', 'summary'],
    queryFn: fetchAssetCollectionSummary,
    enabled,
  });
  const membershipQuery = useQuery({
    queryKey: ['asset-collections', 'membership', pickerTarget?.assetGroupId],
    queryFn: () => fetchAssetMembership(pickerTarget!.assetGroupId),
    enabled: enabled && Boolean(pickerTarget),
  });
  const invalidate = async (assetGroupId?: string, boardId?: string) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['asset-collections', 'summary'] }),
      queryClient.invalidateQueries({
        queryKey: ['asset-collections', 'membership', assetGroupId],
      }),
      queryClient.invalidateQueries({ queryKey: ['asset-collections', 'likes'] }),
      ...(boardId
        ? [queryClient.invalidateQueries({
          queryKey: ['asset-collections', 'board-items', boardId],
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
  const boardMutation = useMutation({
    mutationFn: async ({ boardId, selected }: { boardId: string; selected: boolean }) => {
      if (!pickerTarget) throw new Error('missing target');
      const context = saveContext(pickerTarget);
      return selected
        ? removeAssetFromBoard(boardId, pickerTarget.assetGroupId, context)
        : addAssetToBoard(boardId, pickerTarget.assetGroupId, context);
    },
    onSuccess: async (_membership, variables) => {
      if (!pickerTarget) return;
      await invalidate(pickerTarget.assetGroupId, variables.boardId);
    },
    onError: () => toast.error('画板保存失败，请稍后再试'),
  });
  const createMutation = useMutation({
    mutationFn: async () => {
      if (!pickerTarget) throw new Error('missing target');
      const board = await createCollectionBoard(newBoardName.trim());
      await addAssetToBoard(board.id, pickerTarget.assetGroupId, saveContext(pickerTarget));
      return board;
    },
    onSuccess: async (board) => {
      if (!pickerTarget) return;
      setNewBoardName('');
      await invalidate(pickerTarget.assetGroupId, board.id);
      toast.success(`已收藏到「${board.name}」`);
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
    openBoardPicker: setPickerTarget,
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
          <div className="max-h-64 space-y-2 overflow-y-auto py-1">
            {summaryQuery.data?.boards.length ? summaryQuery.data.boards.map((board) => {
              const selected = membershipQuery.data?.boardIds.includes(board.id) ?? false;
              return (
                <button
                  key={board.id}
                  type="button"
                  className={`flex w-full items-center justify-between rounded-xl border px-3 py-3 text-left transition ${selected ? 'border-foreground bg-foreground text-background' : 'border-border bg-white hover:bg-secondary/60'}`}
                  disabled={boardMutation.isPending}
                  onClick={() => boardMutation.mutate({ boardId: board.id, selected })}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <FolderHeart className="size-4 shrink-0" />
                    <span className="truncate text-sm font-medium">{board.name}</span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2 text-xs opacity-75">
                    {board.itemCount} 张
                    {selected && <Check className="size-4" />}
                  </span>
                </button>
              );
            }) : (
              <div className="rounded-xl border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
                还没有画板，在下方新建一个
              </div>
            )}
          </div>
          <div className="flex gap-2 border-t border-border pt-4">
            <Input
              aria-label="新画板名称"
              value={newBoardName}
              maxLength={80}
              placeholder="新画板名称"
              onChange={(event) => setNewBoardName(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && newBoardName.trim()) createMutation.mutate();
              }}
            />
            <Button
              type="button"
              className="shrink-0"
              disabled={!newBoardName.trim() || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              <Plus className="size-4" />新建并收藏
            </Button>
          </div>
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
