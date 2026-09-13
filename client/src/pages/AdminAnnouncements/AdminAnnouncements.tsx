import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CalendarDays, Megaphone, Send, UserRound } from 'lucide-react';
import { toast } from 'sonner';

import {
  fetchManagedAnnouncements,
  publishAnnouncement,
} from '@client/src/api/announcements';
import PageHeader from '@client/src/components/PageHeader';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { announcementKeys } from '@client/src/features/announcements/useAnnouncements';
import { getApiError } from '@client/src/api/client';

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

const AdminAnnouncements = () => {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const announcements = useQuery({
    queryKey: announcementKeys.manage,
    queryFn: fetchManagedAnnouncements,
  });
  const publish = useMutation({
    mutationFn: publishAnnouncement,
    onSuccess: () => {
      setTitle('');
      setContent('');
      queryClient.invalidateQueries({ queryKey: announcementKeys.all });
      toast.success('公告已发布，业务用户将收到未读提醒');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });

  const canPublish = title.trim().length > 0 && content.trim().length > 0;

  return (
    <div className="page-shell">
      <PageHeader
        eyebrow="消息中心"
        title="公告管理"
        description="发布产品更新、功能优化和重要提醒。发布后，所有业务用户的头像旁都会出现未读数字。"
      />

      <div className="mt-6 grid gap-5 xl:grid-cols-[minmax(0,440px)_minmax(0,1fr)]">
        <section className="surface-card self-start p-5 sm:p-6">
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Megaphone className="size-5" />
            </span>
            <div>
              <h2 className="font-semibold">发布新公告</h2>
              <p className="text-xs text-muted-foreground">发布后立即生效</p>
            </div>
          </div>

          <label className="mt-5 block">
            <span className="field-label">公告标题</span>
            <Input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              maxLength={120}
              placeholder="例如：今日新增批量上传功能"
            />
            <span className="mt-1 block text-right text-[11px] text-muted-foreground">
              {title.length}/120
            </span>
          </label>

          <label className="mt-3 block">
            <span className="field-label">公告内容</span>
            <textarea
              value={content}
              onChange={(event) => setContent(event.target.value)}
              maxLength={5000}
              rows={10}
              placeholder="写清楚今天优化了什么、增加了什么，以及业务用户需要知道的使用变化。"
              className="w-full resize-y rounded-xl border border-input bg-background px-3 py-2 text-sm leading-6 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
            />
            <span className="mt-1 block text-right text-[11px] text-muted-foreground">
              {content.length}/5000
            </span>
          </label>

          <Button
            type="button"
            className="mt-4 w-full"
            disabled={!canPublish || publish.isPending}
            onClick={() => publish.mutate({ title: title.trim(), content: content.trim() })}
          >
            <Send className="size-4" />{publish.isPending ? '正在发布...' : '发布给所有业务用户'}
          </Button>
        </section>

        <section className="surface-card p-5 sm:p-6">
          <div className="flex items-center justify-between gap-3 border-b border-border/70 pb-4">
            <div>
              <h2 className="font-semibold">历史公告</h2>
              <p className="mt-1 text-xs text-muted-foreground">最多展示最近 100 条</p>
            </div>
            <span className="rounded-full bg-secondary px-3 py-1 text-xs text-muted-foreground">
              {announcements.data?.items.length ?? 0} 条
            </span>
          </div>

          {announcements.isLoading ? (
            <div className="grid min-h-48 place-items-center text-sm text-muted-foreground">正在加载...</div>
          ) : announcements.isError ? (
            <div className="grid min-h-48 place-items-center text-sm text-muted-foreground">公告加载失败</div>
          ) : announcements.data?.items.length ? (
            <div className="divide-y divide-border/70">
              {announcements.data.items.map((item) => (
                <article key={item.id} className="py-5 first:pt-4">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <h3 className="font-semibold text-foreground">{item.title}</h3>
                    <time className="flex shrink-0 items-center gap-1.5 text-xs text-muted-foreground" dateTime={item.publishedAt}>
                      <CalendarDays className="size-3.5" />{formatPublishedAt(item.publishedAt)}
                    </time>
                  </div>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-foreground/75">{item.content}</p>
                  <p className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
                    <UserRound className="size-3.5" />{item.publisherName}
                  </p>
                </article>
              ))}
            </div>
          ) : (
            <div className="grid min-h-48 place-items-center text-sm text-muted-foreground">还没有发布过公告</div>
          )}
        </section>
      </div>
    </div>
  );
};

export default AdminAnnouncements;
