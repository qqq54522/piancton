import { useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Bell, CalendarDays, UserRound } from 'lucide-react';
import { Link } from 'react-router-dom';

import {
  fetchAnnouncements,
  markAnnouncementsRead,
  type AnnouncementUnreadCount,
} from '@client/src/api/announcements';
import { Button } from '@client/src/components/ui/button';
import { announcementKeys } from '@client/src/features/announcements/useAnnouncements';

function formatPublishedAt(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(value));
}

const MyMessages = () => {
  const queryClient = useQueryClient();
  const markedThroughRef = useRef<string | null>(null);
  const feedQuery = useQuery({
    queryKey: announcementKeys.feed,
    queryFn: fetchAnnouncements,
  });
  const markRead = useMutation({
    mutationFn: markAnnouncementsRead,
    onSuccess: (result) => {
      queryClient.setQueryData<AnnouncementUnreadCount>(announcementKeys.unread, result);
      queryClient.setQueryData(announcementKeys.feed, (current: typeof feedQuery.data) => (
        current ? { ...current, unreadCount: result.unreadCount } : current
      ));
    },
  });

  useEffect(() => {
    const newest = feedQuery.data?.items[0];
    if (!newest || !feedQuery.data?.unreadCount) return;
    if (markedThroughRef.current === newest.publishedAt) return;
    markedThroughRef.current = newest.publishedAt;
    markRead.mutate(newest.publishedAt);
  }, [feedQuery.data, markRead]);

  return (
    <div className="min-h-screen bg-[#f7f7f5]">
      <header className="sticky top-0 z-40 border-b border-border/70 bg-white/95 backdrop-blur-xl">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-4 sm:px-6 lg:px-8">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/" aria-label="返回素材库"><ArrowLeft className="size-5" /></Link>
          </Button>
          <span className="flex size-10 items-center justify-center rounded-full bg-red-50 text-red-600">
            <Bell className="size-5" />
          </span>
          <div>
            <h1 className="text-lg font-semibold">我的信息</h1>
            <p className="text-xs text-muted-foreground">产品更新和重要通知都在这里</p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
        {feedQuery.isLoading ? (
          <div className="grid min-h-[45vh] place-items-center text-sm text-muted-foreground">
            正在加载消息...
          </div>
        ) : feedQuery.isError ? (
          <div className="surface-card grid min-h-56 place-items-center p-6 text-center">
            <div>
              <p className="text-sm font-medium">消息暂时加载失败</p>
              <Button className="mt-4" variant="outline" onClick={() => feedQuery.refetch()}>
                重新加载
              </Button>
            </div>
          </div>
        ) : feedQuery.data?.items.length ? (
          <div className="space-y-4">
            {feedQuery.data.items.map((item) => (
              <article key={item.id} className="surface-card p-5 sm:p-6">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <h2 className="text-lg font-semibold tracking-tight text-foreground">
                    {item.title}
                  </h2>
                  <time
                    dateTime={item.publishedAt}
                    className="flex shrink-0 items-center gap-1.5 text-xs text-muted-foreground"
                  >
                    <CalendarDays className="size-3.5" />{formatPublishedAt(item.publishedAt)}
                  </time>
                </div>
                <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-foreground/80">
                  {item.content}
                </p>
                <p className="mt-5 flex items-center gap-1.5 border-t border-border/70 pt-4 text-xs text-muted-foreground">
                  <UserRound className="size-3.5" />{item.publisherName}
                </p>
              </article>
            ))}
          </div>
        ) : (
          <div className="surface-card grid min-h-64 place-items-center p-6 text-center">
            <div>
              <Bell className="mx-auto size-8 text-muted-foreground/60" />
              <p className="mt-3 text-sm font-medium">暂时没有新消息</p>
              <p className="mt-1 text-xs text-muted-foreground">后续产品更新会第一时间出现在这里。</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default MyMessages;
