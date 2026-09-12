import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, Gauge, MessageSquareText, MousePointerClick, Search, Users } from 'lucide-react';
import { Link } from 'react-router-dom';

import { fetchSearchActivitySummary } from '@client/src/api/admin';
import { getApiError } from '@client/src/api/client';
import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import type {
  SearchFeedbackItem,
  SearchActivitySummary,
  SearchInteractionItem,
  SearchLogItem,
  SearchMetricItem,
} from '@client/src/types/api';

const dayOptions = [7, 30, 90] as const;
const tabs = [
  { id: 'searches', label: '搜索记录' },
  { id: 'behavior', label: '搜索后行为' },
  { id: 'feedback', label: '用户反馈' },
] as const;
type TabId = (typeof tabs)[number]['id'];

const roleLabels: Record<string, string> = {
  admin: '管理员',
  designer: '设计师',
  business: '业务用户',
};

const interactionLabels: Record<string, string> = {
  exposure: '看到图片',
  open_detail: '打开图片',
  download: '下载图片',
  copy_identity: '复制身份码',
  add_to_project: '加入项目夹',
  remove_from_project: '移出项目夹',
  send_to_agent: '发送到 Agent',
};

const feedbackLabels: Record<string, string> = {
  relevant: '满意',
  not_relevant: '不满意',
  too_few_results: '结果太少',
  need_different_style: '渠道或风格不对',
  right_business_wrong_visual: '卖点对，画面不对',
  right_visual_wrong_business: '画面对，卖点不对',
  wrong_version: '版本或尺寸不对',
  asset_request: '没有合适素材',
};

export default function AdminSearchOps() {
  const [days, setDays] = useState<(typeof dayOptions)[number]>(7);
  const [activeTab, setActiveTab] = useState<TabId>('searches');
  const summary = useQuery({
    queryKey: ['search-ops-summary', days],
    queryFn: () => fetchSearchActivitySummary(days),
  });
  const data = summary.data;

  return (
    <div className="page-shell max-w-[1500px]">
      <PageHeader
        title="搜索运营"
        actions={(
          <div className="inline-flex w-fit overflow-hidden rounded-xl border border-border bg-card p-1">
            {dayOptions.map((value) => (
              <Button
                key={value}
                variant={days === value ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setDays(value)}
              >
                {value} 天
              </Button>
            ))}
          </div>
        )}
      />

      {summary.isLoading ? (
        <p className="mt-7 text-sm text-muted-foreground">正在加载…</p>
      ) : summary.isError ? (
        <p className="mt-7 text-sm text-destructive">{getApiError(summary.error).message}</p>
      ) : data ? (
        <>
          <SearchOverview data={data} />
          <RecommendationEvaluationCard data={data} />
          <div className="mt-6 inline-flex flex-wrap gap-1 rounded-xl border border-border bg-card p-1">
            {tabs.map((tab) => (
              <Button
                key={tab.id}
                variant={activeTab === tab.id ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </Button>
            ))}
          </div>

          <div className="mt-4">
            {activeTab === 'searches' && (
              <SearchesSection rows={data.recentLogs} topQueries={data.topQueries} />
            )}
            {activeTab === 'behavior' && <BehaviorSection rows={data.recentInteractions} />}
            {activeTab === 'feedback' && <FeedbackSection rows={data.recentFeedback} />}
          </div>
        </>
      ) : null}
    </div>
  );
}

function RecommendationEvaluationCard({ data }: { data: SearchActivitySummary }) {
  const evaluation = data.recommendationEvaluation;
  const modeLabels = {
    learning: '积累样本',
    balanced: '平衡推荐',
    personalized: '强化个性化',
    explore: '增加探索',
  } as const;
  return (
    <section className="surface-card mt-4 flex flex-col gap-4 p-5 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex min-w-0 items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-full bg-secondary">
          <Gauge className="size-4" />
        </span>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-semibold">推荐效果自动评估</h2>
            <Badge variant="secondary">{modeLabels[evaluation.strategyMode]}</Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{evaluation.summary}</p>
        </div>
      </div>
      <div className="grid shrink-0 grid-cols-3 gap-5 text-center text-xs text-muted-foreground">
        <Metric label="猜你喜欢曝光" value={evaluation.exposureCount} />
        <Metric label="推荐后操作率" value={`${Math.round(evaluation.clickThroughRate * 100)}%`} />
        <Metric label="满意率" value={evaluation.feedbackCount ? `${Math.round(evaluation.satisfactionRate * 100)}%` : '待积累'} />
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-base font-semibold text-foreground">{value}</div>
      <div className="mt-0.5">{label}</div>
    </div>
  );
}

function SearchOverview({ data }: { data: SearchActivitySummary }) {
  const items = [
    { label: '搜索次数', value: data.totalSearches, icon: Search },
    { label: '搜索用户', value: data.searchUserCount, icon: Users },
    { label: '搜索后操作', value: data.interactionCount, icon: MousePointerClick },
    { label: '反馈完成率', value: `${data.feedbackResponseRate}%`, icon: MessageSquareText },
  ];
  return (
    <div className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <div key={item.label} className="surface-card p-4">
            <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
              <span>{item.label}</span>
              <Icon className="size-4" />
            </div>
            <div className="mt-2 text-2xl font-semibold">{item.value}</div>
          </div>
        );
      })}
    </div>
  );
}

