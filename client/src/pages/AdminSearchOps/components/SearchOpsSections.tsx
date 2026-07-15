import { Link } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  Brain,
  Search,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';

import { Badge } from '@client/src/components/ui/badge';
import type {
  AiConceptReviewQueueItem,
  AssetGapItem,
  ConceptHealthItem,
  SearchFeedbackItem,
  SearchLogItem,
  SearchMetricItem,
  SearchOpsIssue,
  SearchOpsSummary,
} from '@client/src/types/api';

export const FEEDBACK_LABELS: Record<string, string> = {
  not_relevant: '结果不相关',
  too_few_results: '结果太少',
  need_different_style: '想要别的风格',
  asset_request: '素材需求',
};

const ISSUE_LABELS: Record<string, string> = {
  zero_result: '空结果',
  search_fallback: '搜索降级',
  irrelevant_results: '结果不相关',
  too_few_results: '结果太少',
  style_gap: '风格缺口',
  asset_request: '素材需求',
};

const HEALTH_LABELS: Record<string, string> = {
  healthy: '健康',
  needs_assets: '缺素材',
  needs_review: '待审核',
  watch: '观察',
};

const severityClass: Record<string, string> = {
  high: 'border-red-200 bg-red-50 text-red-700',
  medium: 'border-amber-200 bg-amber-50 text-amber-700',
  low: 'border-slate-200 bg-slate-50 text-slate-600',
};

const healthClass: Record<string, string> = {
  healthy: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  needs_assets: 'border-red-200 bg-red-50 text-red-700',
  needs_review: 'border-amber-200 bg-amber-50 text-amber-700',
  watch: 'border-blue-200 bg-blue-50 text-blue-700',
};

export function MetricCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number;
  icon: typeof Activity;
}) {
  return (
    <div className="surface-card p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm text-muted-foreground">{label}</span>
        <Icon className="size-4 text-primary" />
      </div>
      <div className="mt-2 text-2xl font-semibold text-foreground">{value}</div>
    </div>
  );
}

export function MetricList({
  title,
  items,
  emptyText,
}: {
  title: string;
  items: SearchMetricItem[];
  emptyText: string;
}) {
  return (
    <section className="surface-card overflow-hidden">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      </div>
      <div className="divide-y divide-border">
        {items.length ? (
          items.map((item) => (
            <div key={item.label} className="flex items-center justify-between gap-3 px-4 py-3">
              <span className="min-w-0 truncate text-sm text-foreground">{item.label}</span>
              <Badge variant="outline" className="shrink-0">
                {item.count}
              </Badge>
            </div>
          ))
        ) : (
          <p className="px-4 py-5 text-sm text-muted-foreground">{emptyText}</p>
        )}
      </div>
    </section>
  );
}

export function OverviewSection({ data }: { data: SearchOpsSummary }) {
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard label="总搜索" value={data.totalSearches} icon={Search} />
        <MetricCard label="空结果" value={data.zeroResultCount} icon={AlertCircle} />
        <MetricCard label="降级次数" value={data.fallbackCount} icon={ShieldAlert} />
        <MetricCard label="超时次数" value={data.timedOutCount} icon={ShieldAlert} />
        <MetricCard label="P95 耗时(ms)" value={data.p95DurationMs} icon={Activity} />
        <MetricCard label="缓存命中" value={data.cacheHitCount} icon={Activity} />
        <MetricCard label="Reranker 使用" value={data.rerankerUsedCount} icon={Sparkles} />
        <MetricCard label="AI理解" value={data.aiUnderstoodCount} icon={Brain} />
        <MetricCard label="用户反馈" value={data.feedbackCount} icon={Activity} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <MetricList title="高频搜索词" items={data.topQueries} emptyText="暂无搜索词。" />
        <MetricList title="高频空结果" items={data.zeroResultQueries} emptyText="暂未发现空结果搜索。" />
        <MetricList title="AI归一意图" items={data.topNormalizedQueries} emptyText="暂无 AI 意图归一记录。" />
        <MetricList title="命中业务概念" items={data.topMatchedConcepts} emptyText="暂无业务概念命中记录。" />
        <MetricList
          title="反馈类型"
          items={data.feedbackByType.map((item) => ({
            ...item,
            label: FEEDBACK_LABELS[item.label] ?? item.label,
          }))}
          emptyText="暂无业务方反馈。"
        />
        <MetricList title="反馈搜索词" items={data.feedbackQueries} emptyText="暂无反馈关联搜索词。" />
      </div>
    </>
  );
}

