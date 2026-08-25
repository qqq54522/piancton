import { Link } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  Brain,
  Clock,
  ExternalLink,
  FileText,
  Images,
  Link as LinkIcon,
  Search,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';

import { Badge } from '@client/src/components/ui/badge';
import type {
  AiConceptReviewQueueItem,
  AssetGapItem,
  AssetOperationsOverview,
  AssetOpsIssue,
  ConceptHealthItem,
  SearchFeedbackItem,
  SearchLogItem,
  SearchMetricItem,
  SearchOpsIssue,
  SearchOpsSummary,
  SearchPerformanceSummary,
  SourceLinkHealth,
} from '@client/src/types/api';

export const FEEDBACK_LABELS: Record<string, string> = {
  relevant: '就是这张',
  not_relevant: '结果不相关',
  too_few_results: '结果太少',
  need_different_style: '想要别的风格',
  right_business_wrong_visual: '卖点对画面不对',
  right_visual_wrong_business: '画面对卖点不对',
  wrong_version: '版本/尺寸不对',
  asset_request: '素材需求',
};

const ISSUE_LABELS: Record<string, string> = {
  zero_result: '空结果',
  search_fallback: '搜索降级',
  irrelevant_results: '结果不相关',
  too_few_results: '结果太少',
  style_gap: '风格缺口',
  visual_mismatch: '画面不合适',
  business_mismatch: '业务误召回',
  wrong_version: '版本不对',
  asset_request: '素材需求',
};

const HEALTH_LABELS: Record<string, string> = {
  healthy: '健康',
  needs_assets: '缺素材',
  needs_review: '待审核',
  watch: '观察',
};

