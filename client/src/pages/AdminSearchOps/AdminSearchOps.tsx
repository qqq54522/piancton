import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { fetchSearchOpsSummary } from '@client/src/api/admin';
import { getApiError } from '@client/src/api/client';
import { Button } from '@client/src/components/ui/button';
import PageHeader from '@client/src/components/PageHeader';
import {
  AssetGapsSection,
  FeedbackSection,
  IssuesSection,
  ConceptHealthSection,
  OverviewSection,
  ReviewQueueSection,
} from './components/SearchOpsSections';

const dayOptions = [7, 30, 90] as const;

const tabs = [
  { id: 'overview', label: '总览' },
  { id: 'issues', label: '问题队列' },
  { id: 'review', label: 'AI 审核池' },
  { id: 'health', label: '概念健康度' },
  { id: 'gaps', label: '素材缺口' },
  { id: 'records', label: '反馈记录' },
] as const;

type TabId = (typeof tabs)[number]['id'];

export default function AdminSearchOps() {
  const [days, setDays] = useState<(typeof dayOptions)[number]>(7);
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const summary = useQuery({
    queryKey: ['search-ops-summary', days],
    queryFn: () => fetchSearchOpsSummary(days),
  });
  const data = summary.data;

  return (
    <div className="page-shell">
      <PageHeader
        eyebrow="Search Operations"
        title="搜索运营"
        description="从真实查询和业务反馈中发现搜索问题、待审核卖点关系与素材缺口。"
        actions={(
        <div className="inline-flex w-fit border border-border bg-card p-1">
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

      <div className="mt-7 flex flex-wrap gap-1 rounded-xl border border-border/80 bg-card p-1.5 shadow-sm">
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? 'default' : 'ghost'}
            size="sm"
            className=""
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {summary.isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">正在加载...</p>
      ) : summary.isError ? (
        <p className="mt-6 text-sm text-destructive">{getApiError(summary.error).message}</p>
      ) : data ? (
        <div className="mt-7">
          {activeTab === 'overview' && <OverviewSection data={data} />}
          {activeTab === 'issues' && <IssuesSection issues={data.searchIssues} />}
          {activeTab === 'review' && <ReviewQueueSection items={data.aiReviewQueue} />}
          {activeTab === 'health' && <ConceptHealthSection items={data.conceptHealth} />}
          {activeTab === 'gaps' && <AssetGapsSection items={data.assetGaps} />}
          {activeTab === 'records' && (
            <FeedbackSection feedback={data.recentFeedback} logs={data.recentLogs} />
          )}
        </div>
      ) : null}
    </div>
  );
}
