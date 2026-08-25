import { useMemo, useState } from 'react';
import { RotateCcw, X } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';

import { submitSearchFeedback } from '@client/src/api/image';
import { Button } from '@client/src/components/ui/button';
import { useProjectBasket } from '@client/src/features/assets/useProjectBasket';
import type { SearchFeedbackType, SemanticSearchResponse } from '@client/src/types/api';
import { channelIntentLabel } from '../channelIntent';
import { channelRecommendationFor } from '../channelRecommendations';
import ProjectBasketPanel from './ProjectBasketPanel';
import SearchFeedbackPanel from './SearchFeedbackPanel';
import SearchResultGrid from './SearchResultGrid';
import { searchIntentTitle } from './searchConceptPresentation';
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
  const visibleResults = useMemo(
    () => filterResultsByRefinements(result.results, refinements),
    [refinements, result.results],
  );
  const refinementCount = activeRefinementCount(refinements);
  const intentTitle = searchIntentTitle(result.searchUnderstanding?.queryType);
  const channelRecommendation = channelRecommendationFor(refinements.channel);
  const channelIntent = refinements.channel ? null : refinements.channelIntent;
  const channelIntentRecommendation = channelIntent?.recommendation;
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

      {!result.fallback && (channelRecommendation || channelIntentRecommendation) && (
        <div className="mb-4 flex flex-col gap-1 rounded-xl border border-border/80 bg-[#f7f7f5] px-4 py-2.5">
          <p className="text-xs font-semibold leading-5 text-foreground">
            {channelRecommendation
              ? `推荐${channelRecommendation.value}`
              : `已理解：${channelIntentLabel(channelIntent)}使用场景`}
          </p>
          <p className="text-xs leading-5 text-muted-foreground">
            {channelRecommendation?.description ?? channelIntentRecommendation}
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

export default SemanticSearchResult;
