import { useInfiniteQuery } from '@tanstack/react-query';
import { ArrowLeft, Heart } from 'lucide-react';
import { Link } from 'react-router-dom';

import { fetchLikedAssets } from '@client/src/api/assetCollections';
import { Button } from '@client/src/components/ui/button';
import ImageGrid from '@client/src/pages/ImageHome/ImageGrid';

const MyLikes = () => {
  const query = useInfiniteQuery({
    queryKey: ['asset-collections', 'likes'],
    queryFn: ({ pageParam }) => fetchLikedAssets(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => (
      lastPage.hasMore ? lastPage.nextCursor || undefined : undefined
    ),
  });
  const images = query.data?.pages.flatMap((page) => page.items.map((item) => item.image)) ?? [];

  return (
    <div className="min-h-screen bg-[#f7f7f5]">
      <header className="sticky top-0 z-40 border-b border-border/70 bg-white/95 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1920px] items-center gap-3 px-4 py-4 sm:px-6 lg:px-8">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/" aria-label="返回素材库"><ArrowLeft className="size-5" /></Link>
          </Button>
          <span className="flex size-10 items-center justify-center rounded-full bg-rose-50 text-rose-600">
            <Heart className="size-5 fill-current" />
          </span>
          <div>
            <h1 className="text-lg font-semibold">我的喜欢</h1>
            <p className="text-xs text-muted-foreground">你点过喜欢的素材都在这里，不按画板分组</p>
          </div>
          <Button variant="outline" size="sm" className="ml-auto rounded-full" asChild>
            <Link to="/my-collections">我的收藏</Link>
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-[1920px] px-4 py-6 sm:px-6 lg:px-8">
        {query.isLoading ? (
          <div className="grid min-h-[45vh] place-items-center text-sm text-muted-foreground">正在加载...</div>
        ) : (
          <ImageGrid
            images={images}
            layout="masonry"
            emptyVariant="plain"
            emptyText="还没有喜欢的图片"
            emptyDescription="在图片右上角的快捷操作里点喜欢，就会出现在这里。"
          />
        )}
        {query.hasNextPage && (
          <div className="mt-6 flex justify-center">
            <Button
              type="button"
              variant="outline"
              disabled={query.isFetchingNextPage}
              onClick={() => query.fetchNextPage()}
            >
              {query.isFetchingNextPage ? '加载中...' : '加载更多'}
            </Button>
          </div>
        )}
      </main>
    </div>
  );
};

export default MyLikes;
