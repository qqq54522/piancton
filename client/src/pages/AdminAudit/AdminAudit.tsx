import { useQuery } from '@tanstack/react-query';

import { fetchAuditLogs } from '@client/src/api/admin';
import { getApiError } from '@client/src/api/client';
import EmptyState from '@client/src/components/EmptyState';
import PageHeader from '@client/src/components/PageHeader';
import { ScrollText } from 'lucide-react';


export default function AdminAudit() {
  const logs = useQuery({ queryKey: ['audit-logs'], queryFn: fetchAuditLogs });
  return (
    <div className="page-shell max-w-7xl">
      <PageHeader
        eyebrow="Audit Trail"
        title="审计日志"
        description="追踪登录、素材、搜索和用户权限操作，便于排查问题与责任回溯。"
      />
      <div className="surface-card mt-7 overflow-hidden">
        {logs.isLoading ? (
          <p className="p-5 text-sm text-muted-foreground">正在加载...</p>
        ) : logs.isError ? (
          <p className="p-5 text-sm text-destructive">{getApiError(logs.error).message}</p>
        ) : logs.data?.length ? (
          <>
            <div className="hidden grid-cols-[180px_180px_1fr] border-b bg-secondary/45 px-5 py-3 text-xs font-medium text-muted-foreground md:grid">
              <span>发生时间</span><span>操作类型</span><span>目标与请求</span>
            </div>
            {logs.data.map((entry) => (
            <div key={entry.id} className="grid gap-2 border-b border-border/70 px-5 py-4 last:border-0 md:grid-cols-[180px_180px_1fr]">
              <time className="text-xs text-muted-foreground">
                {new Date(entry.createdAt).toLocaleString('zh-CN')}
              </time>
              <code className="text-xs">{entry.action}</code>
              <div className="min-w-0 text-xs text-muted-foreground">
                {entry.targetType}{entry.targetId ? ` · ${entry.targetId}` : ''}
                {entry.requestId ? ` · request ${entry.requestId}` : ''}
              </div>
            </div>
            ))}
          </>
        ) : (
          <div className="border-0">
            <EmptyState icon={<ScrollText className="size-5" />} title="暂无审计记录" description="后续登录和管理操作会显示在这里。" />
          </div>
        )}
      </div>
    </div>
  );
}