export function IssuesSection({ issues }: { issues: SearchOpsIssue[] }) {
  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader title="搜索问题队列" description="从空结果、降级和用户反馈中自动归因出的待处理事项。" />
      {issues.length ? (
        <div className="divide-y divide-border">
          {issues.map((issue) => (
            <div key={issue.id} className="grid gap-3 px-4 py-3 text-sm lg:grid-cols-[120px_1fr_110px]">
              <Badge variant="outline" className={`w-fit ${severityClass[issue.severity]}`}>
                {ISSUE_LABELS[issue.issueType] ?? issue.issueType}
              </Badge>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-foreground">{issue.keyword}</span>
                  <Badge variant="outline" className="text-[11px]">
                    {issue.count} 次
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{issue.reason}</p>
                <p className="mt-1 text-xs text-foreground">{issue.suggestedAction}</p>
              </div>
              <time className="text-xs text-muted-foreground">
                {new Date(issue.latestAt).toLocaleString('zh-CN')}
              </time>
            </div>
          ))}
        </div>
      ) : (
        <EmptyText text="暂无需要处理的搜索问题。" />
      )}
    </section>
  );
}

export function ReviewQueueSection({ items }: { items: AiConceptReviewQueueItem[] }) {
  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader title="AI 概念关系审核池" description="在素材详情中确认主要表达、可以支持或排除关系。" />
      {items.length ? (
        <div className="divide-y divide-border">
          {items.map((item) => (
            <div key={item.id} className="grid gap-3 px-4 py-3 text-sm lg:grid-cols-[72px_1fr_130px]">
              <img
                src={item.thumbnailUrl}
                alt={item.imageTitle}
                className="aspect-square w-16 border border-border object-cover"
              />
              <div className="min-w-0">
                <Link to={`/image/${item.imageId}`} className="font-medium text-foreground hover:text-primary">
                  {item.imageTitle}
                </Link>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  <Badge variant="outline">{item.conceptName}</Badge>
                  <Badge variant="outline">{item.relationRole}</Badge>
                  {item.systemNames.map((name) => <Badge key={name} variant="outline">{name}</Badge>)}
                </div>
                {item.reason && <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">{item.reason}</p>}
              </div>
              <div className="text-xs text-muted-foreground">
                <div className="font-medium text-foreground">
                  {typeof item.confidence === 'number' ? `${Math.round(item.confidence * 100)}%` : '未给置信度'}
                </div>
                <time>{new Date(item.createdAt).toLocaleString('zh-CN')}</time>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyText text="暂无待审核 AI 概念关系。" />
      )}
    </section>
  );
}

export function ConceptHealthSection({ items }: { items: ConceptHealthItem[] }) {
  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader title="业务概念健康度" description="按素材供给、搜索需求和 AI 审核压力判断概念治理优先级。" />
      {items.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-sm">
            <thead className="border-b border-border bg-muted/40 text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">业务概念</th>
                <th className="px-4 py-3 font-medium">状态</th>
                <th className="px-4 py-3 font-medium">素材</th>
                <th className="px-4 py-3 font-medium">人工</th>
                <th className="px-4 py-3 font-medium">AI待审</th>
                <th className="px-4 py-3 font-medium">AI采纳/拒绝</th>
                <th className="px-4 py-3 font-medium">搜索</th>
                <th className="px-4 py-3 font-medium">建议</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((item) => (
                <tr key={item.conceptId}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-foreground">{item.conceptName}</div>
                    <div className="text-xs text-muted-foreground">{item.systemNames.join('、') || item.conceptCode}</div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="outline" className={healthClass[item.healthLevel]}>
                      {HEALTH_LABELS[item.healthLevel]}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">{item.imageCount}</td>
                  <td className="px-4 py-3">{item.manualCount}</td>
                  <td className="px-4 py-3">{item.aiPendingCount}</td>
                  <td className="px-4 py-3">{item.aiAcceptedCount} / {item.aiRejectedCount}</td>
                  <td className="px-4 py-3">{item.searchCount}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{item.recommendation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyText text="暂无业务概念健康数据。" />
      )}
    </section>
  );
}

export function AssetGapsSection({ items }: { items: AssetGapItem[] }) {
  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader title="素材需求地图" description="把高频空结果、结果太少和业务方素材需求合并成补图优先级。" />
      {items.length ? (
        <div className="divide-y divide-border">
          {items.map((item) => (
            <div key={`${item.keyword}-${item.source}`} className="grid gap-3 px-4 py-3 text-sm lg:grid-cols-[1fr_160px_90px]">
              <div className="min-w-0">
                <div className="font-medium text-foreground">{item.keyword}</div>
                <p className="mt-1 text-xs text-muted-foreground">{item.reason}</p>
              </div>
              <div className="text-xs text-muted-foreground">
                {item.suggestedConcept || '待管理员归类'}
              </div>
              <Badge variant="outline" className="h-fit w-fit">
                <Sparkles className="mr-1 size-3" />
                {item.demandCount}
              </Badge>
            </div>
          ))}
        </div>
      ) : (
        <EmptyText text="暂无明显素材缺口。" />
      )}
    </section>
  );
}

export function FeedbackSection({
  feedback,
  logs,
}: {
  feedback: SearchFeedbackItem[];
  logs: SearchLogItem[];
}) {
  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <section className="surface-card overflow-hidden">
        <SectionHeader title="最近反馈" />
        {feedback.length ? (
          <div className="divide-y divide-border">
            {feedback.map((item) => (
              <div key={item.id} className="grid gap-3 px-4 py-3 text-sm lg:grid-cols-[150px_140px_1fr]">
                <time className="text-xs text-muted-foreground">{new Date(item.createdAt).toLocaleString('zh-CN')}</time>
                <Badge variant="outline" className="w-fit">
                  {FEEDBACK_LABELS[item.feedbackType] ?? item.feedbackType}
                </Badge>
                <div className="min-w-0">
                  <div className="truncate font-medium text-foreground">{item.keyword}</div>
                  {item.note && <p className="mt-1 text-xs text-muted-foreground">{item.note}</p>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyText text="暂无反馈记录。" />
        )}
      </section>

      <section className="surface-card overflow-hidden">
        <SectionHeader title="最近搜索" />
        {logs.length ? (
          <div className="divide-y divide-border">
            {logs.map((log) => (
              <div key={log.id} className="grid gap-3 px-4 py-3 text-sm lg:grid-cols-[150px_1fr_90px]">
                <time className="text-xs text-muted-foreground">{new Date(log.createdAt).toLocaleString('zh-CN')}</time>
                <div className="min-w-0">
                  <div className="truncate font-medium text-foreground">{log.keyword}</div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {log.normalizedQuery && <Badge variant="outline" className="text-[11px]">{log.normalizedQuery}</Badge>}
                    {log.matchedConcept && <Badge variant="outline" className="text-[11px]">{log.matchedConcept}</Badge>}
                    {log.fallback && <Badge variant="outline" className="border-amber-200 bg-amber-50 text-[11px] text-amber-700">已降级</Badge>}
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">结果 {log.resultCount}</span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyText text="暂无搜索记录。" />
        )}
      </section>
    </div>
  );
}

function SectionHeader({ title, description }: { title: string; description?: string }) {
  return (
    <div className="border-b border-border px-4 py-3">
      <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      {description && <p className="mt-1 text-xs text-muted-foreground">{description}</p>}
    </div>
  );
}

function EmptyText({ text }: { text: string }) {
  return <p className="px-4 py-5 text-sm text-muted-foreground">{text}</p>;
}
