import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { fetchSearchOpsSummary } from '@client/src/api/admin';
import { getApiError } from '@client/src/api/client';
import { Button } from '@client/src/components/ui/button';
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
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">搜索运营</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            管理员用于治理搜索质量、AI 概念关系、概念健康度和素材缺口。
          </p>
        </div>
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
      </div>

      <div className="mt-5 flex flex-wrap gap-2 border-b border-border">
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? 'default' : 'ghost'}
            size="sm"
            className="mb-2"
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
        <div className="mt-6">
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
