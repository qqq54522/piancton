import { useMemo, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';

import { submitSearchFeedback } from '@client/src/api/image';
import { Button } from '@client/src/components/ui/button';
import type { SearchFeedbackType, SemanticSearchResponse } from '@client/src/types/api';
import SearchFeedbackPanel from './SearchFeedbackPanel';
import SearchResultGrid from './SearchResultGrid';
import {
  searchEvidencePointOptions,
  searchIntentOptions,
  searchIntentTitle,
  searchProofPointOptions,
} from './searchConceptPresentation';
import {
  activeRefinementCount,
  filterResultsByRefinements,
  type SearchRefinements,
} from '../searchResultFilters';

interface SemanticSearchResultProps {
  keyword: string;
  result: SemanticSearchResponse;
  refinements: SearchRefinements;
  onClear: () => void;
}


const SemanticSearchResult = ({
  keyword,
  result,
  refinements,
  onClear,
}: SemanticSearchResultProps) => {
  const [feedbackNote, setFeedbackNote] = useState('');
  const [submittedFeedback, setSubmittedFeedback] = useState<SearchFeedbackType | null>(null);
  const intentions = useMemo(
    () => searchIntentOptions(result.searchUnderstanding),
    [result.searchUnderstanding],
  );
  const proofPoints = useMemo(
    () => searchProofPointOptions(result.searchUnderstanding),
    [result.searchUnderstanding],
  );
  const evidencePoints = useMemo(
    () => searchEvidencePointOptions(result.searchUnderstanding),
    [result.searchUnderstanding],
  );
  const visibleResults = useMemo(
    () => filterResultsByRefinements(result.results, refinements),
    [refinements, result.results],
  );
  const refinementCount = activeRefinementCount(refinements);
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
      <div className="mb-4 flex items-center justify-between gap-3 border-b border-border/70 pb-3">
        <p className="text-sm text-muted-foreground">
          {refinementCount > 0
            ? `当前显示 ${visibleResults.length} 组，已应用 ${refinementCount} 个精细筛选`
            : result.matchSummary || `找到 ${result.results.length} 组素材`}
        </p>
        <Button variant="ghost" size="sm" onClick={onClear}>
          <X className="mr-1 size-3.5" />
          清除搜索
        </Button>
      </div>

      {result.fallback && (
        <div className="mb-4 flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2">
          <AlertTriangle className="size-3.5 text-amber-600" />
          <span className="text-xs text-amber-700">
            {result.results.length === 0
              ? '卖点理解未在时限内完成；为避免返回无关素材，本次没有放开全库结果，请稍后重试。'
              : '本次没有识别出可靠卖点，外部语义增强未在时限内完成；已显示基础搜索结果，可换一种说法或稍后重试。'}
          </span>
        </div>
      )}

      {intentions.length > 0 && (
        <div className="mb-4 rounded-xl border border-primary/15 bg-primary/[0.035] px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-1 text-xs font-medium text-foreground">
              {searchIntentTitle(result.searchUnderstanding?.queryType)}
            </span>
            {intentions.map((intent) => (
              <span
                key={intent.name}
                className="rounded border border-primary/20 bg-background px-2 py-1 text-xs text-foreground"
              >
                {intent.name}
              </span>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            上方业务层级已自动联动；识别不准确时可直接改选卖点、证明点或证据表达点。
          </p>
          {proofPoints.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-primary/10 pt-2">
              <span className="text-[11px] font-medium text-foreground">进一步命中证明点</span>
              {proofPoints.map((point) => (
                <span key={point.name} className="rounded border border-border bg-background px-2 py-0.5 text-[11px] text-muted-foreground">
                  {point.name} · {Math.round(point.weight * 100)}%
                </span>
              ))}
            </div>
          )}
          {evidencePoints.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-primary/10 pt-2">
              <span className="text-[11px] font-medium text-foreground">进一步命中证据表达点</span>
              {evidencePoints.map((point) => (
                <span key={point.name} className="rounded border border-border bg-background px-2 py-0.5 text-[11px] text-muted-foreground">
                  {point.name} · {Math.round(point.weight * 100)}%
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {visibleResults.length > 0 ? (
        <SearchResultGrid
          items={visibleResults}
          keyword={keyword}
          searchLogId={result.searchLogId}
        />
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20">
          <p className="text-sm text-muted-foreground">
            {refinementCount > 0
              ? '当前筛选组合下没有素材，可放宽一个条件'
              : '暂时没有找到合适素材'}
          </p>
        </div>
      )}

      <SearchFeedbackPanel
        feedbackNote={feedbackNote}
        feedbackMutation={feedbackMutation}
        submittedFeedback={submittedFeedback}
        onFeedbackNoteChange={setFeedbackNote}
      />
    </div>
  );
};

export default SemanticSearchResult;
