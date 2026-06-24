import { useQuery } from '@tanstack/react-query';

import { fetchAuditLogs } from '@client/src/api/admin';
import { getApiError } from '@client/src/api/client';


export default function AdminAudit() {
  const logs = useQuery({ queryKey: ['audit-logs'], queryFn: fetchAuditLogs });
  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-semibold">审计日志</h1>
      <p className="mt-1 text-sm text-muted-foreground">记录登录、素材、标签和用户管理操作。</p>
      <div className="mt-6 overflow-hidden rounded-xl border bg-card">
        {logs.isLoading ? (
          <p className="p-5 text-sm text-muted-foreground">正在加载...</p>
        ) : logs.isError ? (
          <p className="p-5 text-sm text-destructive">{getApiError(logs.error).message}</p>
        ) : logs.data?.length ? (
          logs.data.map((entry) => (
            <div key={entry.id} className="grid gap-2 border-b p-4 last:border-0 md:grid-cols-[180px_180px_1fr]">
              <time className="text-xs text-muted-foreground">
                {new Date(entry.createdAt).toLocaleString('zh-CN')}
              </time>
              <code className="text-xs">{entry.action}</code>
              <div className="min-w-0 text-xs text-muted-foreground">
                {entry.targetType}{entry.targetId ? ` · ${entry.targetId}` : ''}
                {entry.requestId ? ` · request ${entry.requestId}` : ''}
              </div>
            </div>
          ))
        ) : (
          <p className="p-5 text-sm text-muted-foreground">暂无审计记录</p>
        )}
      </div>
    </div>
  );
}