const ASSET_ISSUE_LABELS: Record<string, string> = {
  missing_source_link: '缺源文件',
  missing_business_relation: '缺业务关系',
  missing_search_phrase: '缺搜索话术',
  single_version: '单版本',
  missing_style: '缺风格',
  unused_asset: '未使用',
  stale_unused_asset: '长期未用',
  large_gif: '大 GIF',
  possible_duplicate: '疑似重复',
  possible_visual_duplicate: '画面近似',
  stale_source_link: '源文件待复查',
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
  description,
  items,
  emptyText,
}: {
  title: string;
  description?: string;
  items: SearchMetricItem[];
  emptyText: string;
}) {
  return (
    <section className="surface-card overflow-hidden">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        {description && (
          <p className="mt-1 text-xs leading-5 text-muted-foreground">{description}</p>
        )}
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
        <MetricList
          title="用户真实想搜什么"
          description="系统把用户原话理解成内部搜索意图，用来判断大家真实需求集中在哪里。"
          items={data.topNormalizedQueries}
          emptyText="暂无搜索意图记录。"
        />
        <MetricList
          title="命中的标准卖点"
          description="统计搜索最终落到哪些标准卖点，用来判断哪些卖点被业务方用得最多。"
          items={data.topMatchedConcepts}
          emptyText="暂无标准卖点命中记录。"
        />
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

export function GovernanceSection({ data }: { data: SearchOpsSummary }) {
  const rows = governanceRows(data);
  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader
        title="项目治理"
        description="把素材库长期会变乱的风险收敛成固定巡检项。"
      />
      <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">
        {rows.map((row) => (
          <div key={row.title} className="rounded-xl border border-border/80 bg-card p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground">{row.title}</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">{row.description}</p>
              </div>
              <Badge variant="outline" className={healthClass[row.level]}>
                {HEALTH_LABELS[row.level]}
              </Badge>
            </div>
            <div className="mt-3 flex items-end gap-2">
              <span className="text-2xl font-semibold text-foreground">{row.value}</span>
              <span className="pb-1 text-xs text-muted-foreground">{row.unit}</span>
            </div>
            <p className="mt-3 text-xs leading-5 text-foreground">{row.action}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export function IssuesSection({ issues }: { issues: SearchOpsIssue[] }) {
  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader
        title="待处理问题"
        description="把空结果、搜索降级和用户反馈自动整理成待办：该补素材、补搜索话术，还是修卖点关系。"
      />
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
      <SectionHeader
        title="AI 待审核"
        description="AI 对图片可能表达的卖点关系只放进待审核池；确认后才会影响搜索。"
      />
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

export function AssetOperationsSection({
  overview,
  issues,
}: {
  overview: AssetOperationsOverview;
  issues: AssetOpsIssue[];
}) {
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard label="素材组" value={overview.assetGroupCount} icon={Images} />
        <MetricCard label="图片文件" value={overview.imageCount} icon={Images} />
        <MetricCard label="缺源文件" value={overview.missingSourceLinkCount} icon={FileText} />
        <MetricCard label="单版本素材" value={overview.singleVersionGroupCount} icon={AlertCircle} />
        <MetricCard label="总下载" value={overview.totalDownloadCount} icon={Activity} />
        <MetricCard label="缺业务关系" value={overview.missingBusinessRelationCount} icon={Brain} />
        <MetricCard label="缺搜索话术" value={overview.missingSearchPhraseCount} icon={Search} />
        <MetricCard label="缺风格" value={overview.missingStyleCount} icon={Sparkles} />
        <MetricCard label="未定场景" value={overview.unsetSceneCount} icon={Images} />
        <MetricCard label="未使用素材" value={overview.unusedAssetGroupCount} icon={Activity} />
      </div>

      <section className="surface-card mt-6 overflow-hidden">
        <SectionHeader title="素材运营问题" description="按源文件、业务关系、搜索话术和版本完整度整理。" />
        {issues.length ? (
          <div className="divide-y divide-border">
            {issues.map((issue) => (
              <div key={issue.id} className="grid gap-3 px-4 py-3 text-sm lg:grid-cols-[130px_1fr_120px]">
                <Badge variant="outline" className={`w-fit ${severityClass[issue.severity]}`}>
                  {ASSET_ISSUE_LABELS[issue.issueType] ?? issue.issueType}
                </Badge>
                <div className="min-w-0">
                  {issue.primaryImageId ? (
                    <Link
                      to={`/image/${issue.primaryImageId}`}
                      className="font-medium text-foreground hover:text-primary"
                    >
                      {issue.title}
                    </Link>
                  ) : (
                    <span className="font-medium text-foreground">{issue.title}</span>
                  )}
                  <p className="mt-1 text-xs text-muted-foreground">{issue.message}</p>
                  <p className="mt-1 text-xs text-foreground">{issue.suggestedAction}</p>
                </div>
                <time className="text-xs text-muted-foreground">
                  {new Date(issue.updatedAt).toLocaleDateString('zh-CN')}
                </time>
              </div>
            ))}
          </div>
        ) : (
          <EmptyText text="素材资产目前没有明显缺口。" />
        )}
      </section>
    </>
  );
}

export function SourceLinkHealthSection({ data }: { data: SourceLinkHealth }) {
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="源文件链接" value={data.totalLinks} icon={FileText} />
        <MetricCard label="已记录素材" value={data.groupsWithSourceLinks} icon={LinkIcon} />
        <MetricCard label="未记录素材" value={data.groupsWithoutSourceLinks} icon={AlertCircle} />
        <MetricCard label="待复查链接" value={data.staleLinkCount} icon={AlertCircle} />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[360px_1fr]">
        <MetricList title="源文件类型" items={data.linkTypeCounts} emptyText="暂无源文件链接。" />

        <section className="surface-card overflow-hidden">
          <SectionHeader title="最近源文件" />
          {data.recentLinks.length ? (
            <div className="divide-y divide-border">
              {data.recentLinks.map((item) => (
                <div key={item.id} className="grid gap-3 px-4 py-3 text-sm lg:grid-cols-[1fr_100px_120px]">
                  <div className="min-w-0">
                    {item.primaryImageId ? (
                      <Link to={`/image/${item.primaryImageId}`} className="font-medium text-foreground hover:text-primary">
                        {item.assetGroupTitle}
                      </Link>
                    ) : (
                      <span className="font-medium text-foreground">{item.assetGroupTitle}</span>
                    )}
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 flex min-w-0 items-center gap-1 text-xs text-primary hover:underline"
                    >
                      <span className="truncate">{item.label}</span>
                      <ExternalLink className="size-3 shrink-0" />
                    </a>
                  </div>
                  <Badge variant="outline" className="h-fit w-fit">{item.linkType}</Badge>
                  <div className="space-y-1 text-xs text-muted-foreground">
                    {item.reviewStatus === 'stale' && (
                      <Badge variant="outline" className="border-amber-200 bg-amber-50 text-[11px] text-amber-700">
                        待复查
                      </Badge>
                    )}
                    <time className="block">
                      {new Date(item.updatedAt).toLocaleDateString('zh-CN')}
                    </time>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyText text="暂无最近源文件记录。" />
          )}
        </section>
      </div>
    </>
  );
}

export function SearchPerformanceSection({ data }: { data: SearchPerformanceSummary }) {
  const cacheRate = Math.round(data.cacheHitRate * 100);
  const slowRate = Math.round(data.slowSearchRate * 100);
  const modelWorkRate = Math.round(data.modelWorkUnitRate * 100);
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard label="样本数" value={data.sampleCount} icon={Search} />
        <MetricCard label="P50(ms)" value={data.p50DurationMs} icon={Clock} />
        <MetricCard label="P95(ms)" value={data.p95DurationMs} icon={Activity} />
        <MetricCard label="P99(ms)" value={data.p99DurationMs} icon={ShieldAlert} />
        <MetricCard label="慢查询" value={data.slowSearchCount} icon={AlertCircle} />
        <MetricCard label="慢查询占比%" value={slowRate} icon={AlertCircle} />
        <MetricCard label="缓存命中%" value={cacheRate} icon={Activity} />
        <MetricCard label="降级" value={data.fallbackCount} icon={ShieldAlert} />
        <MetricCard label="超时" value={data.timeoutCount} icon={ShieldAlert} />
        <MetricCard label="AI理解" value={data.aiUnderstoodCount} icon={Brain} />
        <MetricCard label="模型工作量" value={data.modelWorkUnitCount} icon={Brain} />
        <MetricCard label="工作量/搜索%" value={modelWorkRate} icon={Activity} />
      </div>

      <section className="surface-card mt-6 overflow-hidden">
        <SectionHeader title="最近慢查询" description="按 3 秒以上的真实搜索记录整理。" />
        {data.recentSlowLogs.length ? (
          <div className="divide-y divide-border">
            {data.recentSlowLogs.map((log) => (
              <div key={log.id} className="grid gap-3 px-4 py-3 text-sm lg:grid-cols-[150px_1fr_110px]">
                <time className="text-xs text-muted-foreground">{new Date(log.createdAt).toLocaleString('zh-CN')}</time>
                <div className="min-w-0">
                  <div className="truncate font-medium text-foreground">{log.keyword}</div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {log.normalizedQuery && <Badge variant="outline" className="text-[11px]">{log.normalizedQuery}</Badge>}
                    {log.queryType && <Badge variant="outline" className="text-[11px]">{log.queryType}</Badge>}
                    {log.cacheHit && <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-[11px] text-emerald-700">缓存</Badge>}
                    {log.fallback && <Badge variant="outline" className="border-amber-200 bg-amber-50 text-[11px] text-amber-700">降级</Badge>}
                    {log.timedOut && <Badge variant="outline" className="border-red-200 bg-red-50 text-[11px] text-red-700">超时</Badge>}
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">{log.durationMs ?? 0} ms</span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyText text="当前时间范围内没有慢查询。" />
        )}
      </section>
    </>
  );
}

export function FeedbackArchiveSection({ feedback }: { feedback: SearchFeedbackItem[] }) {
  const rows = feedbackArchiveRows(feedback);
  return (
    <section className="surface-card overflow-hidden">
      <SectionHeader
        title="反馈归档"
        description="把业务反馈先归到待沉淀池，再由设计或运营确认是否补话术、补图或修关系。"
      />
      {rows.length ? (
        <div className="divide-y divide-border">
          {rows.map((row) => (
            <div key={row.key} className="grid gap-3 px-4 py-3 text-sm lg:grid-cols-[150px_1fr_120px]">
              <Badge variant="outline" className={`h-fit w-fit ${severityClass[row.severity]}`}>
                {row.label}
              </Badge>
              <div className="min-w-0">
                <p className="font-medium text-foreground">{row.action}</p>
                <p className="mt-1 text-xs text-muted-foreground">{row.description}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {row.examples.map((keyword) => (
                    <Badge key={keyword} variant="outline" className="max-w-[220px] truncate text-[11px]">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>
              <Badge variant="outline" className="h-fit w-fit">{row.count} 条</Badge>
            </div>
          ))}
        </div>
      ) : (
        <EmptyText text="暂无需要归档处理的反馈。" />
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

type GovernanceLevel = keyof typeof HEALTH_LABELS;

interface GovernanceRow {
  title: string;
  description: string;
  value: number;
  unit: string;
  level: GovernanceLevel;
  action: string;
}

function governanceRows(data: SearchOpsSummary): GovernanceRow[] {
  const asset = data.assetOperations;
  const performance = data.searchPerformance;
  const issueCount = (type: string) => data.assetOpsIssues.filter((item) => item.issueType === type).length;
  const feedbackCount = (type: string) => data.feedbackByType.find((item) => item.label === type)?.count ?? 0;
  const percent = (value: number) => Math.round(value * 100);
  const duplicateIssueCount = issueCount('possible_duplicate') + issueCount('possible_visual_duplicate');
  const lifecycleIssueCount = issueCount('stale_unused_asset') + asset.unusedAssetGroupCount;
  return [
    {
      title: 'GIF / 动图体积',
      description: '动图预览已保留动画，但大 GIF 会拖慢首页。',
      value: issueCount('large_gif'),
      unit: '个风险素材',
      level: issueCount('large_gif') > 0 ? 'watch' : 'healthy',
      action: '大 GIF 出现时优先压缩，或补一张静态替代图。',
    },
    {
      title: '源文件链接健康',
      description: '设计师改图时必须能找到 Figma、网盘或源文件包，并定期复查。',
      value: asset.missingSourceLinkCount + data.sourceLinkHealth.staleLinkCount,
      unit: `个缺口，覆盖率 ${100 - percent(asset.missingSourceLinkRate)}%`,
      level: asset.missingSourceLinkCount + data.sourceLinkHealth.staleLinkCount > 0 ? 'needs_review' : 'healthy',
      action: '先补缺失链接，再复查太久没更新的源文件入口。',
    },
    {
      title: '权限分层',
      description: '业务端不展示源文件，设计师和管理员可维护。',
      value: data.sourceLinkHealth.totalLinks,
      unit: '条源文件受控记录',
      level: 'healthy',
      action: '继续保持源文件只在设计/管理侧出现。',
    },
    {
      title: '搜索满意度闭环',
      description: '反馈已细分到画面、业务、版本、数量和素材需求。',
      value: data.feedbackCount,
      unit: '条反馈',
      level: data.feedbackCount > 0 ? 'watch' : 'healthy',
      action: '优先处理“画面对卖点不对”和“结果不相关”。',
    },
    {
      title: '重复素材治理',
      description: '按文件指纹和画面近似识别疑似重复上传。',
      value: duplicateIssueCount,
      unit: '个疑似重复',
      level: duplicateIssueCount > 0 ? 'needs_review' : 'healthy',
      action: '确认是否合并为同组版本，减少素材库噪音。',
    },
    {
      title: '素材生命周期',
      description: '用下载量、更新时间和版本状态识别未使用或待归档素材。',
      value: lifecycleIssueCount,
      unit: '个生命周期信号',
      level: lifecycleIssueCount > 0 ? 'watch' : 'healthy',
      action: '判断是等待曝光、需要改名补话术，还是应该下架。',
    },
    {
      title: '上传质量门槛',
      description: '缺渠道、缺风格、缺场景、缺业务关系都会进入问题队列。',
      value: asset.missingChannelCount + asset.missingStyleCount + asset.unsetSceneCount,
      unit: '个质量缺口',
      level: asset.missingChannelCount + asset.missingStyleCount + asset.unsetSceneCount > 0 ? 'needs_review' : 'healthy',
      action: '上传时先补渠道；上线前补齐风格、场景和业务关系。',
    },
    {
      title: '搜索成本和速度',
      description: '模型速度、工作量、缓存命中、降级和超时已经按真实搜索记录。',
      value: performance.modelWorkUnitCount,
      unit: `个模型工作单元，P95 ${performance.p95DurationMs}ms`,
      level: performance.p95DurationMs >= 6000 ? 'needs_review' : performance.p95DurationMs >= 3000 ? 'watch' : 'healthy',
      action: '慢查询优先看模型理解链路和候选复核是否超预算。',
    },
    {
      title: '备份恢复',
      description: '本地脚本会同时备份 SQLite 数据库、图片文件和 manifest。',
      value: 1,
      unit: '个备份脚本',
      level: 'healthy',
      action: '定期运行 backup_local_assets.py，并演练恢复。',
    },
    {
      title: '导出能力',
      description: '素材可按单组或项目夹批量导出，业务导出不包含源文件。',
      value: feedbackCount('wrong_version'),
      unit: '条版本反馈',
      level: feedbackCount('wrong_version') > 0 ? 'watch' : 'healthy',
      action: '版本反馈增多时，用项目夹收集候选后一并导出给设计师检查。',
    },
  ];
}

interface FeedbackArchiveRow {
  key: string;
  label: string;
  count: number;
  severity: 'high' | 'medium' | 'low';
  action: string;
  description: string;
  examples: string[];
}

function feedbackArchiveRows(feedback: SearchFeedbackItem[]): FeedbackArchiveRow[] {
  const groups: Record<string, FeedbackArchiveRow> = {
    relationship: {
      key: 'relationship',
      label: '修业务关系',
      count: 0,
      severity: 'high',
      action: '检查素材和卖点关系',
      description: '画面对但卖点不对，通常说明关系误标或召回边界需要收紧。',
      examples: [],
    },
    phrase: {
      key: 'phrase',
      label: '补搜索话术',
      count: 0,
      severity: 'medium',
      action: '把业务方真实说法沉淀成待审核话术',
      description: '结果少或不相关时，先看是否缺少业务方实际搜索表达。',
      examples: [],
    },
    version: {
      key: 'version',
      label: '补版本尺寸',
      count: 0,
      severity: 'medium',
      action: '补齐对应渠道或尺寸版本',
      description: '卖点和画面方向正确但版本不对，适合进入设计生产队列。',
      examples: [],
    },
    asset: {
      key: 'asset',
      label: '补素材',
      count: 0,
      severity: 'high',
      action: '整理为补图需求',
      description: '业务方明确要素材或反馈结果太少，应进入素材需求地图。',
      examples: [],
    },
    visual: {
      key: 'visual',
      label: '补画面表达',
      count: 0,
      severity: 'medium',
      action: '补更贴合的视觉表达或风格',
      description: '卖点对但画面不合适，说明现有图不能承接这个使用语境。',
      examples: [],
    },
  };
  for (const item of feedback) {
    const row = archiveRowForFeedback(item.feedbackType, groups);
    if (!row) continue;
    row.count += 1;
    if (item.keyword && !row.examples.includes(item.keyword)) {
      row.examples.push(item.keyword);
    }
  }
  return Object.values(groups)
    .filter((row) => row.count > 0)
    .map((row) => ({ ...row, examples: row.examples.slice(0, 6) }))
    .sort((a, b) => b.count - a.count);
}

function archiveRowForFeedback(
  type: string,
  groups: Record<string, FeedbackArchiveRow>,
): FeedbackArchiveRow | null {
  if (type === 'right_visual_wrong_business' || type === 'not_relevant') return groups.relationship;
  if (type === 'too_few_results') return groups.phrase;
  if (type === 'wrong_version') return groups.version;
  if (type === 'asset_request') return groups.asset;
  if (type === 'right_business_wrong_visual' || type === 'need_different_style') return groups.visual;
  return null;
}
