import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Check, Clipboard, ExternalLink, Fingerprint, RefreshCw, Search } from 'lucide-react';
import { toast } from 'sonner';

import { fetchIdentityCodes } from '@client/src/api/admin';
import { getApiError } from '@client/src/api/client';
import EmptyState from '@client/src/components/EmptyState';
import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import type { ImageIdentityCodeRead } from '@client/src/types/api';

const PAGE_SIZE = 20;

export default function AdminIdentityCodes() {
  const [keyword, setKeyword] = useState('');
  const [queryKeyword, setQueryKeyword] = useState('');
  const [page, setPage] = useState(1);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ['admin-identity-codes', queryKeyword, page],
    queryFn: () => fetchIdentityCodes({
      q: queryKeyword || undefined,
      page,
      pageSize: PAGE_SIZE,
    }),
  });

  const pageCount = useMemo(
    () => Math.max(1, Math.ceil((query.data?.total ?? 0) / PAGE_SIZE)),
    [query.data?.total],
  );

  const submitSearch = () => {
    setQueryKeyword(keyword.trim());
    setPage(1);
  };

  const copyCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(code);
      window.setTimeout(() => setCopiedCode((current) => current === code ? null : current), 1600);
      toast.success('身份码已复制');
    } catch {
      toast.error('复制失败，请手动选择身份码');
    }
  };

  return (
    <div className="page-shell max-w-7xl">
      <PageHeader
        eyebrow="Image Identity"
        title="身份码管理"
        description="每张当前图片只对应一个身份码；图片删除后，身份码同步从这里移除。"
        actions={(
          <Button variant="outline" size="sm" onClick={() => query.refetch()} disabled={query.isFetching}>
            <RefreshCw className={query.isFetching ? 'size-4 animate-spin' : 'size-4'} />
            刷新
          </Button>
        )}
      />

      <section className="surface-card mt-6 overflow-hidden">
        <div className="border-b border-border/80 p-4 sm:p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <label className="min-w-0 flex-1">
              <span className="field-label">搜索身份码或图片</span>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={keyword}
                  onChange={(event) => setKeyword(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') submitSearch();
                  }}
                  placeholder="输入身份码、图片名称或文件名"
                  className="pl-10"
                />
              </div>
            </label>
            <Button onClick={submitSearch}>
              <Search className="size-4" />搜索
            </Button>
          </div>
          <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary">{query.data?.summary.imageTotal ?? 0} 张图片</Badge>
            <span>这里只显示未删除图片，不保留已删除身份码历史。</span>
          </div>
        </div>

        {query.isLoading ? (
          <p className="p-6 text-sm text-muted-foreground">正在加载身份码…</p>
        ) : query.isError ? (
          <p className="p-6 text-sm text-destructive">{getApiError(query.error).message}</p>
        ) : query.data?.items.length ? (
          <>
            <div className="hidden grid-cols-[minmax(220px,0.9fr)_minmax(260px,1.4fr)_150px_180px] border-b bg-secondary/45 px-5 py-3 text-xs font-medium text-muted-foreground lg:grid">
              <span>身份码</span>
              <span>图片</span>
              <span>图片信息</span>
              <span>上传时间</span>
            </div>
            {query.data.items.map((item: ImageIdentityCodeRead) => (
              <IdentityCodeRow
                key={item.code}
                item={item}
                copied={copiedCode === item.code}
                onCopy={copyCode}
              />
            ))}
            <Pagination page={page} pageCount={pageCount} onChange={setPage} />
          </>
        ) : (
          <EmptyState
            icon={<Fingerprint className="size-5" />}
            title="暂无匹配的身份码"
            description="上传图片后，系统会为这张图片自动分配一个身份码。"
          />
        )}
      </section>
    </div>
  );
}

function IdentityCodeRow({
  item,
  copied,
  onCopy,
}: {
  item: ImageIdentityCodeRead;
  copied: boolean;
  onCopy: (code: string) => void;
}) {
  const dimensions = item.width && item.height ? `${item.width}×${item.height}` : '尺寸未记录';
  return (
    <div className="grid gap-4 border-b border-border/70 px-5 py-4 last:border-0 lg:grid-cols-[minmax(220px,0.9fr)_minmax(260px,1.4fr)_150px_180px] lg:items-center">
      <div className="flex min-w-0 items-center gap-2">
        <code className="break-all text-sm font-semibold tracking-wide">{item.code}</code>
        <Button
          variant="ghost"
          size="icon"
          className="size-8 shrink-0"
          aria-label={`复制 ${item.code}`}
          title="复制身份码"
          onClick={() => onCopy(item.code)}
        >
          {copied ? <Check className="size-3.5 text-emerald-600" /> : <Clipboard className="size-3.5" />}
        </Button>
      </div>
      <div className="min-w-0">
        <div className="truncate text-sm font-medium">{item.imageTitle}</div>
        <div className="mt-1 truncate text-xs text-muted-foreground">{item.fileName}</div>
      </div>
      <div className="text-sm text-muted-foreground">
        <div>{dimensions}</div>
        <div className="mt-1 text-xs">{item.channel || '未标渠道'}</div>
      </div>
      <div className="flex items-center justify-between gap-3 lg:block">
        <time className="text-xs text-muted-foreground">{formatDate(item.createdAt)}</time>
        <a
          href={item.detailPath}
          className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-foreground underline-offset-4 hover:underline"
        >
          查看图片 <ExternalLink className="size-3" />
        </a>
      </div>
    </div>
  );
}

function Pagination({
  page,
  pageCount,
  onChange,
}: {
  page: number;
  pageCount: number;
  onChange: (page: number) => void;
}) {
  if (pageCount <= 1) return null;
  return (
    <div className="flex items-center justify-between border-t border-border/80 px-5 py-4">
      <span className="text-xs text-muted-foreground">第 {page} / {pageCount} 页</span>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>上一页</Button>
        <Button variant="outline" size="sm" disabled={page >= pageCount} onClick={() => onChange(page + 1)}>下一页</Button>
      </div>
    </div>
  );
}

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}
