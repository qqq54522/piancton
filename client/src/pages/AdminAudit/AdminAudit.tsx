import { useQuery } from '@tanstack/react-query';

import { fetchAuditLogs } from '@client/src/api/admin';
import { getApiError } from '@client/src/api/client';
import EmptyState from '@client/src/components/EmptyState';
import PageHeader from '@client/src/components/PageHeader';
import { ScrollText } from 'lucide-react';

const actionLabels: Record<string, string> = {
  'auth.login': '用户登录',
  'auth.logout': '用户退出',
  'image.upload': '上传图片',
  'image.update': '修改图片',
  'image.delete': '移入回收站',
  'image.restore': '恢复图片',
  'image.purge': '永久删除图片',
  'user.create': '创建用户',
  'user.update': '修改用户权限',
  'user.reset_password': '重置用户密码',
};

const targetLabels: Record<string, string> = {
  image: '图片',
  asset_group: '素材组',
  user: '用户',
  session: '会话',
};


export default function AdminAudit() {
  const logs = useQuery({ queryKey: ['audit-logs'], queryFn: fetchAuditLogs });
  return (
    <div className="page-shell max-w-7xl">
      <PageHeader title="审计日志" />
      <div className="surface-card mt-7 overflow-hidden">
        {logs.isLoading ? (
          <p className="p-5 text-sm text-muted-foreground">正在加载...</p>
        ) : logs.isError ? (
          <p className="p-5 text-sm text-destructive">{getApiError(logs.error).message}</p>
        ) : logs.data?.length ? (
          <>
            <div className="hidden grid-cols-[180px_180px_1fr] border-b bg-secondary/45 px-5 py-3 text-xs font-medium text-muted-foreground md:grid">
              <span>发生时间</span><span>做了什么</span><span>操作对象</span>
            </div>
            {logs.data.map((entry) => (
            <div key={entry.id} className="grid gap-2 border-b border-border/70 px-5 py-4 last:border-0 md:grid-cols-[180px_180px_1fr]">
              <time className="text-xs text-muted-foreground">
                {new Date(entry.createdAt).toLocaleString('zh-CN')}
              </time>
              <span className="text-sm font-medium">{actionLabels[entry.action] ?? entry.action}</span>
              <div className="min-w-0 text-xs text-muted-foreground">
                {targetLabels[entry.targetType] ?? entry.targetType}{entry.targetId ? ` · ${entry.targetId}` : ''}
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
