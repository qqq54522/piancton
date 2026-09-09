import { useMemo, useState } from 'react';
import { RotateCcw, X } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';

import { submitSearchFeedback } from '@client/src/api/image';
import { Button } from '@client/src/components/ui/button';
import { useProjectBasket } from '@client/src/features/assets/useProjectBasket';
import type { SearchFeedbackType, SemanticSearchResponse } from '@client/src/types/api';
import ProjectBasketPanel from './ProjectBasketPanel';
import SearchFeedbackPanel from './SearchFeedbackPanel';
import SearchResultGrid from './SearchResultGrid';
import { searchIntentOptions, searchIntentTitle } from './searchConceptPresentation';
import {
  activeRefinementCount,
  filterResultsByRefinements,
  type SearchRefinements,
} from '../searchResultFilters';

interface SemanticSearchResultProps {
  keyword: string;
  result: SemanticSearchResponse;
  refinements: SearchRefinements;
  showSearchContext: boolean;
  manualFilterOpen: boolean;
  showBusinessAccount: boolean;
  animateGifPreview: boolean;
  onClear: () => void;
  onRetry: () => void;
}


const SemanticSearchResult = ({
  keyword,
  result,
  refinements,
  showSearchContext,
  manualFilterOpen,
  showBusinessAccount,
  animateGifPreview,
  onClear,
  onRetry,
}: SemanticSearchResultProps) => {
  const [feedbackNote, setFeedbackNote] = useState('');
  const [submittedFeedback, setSubmittedFeedback] = useState<SearchFeedbackType | null>(null);
  const projectBasket = useProjectBasket();
  const matchedSellingPoints = useMemo(
    () => searchIntentOptions(result.searchUnderstanding).map((item) => item.name),
    [result.searchUnderstanding],
  );
  const visibleResults = useMemo(
    () => filterResultsByRefinements(
      result.results,
      refinements,
      { preserveConceptNames: matchedSellingPoints },
    ),
    [matchedSellingPoints, refinements, result.results],
  );
  const refinementCount = activeRefinementCount(refinements);
  const intentTitle = searchIntentTitle(result.searchUnderstanding?.queryType);
  const routeSummary = buildRouteSummary({
    keyword,
    matchedSellingPoints,
    routeExplanation: result.routeExplanation,
  });
  const feedbackMutation = useMutation({
    mutationFn: (feedbackType: SearchFeedbackType) => submitSearchFeedback({
      searchLogId: result.searchLogId,
      keyword,
      feedbackType,
      note: feedbackNote.trim() || undefined,
    }),
    onSuccess: (_data, feedbackType) => {
      setSubmittedFeedback(feedbackType);
      setFeedbackNote('');
    },
  });

  return (
    <div className="mt-6">
      {showSearchContext && (
        <div className="mb-4 flex items-center justify-between gap-3 border-b border-border/70 pb-3">
          <p className="text-sm text-muted-foreground">
            {refinementCount > 0
              ? `当前显示 ${visibleResults.length} 组，已应用 ${refinementCount} 个渠道/场景筛选`
              : result.matchSummary || `${intentTitle}，找到 ${result.results.length} 组素材`}
          </p>
          <Button variant="ghost" size="sm" onClick={onClear}>
            <X className="mr-1 size-3.5" />
            清除搜索
          </Button>
        </div>
      )}

      {result.fallback && (
        <div className="flex min-h-[360px] items-center justify-center">
          <div className="text-center">
            <h2 className="text-base font-semibold text-muted-foreground">查找通道出现了一些问题，请稍后再试</h2>
            <p className="mt-2 text-xs text-muted-foreground">
              {result.fallbackReason || '外部语义增强未在时限内完成'}
            </p>
            <div className="mt-4 flex items-center justify-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground"
                onClick={onRetry}
              >
                <RotateCcw className="size-4" />
                重新尝试
              </Button>
              <Button type="button" variant="ghost" size="sm" className="rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground" onClick={onClear}>
                清除搜索
              </Button>
            </div>
          </div>
        </div>
      )}

      {!result.fallback && routeSummary && (
        <div className="mb-4 flex flex-col gap-1 rounded-lg border border-foreground/10 bg-foreground px-4 py-3 text-background shadow-sm">
          <p className="text-xs font-semibold leading-5">
            {routeSummary.title}
          </p>
          <p className="text-xs leading-5 text-background/78">
            {routeSummary.description}
          </p>
        </div>
      )}

      {!result.fallback && visibleResults.length > 0 ? (
        <>
          <ProjectBasketPanel
            items={projectBasket.items}
            onRemove={projectBasket.remove}
            onClear={projectBasket.clear}
          />
          <SearchResultGrid
            key={`${result.searchLogId ?? keyword}:${visibleResults.length}`}
            items={visibleResults}
            keyword={keyword}
            searchLogId={result.searchLogId}
            showSearchContext={showSearchContext}
            animateGifPreview={animateGifPreview}
            isInProjectBasket={projectBasket.has}
            onToggleProjectBasket={projectBasket.toggle}
          />
        </>
      ) : !result.fallback ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20">
          <p className="text-sm text-muted-foreground">
            {refinementCount > 0
              ? '当前筛选组合下没有素材，可放宽一个条件'
              : (result.searchUnderstanding?.matchedBusinessConcepts.length ?? 0) === 0
                ? '本次没有识别出可靠卖点，暂时没有找到合适素材'
                : '暂时没有找到合适素材'}
          </p>
        </div>
      ) : null}

      {showSearchContext && !result.fallback && (
        <SearchFeedbackPanel
          feedbackNote={feedbackNote}
          feedbackMutation={feedbackMutation}
          manualFilterOpen={manualFilterOpen}
          showBusinessAccount={showBusinessAccount}
          submittedFeedback={submittedFeedback}
          onFeedbackNoteChange={setFeedbackNote}
        />
      )}
    </div>
  );
};

