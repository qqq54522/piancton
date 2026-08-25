import { useEffect, useMemo, useState } from 'react';
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
import { Select } from '@client/src/components/ui/select';
import type {
  AssetIdentityCodeRead,
  AssetIdentityCodeStatus,
} from '@client/src/types/api';

const PAGE_SIZE = 20;

const statusLabels: Record<'all' | AssetIdentityCodeStatus, string> = {
  all: '全部状态',
  active: '当前有效',
  deleted: '图片已删除',
  retired: '已退休',
};

export default function AdminIdentityCodes() {
  const [keyword, setKeyword] = useState('');
  const [queryKeyword, setQueryKeyword] = useState('');
  const [codeType, setCodeType] = useState<'all' | 'asset' | 'version'>('all');
  const [status, setStatus] = useState<'all' | AssetIdentityCodeStatus>('all');
  const [page, setPage] = useState(1);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ['admin-identity-codes', queryKeyword, codeType, status, page],
    queryFn: () => fetchIdentityCodes({
      q: queryKeyword || undefined,
      codeType,
      status,
      page,
      pageSize: PAGE_SIZE,
    }),
  });

  useEffect(() => {
    setPage(1);
  }, [queryKeyword, codeType, status]);

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
        eyebrow="Asset Identity Registry"
        title="身份码管理"
        description="查看所有素材组和图片版本的正式身份码。身份码由系统自动分配并永久登记，不支持手工修改。"
        actions={(
          <Button variant="outline" size="sm" onClick={() => query.refetch()} disabled={query.isFetching}>
            <RefreshCw className={query.isFetching ? 'size-4 animate-spin' : 'size-4'} />
            刷新台账
          </Button>
        )}
      />

      <SummaryCards summary={query.data?.summary} />

      <section className="surface-card mt-6 overflow-hidden">
        <div className="border-b border-border/80 p-4 sm:p-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
            <label className="min-w-0 flex-1">
              <span className="field-label">搜索身份码或素材</span>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={keyword}
                  onChange={(event) => setKeyword(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') submitSearch();
                  }}
                  placeholder="输入素材码、版本码、素材名称或文件名"
                  className="pl-10"
                />
              </div>
            </label>
            <label className="w-full lg:w-40">
              <span className="field-label">码类型</span>
              <Select
                value={codeType}
                onChange={(event) => {
                  setCodeType(event.target.value as typeof codeType);
                  setPage(1);
                }}
              >
                <option value="all">全部类型</option>
                <option value="asset">素材码</option>
                <option value="version">版本码</option>
              </Select>
            </label>
            <label className="w-full lg:w-40">
              <span className="field-label">状态</span>
              <Select
                value={status}
                onChange={(event) => {
                  setStatus(event.target.value as typeof status);
                  setPage(1);
                }}
              >
                {Object.entries(statusLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </Select>
            </label>
            <Button onClick={submitSearch}>
              <Search className="size-4" />搜索
            </Button>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            台账包含当前有效、已删除和已退休身份码；删除或永久清理不会释放旧码。
          </p>
        </div>

        {query.isLoading ? (
          <p className="p-6 text-sm text-muted-foreground">正在加载身份码台账…</p>
        ) : query.isError ? (
          <p className="p-6 text-sm text-destructive">{getApiError(query.error).message}</p>
        ) : query.data?.items.length ? (
          <>
            <div className="hidden grid-cols-[minmax(220px,1.2fr)_100px_minmax(220px,1fr)_130px_130px_180px] border-b bg-secondary/45 px-5 py-3 text-xs font-medium text-muted-foreground xl:grid">
              <span>身份码</span>
              <span>类型</span>
              <span>关联素材</span>
              <span>版本信息</span>
              <span>状态</span>
              <span>登记时间</span>
            </div>
                {query.data.items.map((item: AssetIdentityCodeRead) => (
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
            description="新增素材后，系统会自动分配身份码并出现在这份台账中。"
          />
        )}
      </section>
    </div>
  );
}

function SummaryCards({
  summary,
}: {
  summary?: {
    assetTotal: number;
    versionTotal: number;
    activeTotal: number;
    deletedTotal: number;
    retiredTotal: number;
  };
}) {
  const cards = [
    { label: '素材组', value: summary?.assetTotal ?? 0 },
    { label: '图片版本', value: summary?.versionTotal ?? 0 },
    { label: '当前有效码', value: summary?.activeTotal ?? 0 },
    { label: '已删除 / 退休', value: (summary?.deletedTotal ?? 0) + (summary?.retiredTotal ?? 0) },
  ];
  return (
    <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <div key={card.label} className="surface-card px-4 py-4">
          <p className="text-xs text-muted-foreground">{card.label}</p>
          <p className="mt-1 text-2xl font-semibold tracking-tight">{card.value}</p>
        </div>
      ))}
    </div>
  );
}

function IdentityCodeRow({
  item,
  copied,
  onCopy,
}: {
  item: AssetIdentityCodeRead;
  copied: boolean;
  onCopy: (code: string) => void;
}) {
  const title = item.codeType === 'asset'
    ? item.assetTitle ?? '未关联素材组'
    : item.imageTitle ?? item.assetTitle ?? '未关联图片';
  const detailPath = item.status === 'active' && item.codeType === 'version' && item.imageId
    ? `/image/${item.imageId}`
    : item.status === 'active' && item.primaryImageId
      ? `/image/${item.primaryImageId}`
      : item.status === 'active' ? item.detailPath : undefined;
  return (
    <div className="grid gap-4 border-b border-border/70 px-5 py-4 last:border-0 xl:grid-cols-[minmax(220px,1.2fr)_100px_minmax(220px,1fr)_130px_130px_180px] xl:items-center">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
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
        <div className="mt-1 text-xs text-muted-foreground">
          {item.codeType === 'asset' ? '素材组长期身份' : '图片版本身份'}
        </div>
      </div>
      <div><Badge variant="outline">{item.codeType === 'asset' ? '素材码' : '版本码'}</Badge></div>
      <div className="min-w-0">
        <div className="truncate text-sm font-medium">{title}</div>
        <div className="mt-1 truncate text-xs text-muted-foreground">
          {item.codeType === 'asset' ? `${item.assetTitle ?? '未命名'} · ${item.primaryImageId ? '已关联主图' : '未关联主图'}` : item.fileName ?? '图片记录'}
        </div>
      </div>
      <div className="text-sm text-muted-foreground">
        {item.codeType === 'version' ? `V${String(item.versionNo ?? 1).padStart(2, '0')}` : `${item.versionNo ? `当前 V${String(item.versionNo).padStart(2, '0')}` : '素材组'}`}
        {item.codeType === 'version' && item.isCurrent ? ' · 当前' : ''}
      </div>
      <div><StatusBadge status={item.status} /></div>
      <div className="flex items-center justify-between gap-3 xl:block">
        <time className="text-xs text-muted-foreground">{formatDate(item.createdAt)}</time>
        {detailPath && (
          <a
            href={detailPath}
            className="inline-flex items-center gap-1 text-xs font-medium text-foreground underline-offset-4 hover:underline"
          >
            查看素材 <ExternalLink className="size-3" />
          </a>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: AssetIdentityCodeStatus }) {
  const label = statusLabels[status];
  return <Badge variant={status === 'active' ? 'secondary' : 'outline'}>{label}</Badge>;
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
