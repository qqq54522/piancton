import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  CalendarDays,
  Download,
  LogIn,
  MousePointerClick,
  Users,
} from 'lucide-react';

import { fetchUsageAnalyticsSummary } from '@client/src/api/admin';
import { getApiError } from '@client/src/api/client';
import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import type {
  DailyUsageMetric,
  UsageAnalyticsSummary,
  UsageEventRead,
  UserUsageMetric,
} from '@client/src/types/api';

const dayOptions = [1, 7, 30, 90] as const;

const eventLabels: Record<string, string> = {
  login: '登录',
  page_view: '访问',
  download: '下载',
};

const roleLabels: Record<string, string> = {
  admin: '管理员',
  designer: '设计师',
  business: '业务用户',
};

export default function AdminUsage() {
  const [days, setDays] = useState<(typeof dayOptions)[number]>(7);
  const summary = useQuery({
    queryKey: ['usage-analytics-summary', days],
    queryFn: () => fetchUsageAnalyticsSummary(days),
  });
  const data = summary.data;

  return (
    <div className="page-shell max-w-7xl">
      <PageHeader
        eyebrow="Usage Analytics"
        title="使用统计"
        description="按用户查看登录、访问和下载使用量，保留今日与区间维度。"
        actions={(
          <div className="inline-flex w-fit overflow-hidden rounded-xl border border-border bg-card p-1">
            {dayOptions.map((value) => (
              <Button
                key={value}
                variant={days === value ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setDays(value)}
              >
                {value === 1 ? '今日' : `${value} 天`}
              </Button>
            ))}
          </div>
        )}
      />

      {summary.isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">正在加载...</p>
      ) : summary.isError ? (
        <p className="mt-6 text-sm text-destructive">
          {getApiError(summary.error).message}
        </p>
      ) : data ? (
        <div className="mt-7 space-y-6">
          <Overview data={data} />
          <DailyTable rows={data.daily} />
          <UserTable rows={data.users} />
          <RecentEvents rows={data.recentEvents} />
        </div>
      ) : null}
    </div>
  );
}

function Overview({ data }: { data: UsageAnalyticsSummary }) {
  const items = [
    {
      label: '登录次数',
      value: data.totals.loginCount,
      icon: LogIn,
    },
    {
      label: '页面访问',
      value: data.totals.pageViewCount,
      icon: MousePointerClick,
    },
    {
      label: '下载次数',
      value: data.totals.downloadCount,
      icon: Download,
    },
    {
      label: '活跃用户',
      value: data.totals.activeUserCount,
      icon: Users,
    },
  ];
  return (
    <section>
      <div className="mb-3 flex items-center gap-2 text-sm text-muted-foreground">
        <CalendarDays className="size-4" />
        {data.dateFrom} 至 {data.dateTo}
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="surface-card p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-muted-foreground">{item.label}</span>
                <Icon className="size-4 text-primary" />
              </div>
              <div className="mt-2 text-2xl font-semibold text-foreground">
                {item.value}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function DailyTable({ rows }: { rows: DailyUsageMetric[] }) {
  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader title="每日趋势" />
      <div className="hidden grid-cols-5 border-b bg-secondary/45 px-5 py-3 text-xs font-medium text-muted-foreground md:grid">
        <span>日期</span>
        <span>登录</span>
        <span>访问</span>
        <span>下载</span>
        <span>活跃用户</span>
      </div>
      {rows.map((row) => (
        <div
          key={row.date}
          className="grid gap-2 border-b border-border/70 px-5 py-4 text-sm last:border-0 md:grid-cols-5"
        >
          <span className="font-medium text-foreground">{row.date}</span>
          <MetricLine label="登录" value={row.loginCount} />
          <MetricLine label="访问" value={row.pageViewCount} />
          <MetricLine label="下载" value={row.downloadCount} />
          <MetricLine label="活跃" value={row.activeUserCount} />
        </div>
      ))}
    </section>
  );
}

function UserTable({ rows }: { rows: UserUsageMetric[] }) {
  const sorted = [...rows].sort((left, right) => right.activityCount - left.activityCount);
  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader title="用户使用量" />
      <div className="hidden grid-cols-[1.5fr_90px_repeat(4,90px)_150px] border-b bg-secondary/45 px-5 py-3 text-xs font-medium text-muted-foreground lg:grid">
        <span>用户</span>
        <span>身份</span>
        <span>登录</span>
        <span>访问</span>
        <span>下载</span>
        <span>总活动</span>
        <span>最近活动</span>
      </div>
      {sorted.map((row) => (
        <div
          key={row.userId}
          className="grid gap-2 border-b border-border/70 px-5 py-4 text-sm last:border-0 lg:grid-cols-[1.5fr_90px_repeat(4,90px)_150px]"
        >
          <div className="min-w-0">
            <div className="truncate font-medium text-foreground">{row.username}</div>
            {!row.isActive && <div className="mt-1 text-xs text-muted-foreground">已停用</div>}
          </div>
          <span className="text-muted-foreground">{roleLabels[row.role] ?? row.role}</span>
          <MetricLine label="登录" value={row.loginCount} />
          <MetricLine label="访问" value={row.pageViewCount} />
          <MetricLine label="下载" value={row.downloadCount} />
          <MetricLine label="总活动" value={row.activityCount} />
          <span className="text-xs text-muted-foreground">
            {row.lastActivityAt ? new Date(row.lastActivityAt).toLocaleString('zh-CN') : '-'}
          </span>
        </div>
      ))}
    </section>
  );
}

function RecentEvents({ rows }: { rows: UsageEventRead[] }) {
  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader title="最近事件" />
      {rows.length ? (
        rows.map((row) => (
          <div
            key={row.id}
            className="grid gap-2 border-b border-border/70 px-5 py-4 text-sm last:border-0 md:grid-cols-[160px_110px_1fr_180px]"
          >
            <time className="text-xs text-muted-foreground">
              {new Date(row.createdAt).toLocaleString('zh-CN')}
            </time>
            <Badge variant="outline" className="w-fit">
              {eventLabels[row.eventType] ?? row.eventType}
            </Badge>
            <span className="min-w-0 truncate text-foreground">
              {row.username ?? '未知用户'}
              {row.path ? ` · ${row.path}` : ''}
              {row.targetId ? ` · ${row.targetId}` : ''}
            </span>
            <span className="text-xs text-muted-foreground">
              {row.targetType ?? '-'}
            </span>
          </div>
        ))
      ) : (
        <div className="grid min-h-32 place-items-center text-sm text-muted-foreground">
          暂无使用记录
        </div>
      )}
    </section>
  );
}

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="flex items-center gap-2 border-b border-border bg-secondary/30 px-5 py-3">
      <Activity className="size-4 text-primary" />
      <h2 className="text-sm font-semibold text-foreground">{title}</h2>
    </div>
  );
}

function MetricLine({ label, value }: { label: string; value: number }) {
  return (
    <span className="flex items-center justify-between gap-3 text-muted-foreground md:block">
      <span className="md:hidden">{label}</span>
      <span className="font-medium text-foreground">{value}</span>
    </span>
  );
}