interface RouteSummaryInput {
  keyword: string;
  matchedSellingPoints: string[];
  routeExplanation?: string | null;
}

function buildRouteSummary({
  keyword,
  matchedSellingPoints,
  routeExplanation,
}: RouteSummaryInput): { title: string; description: string } | null {
  if (matchedSellingPoints.length === 0) return null;
  const sellingPointText = matchedSellingPoints.length > 0
    ? matchedSellingPoints.slice(0, 3).join('、')
    : '当前需求';
  return {
    title: `命中卖点：${sellingPointText}`,
    description: cleanRouteExplanation(routeExplanation)
      || buildLocalRouteExplanation(keyword, sellingPointText),
  };
}

function cleanRouteExplanation(value?: string | null): string {
  const processMarkers = [
    '未指定渠道',
    '当前返回',
    '卡片下方',
    '已审核素材',
    '保留手机端大图',
    '保留手机端小图',
    '已按当前渠道',
    '渠道/场景筛选',
    '同时按',
    '收窄版位',
  ];
  const explanation = (value ?? '').replace(/\s+/g, ' ').trim();
  const cutoffIndexes = processMarkers
    .map((marker) => explanation.indexOf(marker))
    .filter((index) => index >= 0);
  return (cutoffIndexes.length
    ? explanation.slice(0, Math.min(...cutoffIndexes))
    : explanation
  )
    .replace(/(?:未指定渠道|已按当前渠道\/场景筛选|同时按).+?(?:。|$)/g, '')
    .replace(/当前返回\s*\d+\s*组[^。]*。?/g, '')
    .replace(/卡片下方[^。]*。?/g, '')
    .replace(/[，,；; ]+$/g, '')
    .trim();
}

function buildLocalRouteExplanation(keyword: string, sellingPointText: string): string {
  const query = keyword.trim();
  const queryText = query ? `「${query}」` : '这句话';
  return `${queryText}的有效信号不是单个关键词，而是整句话表达出的学习动作、目标结果和使用场景；这些信号与「${sellingPointText}」的核心能力一致，所以优先推荐该卖点下已确认的素材。`;
}

export default SemanticSearchResult;
