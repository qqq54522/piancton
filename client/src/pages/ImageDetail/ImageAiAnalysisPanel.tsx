import { Check, Loader2, RefreshCw, X } from 'lucide-react';

import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { CanRole } from '@client/src/lib/auth';
import type { useProviderStatus } from '@client/src/features/ai/useProviderStatus';
import type { useImageDetailActions } from '@client/src/features/images/useImageDetailActions';
import type {
  BusinessLabel,
  ContentTag,
  ImageDetail,
  Level2Category,
} from '@client/src/types/api';

type ImageDetailActions = ReturnType<typeof useImageDetailActions>;
type ProviderStatusQuery = ReturnType<typeof useProviderStatus>;

interface ImageAiAnalysisPanelProps {
  detail: ImageDetail;
  provider: ProviderStatusQuery;
  actions: ImageDetailActions;
}

const reviewStatusLabel = (label: BusinessLabel) => {
  if (label.reviewStatus === 'accepted') return '已接受';
  if (label.reviewStatus === 'rejected') return '已拒绝';
  return '待审核';
};

const ProfileTagGroup = ({
  title,
  items,
  tone = 'primary',
}: {
  title: string;
  items: string[];
  tone?: 'primary' | 'rose';
}) => {
  if (!items.length) return null;
  const toneClass = tone === 'rose'
    ? 'border-rose-200 bg-rose-50 text-rose-700'
    : 'border-primary/20 bg-primary/5 text-primary/70';
  return (
    <div className="space-y-1.5">
      <span className="text-[11px] font-medium text-muted-foreground">{title}</span>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <Badge
            key={item}
            variant="outline"
            className={`max-w-full cursor-default whitespace-normal text-left text-xs leading-relaxed ${toneClass}`}
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
}: ImageAiAnalysisPanelProps) => {
  const hasAiBusinessLabelRecords = detail.businessLabels.some((label) => label.origin === 'ai');
  const aiBusinessLabels = detail.businessLabels.filter(
    (label) => label.origin === 'ai' && label.reviewStatus !== 'rejected',
  );
  const latestAnalysisRun = detail.analysisRuns?.[0];
  const latestAnalysisActive =
    latestAnalysisRun?.status === 'queued' || latestAnalysisRun?.status === 'running';
  const analysisStatusText = latestAnalysisRun
    ? ({
        queued: '排队中',
        running: '分析中',
        succeeded: '已完成',
        failed: '失败',
      } as const)[latestAnalysisRun.status]
    : '未分析';
  const analysisStatusClass = latestAnalysisRun
    ? ({
        queued: 'border-amber-200 bg-amber-50 text-amber-700',
        running: 'border-blue-200 bg-blue-50 text-blue-700',
        succeeded: 'border-emerald-200 bg-emerald-50 text-emerald-700',
        failed: 'border-rose-200 bg-rose-50 text-rose-700',
      } as const)[latestAnalysisRun.status]
    : 'border-muted bg-muted text-muted-foreground';

  return (
    <CanRole roles={['designer']}>
      <div className="mt-5 flex items-center justify-between border-t border-border pt-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground">AI 分析</span>
            <Badge variant="outline" className={`text-[11px] ${analysisStatusClass}`}>
              {latestAnalysisActive && (
                <Loader2 className="mr-1 size-3 animate-spin" />
              )}
              {analysisStatusText}
            </Badge>
          </div>
          <p className="mt-0.5 text-[11px] text-muted-foreground">
            上传后自动分析；手动重跑会刷新自动匹配、语义总结和隐形内容标签
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={!provider.data?.configured || actions.analyzing || latestAnalysisActive}
          onClick={() => actions.analyze()}
          title={provider.data?.configured ? '重新执行完整 AI 分析' : 'AI Provider 尚未配置'}
        >
          <RefreshCw className={`mr-1.5 size-3.5 ${actions.analyzing ? 'animate-spin' : ''}`} />
          {provider.isLoading
            ? '检查模型…'
            : provider.data?.configured
            ? latestAnalysisActive ? '后台分析中…' : actions.analyzing ? '分析中…' : '重新分析'
            : 'AI 未配置'}
        </Button>
      </div>

      {detail.imageSummary && (
        <div className="mt-5">
          <span className="text-sm font-medium text-foreground">语义总结</span>
          <p className="mt-1.5 rounded-lg border border-primary/10 bg-primary/5 px-3 py-2 text-sm leading-relaxed text-foreground/80">
            {detail.imageSummary}
          </p>
        </div>
      )}

      {detail.semanticProfile && (
        <div className="mt-5">
          <span className="text-sm font-medium text-foreground">语义画像</span>
          <div className="mt-2 space-y-3 border-l border-primary/20 pl-3">
            {detail.semanticProfile.businessIntent && (
              <div>
                <span className="text-[11px] font-medium text-muted-foreground">业务意图</span>
                <p className="mt-1 text-sm text-foreground/80">
                  {detail.semanticProfile.businessIntent}
                </p>
              </div>
            )}
            <ProfileTagGroup title="画面事实" items={detail.semanticProfile.visualFacts ?? []} />
            <ProfileTagGroup title="适合搜索" items={detail.semanticProfile.searchPhrases ?? []} />
            <ProfileTagGroup
              title="排除边界"
              items={detail.semanticProfile.exclusionBoundaries ?? []}
              tone="rose"
            />
          </div>
        </div>
      )}

      <div className="mt-5">
        <span className="text-sm font-medium text-foreground">AI 自动匹配</span>
        <p className="mt-0.5 text-[11px] text-muted-foreground">
          来自封闭业务标签目录；接受后会追加为设计师附加标签，不覆盖主标签
        </p>
        {aiBusinessLabels.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-2">
            {aiBusinessLabels.map((label) => (
              <div
                key={label.id}
                className="inline-flex items-center gap-1 rounded-full border border-purple-200 bg-purple-50 px-2 py-1 text-xs text-purple-700"
                title={label.reason ?? ''}
              >
                {label.systemName ? `${label.systemName} > ${label.tagName}` : label.tagName}
                {label.confidence != null && (
                  <span className="ml-1 text-[10px] text-purple-400">
                    {Math.round(label.confidence * 100)}
                  </span>
                )}
                <span className="ml-1 rounded bg-purple-100 px-1 text-[10px] text-purple-500">
                  {reviewStatusLabel(label)}
                </span>
                {label.reviewStatus === 'pending' && (
                  <>
                    <button
                      type="button"
                      className="ml-1 rounded-full bg-emerald-100 p-0.5 text-emerald-700 hover:bg-emerald-200 disabled:opacity-50"
                      onClick={() => actions.reviewBusinessLabel({
                        labelId: label.id,
                        reviewStatus: 'accepted',
                      })}
                      disabled={actions.reviewingBusinessLabel}
                      title="接受并转为设计师附加标签"
                    >
                      <Check className="size-3" />
                    </button>
                    <button
                      type="button"
                      className="rounded-full bg-rose-100 p-0.5 text-rose-700 hover:bg-rose-200 disabled:opacity-50"
                      onClick={() => actions.reviewBusinessLabel({
                        labelId: label.id,
                        reviewStatus: 'rejected',
                      })}
                      disabled={actions.reviewingBusinessLabel}
                      title="拒绝这个 AI 建议"
                    >
                      <X className="size-3" />
                    </button>
                  </>
                )}
              </div>
            ))}
          </div>
        ) : !hasAiBusinessLabelRecords && detail.level2Categories && detail.level2Categories.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-2">
            {detail.level2Categories.map((category: Level2Category) => (
              <Badge
                key={category.id}
                variant="outline"
                className="cursor-default border-purple-200 bg-purple-50 text-xs text-purple-700"
                title={category.reason ?? ''}
              >
                {category.categoryName}
                <span className="ml-1 text-[10px] text-purple-400">
                  {Math.round(category.confidence * 100)}
                </span>
              </Badge>
            ))}
          </div>
        ) : (
          <span className="mt-1 block text-xs text-muted-foreground">
            暂无符合证据要求的自动匹配标签
          </span>
        )}
      </div>

      <div className="mt-5">
        <span className="text-sm font-medium text-foreground">隐形内容标签</span>
        <p className="mt-0.5 text-[11px] text-muted-foreground">
          约 20 个可检索的中文可见内容描述
        </p>
        {detail.contentTags && detail.contentTags.length > 0 ? (
          <div className="mt-2 space-y-2">
            {(() => {
              const dimensionGroups = new Map<string, ContentTag[]>();
              for (const contentTag of detail.contentTags) {
                const dimension = contentTag.dimension ?? '其他';
                const list = dimensionGroups.get(dimension) ?? [];
                list.push(contentTag);
                dimensionGroups.set(dimension, list);
              }
              const dimensionOrder = ['人物', '关系', '场景', '动作', '情绪', '产品功能', '业务卖点', '视觉风格', '其他'];
              const sortedGroups = [...dimensionGroups.entries()].sort(
                (left, right) => dimensionOrder.indexOf(left[0]) - dimensionOrder.indexOf(right[0]) || left[0].localeCompare(right[0]),
              );
              return sortedGroups.map(([dimension, tagsList]) => (
                <div key={dimension} className="flex flex-wrap items-start gap-1.5">
                  <Badge
                    variant="outline"
                    className="flex-shrink-0 border-primary/20 bg-primary/5 text-[10px] text-primary/60"
                  >
                    {dimension}
                  </Badge>
                  {tagsList.map((contentTag: ContentTag) => (
                    <Badge
                      key={contentTag.id}
                      variant="outline"
                      className="cursor-default border-dashed border-primary/30 bg-primary/5 text-xs text-primary/70"
                      title={`置信度: ${Math.round(contentTag.confidence * 100)}%`}
                    >
                      {contentTag.tagName}
                      <span className="ml-1 text-[10px] text-primary/40">
                        {Math.round(contentTag.confidence * 100)}
                      </span>
                    </Badge>
                  ))}
                </div>
              ));
            })()}
          </div>
        ) : (
          <span className="mt-1 block text-xs text-muted-foreground">
            {latestAnalysisActive
              ? '后台自动分析中，完成后会自动刷新。'
              : provider.data?.configured
              ? '暂无隐形标签，点击“重新分析”生成。'
              : 'AI Provider 尚未配置'}
          </span>
        )}
      </div>
    </CanRole>
  );
};

export default ImageAiAnalysisPanel;
