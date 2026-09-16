import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, FolderHeart, Pencil, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';

import {
  createCollectionBoard,
  deleteCollectionBoard,
  fetchCollectionBoardItems,
  fetchCollectionBoards,
  renameCollectionBoard,
} from '@client/src/api/assetCollections';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { assetCollectionQueryKeys } from '@client/src/features/assets/assetCollectionQueryKeys';
import ImageGrid from '@client/src/pages/ImageHome/ImageGrid';

const MyCollections = () => {
  const { boardId } = useParams<{ boardId: string }>();
  return boardId ? <BoardDetail boardId={boardId} /> : <BoardList />;
};

const BoardList = () => {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const boardsQuery = useQuery({
    queryKey: assetCollectionQueryKeys.boards,
    queryFn: fetchCollectionBoards,
  });
  const createMutation = useMutation({
    mutationFn: () => createCollectionBoard(name.trim()),
    onSuccess: async () => {
      setName('');
      await invalidateBoards(queryClient);
      toast.success('画板已创建');
    },
    onError: () => toast.error('画板创建失败，请检查名称是否重复'),
  });
  const renameMutation = useMutation({
    mutationFn: ({ boardId, nextName }: { boardId: string; nextName: string }) => (
      renameCollectionBoard(boardId, nextName)
    ),
    onSuccess: async () => {
      await invalidateBoards(queryClient);
      toast.success('画板已重命名');
    },
    onError: () => toast.error('重命名失败，请检查名称是否重复'),
  });
  const deleteMutation = useMutation({
    mutationFn: deleteCollectionBoard,
    onSuccess: async () => {
      await invalidateBoards(queryClient);
      toast.success('画板已删除，图片素材仍保留在素材库');
    },
    onError: () => toast.error('画板删除失败'),
  });

  return (
    <div className="min-h-screen bg-[#f7f7f5]">
      <CollectionHeader title="我的收藏" description="用私有画板整理你常用的业务素材" />
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <div className="mb-8 flex gap-2 rounded-2xl border border-border/70 bg-white p-4 shadow-sm">
          <Input
            aria-label="画板名称"
            value={name}
            maxLength={80}
            placeholder="新画板名称，例如：秋季家长会"
            onChange={(event) => setName(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && name.trim()) createMutation.mutate();
            }}
          />
          <Button
            type="button"
            className="shrink-0"
            disabled={!name.trim() || createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            <Plus className="size-4" />新建画板
          </Button>
        </div>
        {boardsQuery.isLoading ? (
          <div className="grid min-h-[35vh] place-items-center text-sm text-muted-foreground">正在加载...</div>
        ) : boardsQuery.data?.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {boardsQuery.data.map((board) => (
              <article key={board.id} className="group rounded-2xl border border-border/70 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
                <Link to={`/my-collections/${board.id}`} className="block">
                  <span className="mb-5 flex size-12 items-center justify-center rounded-2xl bg-[#f1f1ef]">
                    <FolderHeart className="size-5" />
                  </span>
                  <h2 className="truncate font-semibold">{board.name}</h2>
                  <p className="mt-1 text-xs text-muted-foreground">{board.itemCount} 张图片</p>
                </Link>
                <div className="mt-4 flex justify-end gap-1 border-t border-border/60 pt-3">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const nextName = window.prompt('新的画板名称', board.name)?.trim();
                      if (nextName && nextName !== board.name) {
                        renameMutation.mutate({ boardId: board.id, nextName });
                      }
                    }}
                  >
                    <Pencil className="size-3.5" />重命名
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    onClick={() => {
                      if (window.confirm(`删除画板「${board.name}」？图片素材不会被删除。`)) {
                        deleteMutation.mutate(board.id);
                      }
                    }}
                  >
                    <Trash2 className="size-3.5" />删除
                  </Button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed py-20 text-center text-sm text-muted-foreground">
            还没有画板，新建一个后就能从图片快捷操作里收藏
          </div>
        )}
      </main>
    </div>
  );
};

const BoardDetail = ({ boardId }: { boardId: string }) => {
  const navigate = useNavigate();
  const boardsQuery = useQuery({
    queryKey: assetCollectionQueryKeys.boards,
    queryFn: fetchCollectionBoards,
  });
  const board = boardsQuery.data?.find((item) => item.id === boardId);
  const itemsQuery = useInfiniteQuery({
    queryKey: assetCollectionQueryKeys.boardItems(boardId),
    queryFn: ({ pageParam }) => fetchCollectionBoardItems(boardId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => (
      lastPage.hasMore ? lastPage.nextCursor || undefined : undefined
    ),
  });
  const images = itemsQuery.data?.pages.flatMap((page) => page.items.map((item) => item.image)) ?? [];

  return (
    <div className="min-h-screen bg-[#f7f7f5]">
      <header className="sticky top-0 z-40 border-b border-border/70 bg-white/95 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1920px] items-center gap-3 px-4 py-4 sm:px-6 lg:px-8">
          <Button variant="ghost" size="icon" onClick={() => navigate('/my-collections')} aria-label="返回我的收藏">
            <ArrowLeft className="size-5" />
          </Button>
          <span className="flex size-10 items-center justify-center rounded-full bg-[#f1f1ef]">
            <FolderHeart className="size-5" />
          </span>
          <div>
            <h1 className="text-lg font-semibold">{board?.name || '我的画板'}</h1>
            <p className="text-xs text-muted-foreground">{board ? `${board.itemCount} 张图片` : '正在加载画板'}</p>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1920px] px-4 py-6 sm:px-6 lg:px-8">
        {itemsQuery.isLoading ? (
          <div className="grid min-h-[45vh] place-items-center text-sm text-muted-foreground">正在加载...</div>
        ) : (
          <ImageGrid
            images={images}
            layout="masonry"
            emptyVariant="plain"
            emptyText="这个画板还是空的"
            emptyDescription="从图片右上角的快捷操作选择收藏到画板。"
          />
        )}
        {itemsQuery.hasNextPage && (
          <div className="mt-6 flex justify-center">
            <Button
              variant="outline"
              disabled={itemsQuery.isFetchingNextPage}
              onClick={() => itemsQuery.fetchNextPage()}
            >
              {itemsQuery.isFetchingNextPage ? '加载中...' : '加载更多'}
            </Button>
          </div>
        )}
      </main>
    </div>
  );
};

const CollectionHeader = ({ title, description }: { title: string; description: string }) => (
  <header className="sticky top-0 z-40 border-b border-border/70 bg-white/95 backdrop-blur-xl">
    <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-4 sm:px-6">
      <Button variant="ghost" size="icon" asChild>
        <Link to="/" aria-label="返回素材库"><ArrowLeft className="size-5" /></Link>
      </Button>
      <span className="flex size-10 items-center justify-center rounded-full bg-[#f1f1ef]">
        <FolderHeart className="size-5" />
      </span>
      <div>
        <h1 className="text-lg font-semibold">{title}</h1>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <Button variant="outline" size="sm" className="ml-auto rounded-full" asChild>
        <Link to="/my-likes">我的喜欢</Link>
      </Button>
    </div>
  </header>
);

async function invalidateBoards(queryClient: ReturnType<typeof useQueryClient>) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: assetCollectionQueryKeys.boards }),
    queryClient.invalidateQueries({ queryKey: assetCollectionQueryKeys.summary }),
  ]);
}

export default MyCollections;