function SearchesSection({ rows, topQueries }: { rows: SearchLogItem[]; topQueries: SearchMetricItem[] }) {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
      <section className="surface-card overflow-hidden">
        <SectionTitle title="他们搜索了什么" />
        {rows.length ? rows.map((row) => (
          <div
            key={row.id}
            className="grid gap-2 border-b border-border/70 px-5 py-4 text-sm last:border-0 lg:grid-cols-[150px_150px_minmax(220px,1.6fr)_minmax(150px,1fr)_90px]"
          >
            <time className="text-xs text-muted-foreground">{formatTime(row.createdAt)}</time>
            <UserCell username={row.actorUsername} role={row.actorRole} />
            <div className="min-w-0">
              <p className="font-medium text-foreground">{row.keyword}</p>
              {row.normalizedQuery && row.normalizedQuery !== row.keyword && (
                <p className="mt-1 truncate text-xs text-muted-foreground">理解为：{row.normalizedQuery}</p>
              )}
            </div>
            <span className="text-muted-foreground">{row.matchedConcept || '未命中卖点'}</span>
            <Badge variant={row.resultCount > 0 ? 'secondary' : 'outline'} className="h-fit w-fit">
              {row.resultCount} 张
            </Badge>
          </div>
        )) : <EmptyText text="暂无搜索记录" />}
      </section>

      <section className="surface-card h-fit overflow-hidden">
        <SectionTitle title="常搜内容" />
        {topQueries.length ? topQueries.map((item) => (
          <div key={item.label} className="flex items-center justify-between gap-3 border-b border-border/70 px-4 py-3 text-sm last:border-0">
            <span className="min-w-0 truncate">{item.label}</span>
            <Badge variant="outline">{item.count}</Badge>
          </div>
        )) : <EmptyText text="暂无高频搜索" />}
      </section>
    </div>
  );
}

function BehaviorSection({ rows }: { rows: SearchInteractionItem[] }) {
  return (
    <section className="surface-card overflow-hidden">
      <SectionTitle title="搜索、猜你喜欢与 Agent 的素材行为" />
      {rows.length ? rows.map((row) => (
        <div
          key={row.id}
          className="grid gap-2 border-b border-border/70 px-5 py-4 text-sm last:border-0 md:grid-cols-[160px_160px_150px_minmax(220px,1fr)_120px]"
        >
          <time className="text-xs text-muted-foreground">{formatTime(row.createdAt)}</time>
          <UserCell username={row.actorUsername} role={row.actorRole} />
          <Badge variant="outline" className="h-fit w-fit">{interactionLabels[row.action] ?? row.action}</Badge>
          <span className="min-w-0 truncate">
            {row.source === 'agent_chat'
              ? 'Agent 推荐'
              : row.source === 'home_for_you'
              ? '猜你喜欢'
              : row.keyword || '—'}
          </span>
          {row.resultImageId ? (
            <Link className="text-xs font-medium text-foreground underline-offset-4 hover:underline" to={`/image/${row.resultImageId}`}>
              查看图片{row.position ? ` · 第 ${row.position} 位` : ''}
            </Link>
          ) : <span className="text-xs text-muted-foreground">—</span>}
        </div>
      )) : <EmptyText text="暂无搜索后行为记录" />}
    </section>
  );
}

function FeedbackSection({ rows }: { rows: SearchFeedbackItem[] }) {
  return (
    <section className="surface-card overflow-hidden">
      <SectionTitle title="满意度与改进意见" />
      {rows.length ? rows.map((row) => {
        const positive = row.feedbackType === 'relevant';
        return (
          <div
            key={row.id}
            className="grid gap-2 border-b border-border/70 px-5 py-4 text-sm last:border-0 lg:grid-cols-[160px_150px_110px_minmax(180px,0.9fr)_minmax(240px,1.4fr)]"
          >
            <time className="text-xs text-muted-foreground">{formatTime(row.createdAt)}</time>
            <UserCell username={row.actorUsername} role={row.actorRole} />
            <Badge variant={positive ? 'secondary' : 'outline'} className="h-fit w-fit">
              {positive && <CheckCircle2 className="mr-1 size-3" />}
              {feedbackLabels[row.feedbackType] ?? row.feedbackType}
            </Badge>
            <span className="min-w-0 truncate font-medium">{row.keyword}</span>
            <span className="text-muted-foreground">{row.note || '未填写改进意见'}</span>
          </div>
        );
      }) : <EmptyText text="暂无用户反馈" />}
    </section>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <h2 className="border-b border-border bg-secondary/30 px-5 py-3 text-sm font-semibold">{title}</h2>;
}

function UserCell({ username, role }: { username?: string | null; role?: string | null }) {
  return (
    <div className="min-w-0">
      <p className="truncate font-medium">{username || '未知用户'}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">{role ? roleLabels[role] ?? role : '—'}</p>
    </div>
  );
}

function EmptyText({ text }: { text: string }) {
  return <div className="grid min-h-32 place-items-center text-sm text-muted-foreground">{text}</div>;
}

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN');
}
