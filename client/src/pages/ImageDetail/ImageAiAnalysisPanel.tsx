import { Loader2, RefreshCw } from 'lucide-react';

import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { CanRole } from '@client/src/lib/auth';
import type { useProviderStatus } from '@client/src/features/ai/useProviderStatus';
import type { useImageDetailActions } from '@client/src/features/images/useImageDetailActions';
import type { ContentTag, ImageDetail } from '@client/src/types/api';

type ImageDetailActions = ReturnType<typeof useImageDetailActions>;
type ProviderStatusQuery = ReturnType<typeof useProviderStatus>;

const ProfileTagGroup = ({ title, items, danger = false }: { title: string; items: string[]; danger?: boolean }) => {
  if (!items.length) return null;
  return (
    <div className="space-y-1.5">
      <span className="text-[11px] font-medium text-muted-foreground">{title}</span>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <Badge
            key={item}
            variant="outline"
            className={danger ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-primary/20 bg-primary/5 text-primary/70'}
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
  const dimensions = new Map<string, ContentTag[]>();
  for (const tag of detail.contentTags) {
    const group = tag.dimension ?? '其他';
    dimensions.set(group, [...(dimensions.get(group) ?? []), tag]);
  }

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
          <p className="mt-0.5 text-[11px] text-muted-foreground">只负责画面事实、OCR、场景和检索表达；业务概念在下方由负责人确认</p>
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
          <p className="mt-1.5 rounded-lg border border-primary/10 bg-primary/5 px-3 py-2 text-sm leading-relaxed">{detail.imageSummary}</p>
        </div>
      )}

      {detail.semanticProfile && (
        <div className="mt-5 space-y-3 border-l border-primary/20 pl-3">
          <ProfileTagGroup title="画面事实" items={detail.semanticProfile.visualFacts ?? []} />
          <ProfileTagGroup title="OCR 文字" items={detail.semanticProfile.ocrText ?? []} />
          <ProfileTagGroup title="主体" items={detail.semanticProfile.subjects ?? []} />
          <ProfileTagGroup title="场景" items={detail.semanticProfile.scenes ?? []} />
          <ProfileTagGroup title="动作" items={detail.semanticProfile.actions ?? []} />
          <ProfileTagGroup title="视觉风格" items={detail.semanticProfile.visualStyle ?? []} />
          <ProfileTagGroup title="画面可见产品功能" items={detail.semanticProfile.visibleProductFeatures ?? []} />
          <ProfileTagGroup title="素材独有搜索表达" items={detail.semanticProfile.assetSearchPhrases ?? []} />
          <ProfileTagGroup title="画面排除边界" items={detail.semanticProfile.negativeVisualConcepts ?? []} danger />
        </div>
      )}

      <div className="mt-5">
        <span className="text-sm font-medium">客观内容标签</span>
        {dimensions.size ? (
          <div className="mt-2 space-y-2">
            {[...dimensions.entries()].map(([dimension, tags]) => (
              <div key={dimension} className="flex flex-wrap gap-1.5">
                <Badge variant="outline" className="text-[10px]">{dimension}</Badge>
                {tags.map((tag) => <Badge key={tag.id} variant="outline">{tag.tagName}</Badge>)}
              </div>
            ))}
          </div>
        ) : (
          <span className="mt-1 block text-xs text-muted-foreground">尚无分析结果</span>
        )}
      </div>
    </CanRole>
  );
};

export default ImageAiAnalysisPanel;
