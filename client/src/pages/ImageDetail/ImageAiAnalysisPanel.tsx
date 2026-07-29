import { Loader2, RefreshCw } from 'lucide-react';

import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { CanRole } from '@client/src/lib/auth';
import type { useProviderStatus } from '@client/src/features/ai/useProviderStatus';
import type { useImageDetailActions } from '@client/src/features/images/useImageDetailActions';
import type { ImageDetail } from '@client/src/types/api';
import { visibleSemanticProfileGroups } from './semanticProfilePresentation';

type ImageDetailActions = ReturnType<typeof useImageDetailActions>;
type ProviderStatusQuery = ReturnType<typeof useProviderStatus>;

const ProfileTagGroup = ({ title, items }: { title: string; items: string[] }) => {
  if (!items.length) return null;
  return (
    <div className="space-y-1.5">
      <span className="text-[11px] font-medium text-muted-foreground">{title}</span>
      <div className="flex min-w-0 max-w-full flex-wrap gap-1.5 overflow-hidden">
        {items.map((item) => (
          <Badge
            key={item}
            variant="outline"
            className="max-w-full whitespace-normal break-words border-border bg-[#f7f7f5] text-left leading-5 text-foreground/70"
          >
            {item}
          </Badge>
        ))}
      </div>
    </div>
  );
};

const ImageAiAnalysisPanel = ({
  detail,
  provider,
  actions,
}: {
  detail: ImageDetail;
  provider: ProviderStatusQuery;
  actions: ImageDetailActions;
}) => {
  const latest = detail.analysisRuns[0];
  const active = latest?.status === 'queued' || latest?.status === 'running';
  const status = latest
    ? ({ queued: '排队中', running: '分析中', succeeded: '已完成', failed: '失败' } as const)[latest.status]
    : '未分析';
  const visibleGroups = detail.semanticProfile
    ? visibleSemanticProfileGroups(detail.semanticProfile)
    : [];
  // 页面只展示画面事实、场景和素材独有搜索表达；其余 V3 字段留在后端契约内。

  return (
    <CanRole roles={['designer']}>
      <div className="mt-5 flex items-center justify-between border-t pt-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">AI 画面分析</span>
            <Badge variant="outline" className="text-[11px]">
              {active && <Loader2 className="mr-1 size-3 animate-spin" />}{status}
            </Badge>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={!provider.data?.configured || actions.analyzing || active}
          onClick={() => actions.analyze()}
        >
          <RefreshCw className={`mr-1.5 size-3.5 ${actions.analyzing ? 'animate-spin' : ''}`} />
          {provider.data?.configured ? (active ? '后台分析中…' : '重新分析') : 'AI 未配置'}
        </Button>
      </div>

      {detail.imageSummary && (
        <div className="mt-5">
          <span className="text-sm font-medium">语义总结</span>
          <p className="mt-1.5 rounded-lg border border-border/80 bg-[#f7f7f5] px-3 py-2 text-sm leading-relaxed">{detail.imageSummary}</p>
        </div>
      )}

      {visibleGroups.length > 0 && (
        <div className="mt-5 min-w-0 space-y-3 overflow-x-hidden border-l border-border pl-3">
          {visibleGroups.map((group) => (
            <ProfileTagGroup key={group.key} title={group.title} items={group.items} />
          ))}
        </div>
      )}
    </CanRole>
  );
};

export default ImageAiAnalysisPanel;
