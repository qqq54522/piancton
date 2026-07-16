import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';

import { submitSearchFeedback } from '@client/src/api/image';
import { Button } from '@client/src/components/ui/button';
import type { SearchFeedbackType, SemanticSearchResponse } from '@client/src/types/api';
import SearchFeedbackPanel from './SearchFeedbackPanel';
import SearchResultGrid from './SearchResultGrid';
import { filterResultsByIntent, searchIntentOptions } from './searchConceptPresentation';

interface SemanticSearchResultProps {
  keyword: string;
  result: SemanticSearchResponse;
  onClear: () => void;
}

const SemanticSearchResult = ({
  keyword,
  result,
  onClear,
}: SemanticSearchResultProps) => {
  const [feedbackNote, setFeedbackNote] = useState('');
  const [submittedFeedback, setSubmittedFeedback] = useState<SearchFeedbackType | null>(null);
  const [activeIntent, setActiveIntent] = useState<string | null>(null);
  const intentions = useMemo(
    () => searchIntentOptions(result.searchUnderstanding),
    [result.searchUnderstanding],
  );
  const visibleResults = useMemo(
    () => filterResultsByIntent(result.results, activeIntent),
    [activeIntent, result.results],
  );
  useEffect(() => setActiveIntent(null), [keyword, result]);
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
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-medium text-foreground">「{keyword}」的素材结果</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {result.matchSummary || `找到 ${result.results.length} 组素材`}
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onClear}>
          <X className="mr-1 size-3.5" />
          清除搜索
        </Button>
      </div>

      {result.fallback && (
        <div className="mb-4 flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2">
          <AlertTriangle className="size-3.5 text-amber-600" />
          <span className="text-xs text-amber-700">
            智能语义搜索暂时响应较慢，已使用基础搜索；结果可能不完整，可换一种说法或稍后重试。
          </span>
        </div>
      )}

      {intentions.length > 0 && (
        <div className="mb-4 rounded-xl border border-primary/15 bg-primary/[0.035] px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-1 text-xs font-medium text-foreground">本次识别到的卖点</span>
            {intentions.length > 1 && (
              <button
                type="button"
                onClick={() => setActiveIntent(null)}
                aria-pressed={activeIntent === null}
                className={`rounded-full border px-3 py-1 text-xs transition-colors ${activeIntent === null ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background hover:border-primary hover:text-primary'}`}
              >
                全部
              </button>
            )}
            {intentions.map((intent) => (
              <button
                key={intent.name}
                type="button"
                onClick={() => setActiveIntent(intent.name)}
                aria-pressed={activeIntent === intent.name}
                className={`rounded-full border px-3 py-1 text-xs transition-colors ${activeIntent === intent.name ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background hover:border-primary hover:text-primary'}`}
              >
                {intent.name}
              </button>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            可按卖点缩小当前结果；图片右下角会说明它因哪个卖点出现。
          </p>
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
            {activeIntent ? `当前结果中没有“${activeIntent}”素材` : '暂时没有找到合适素材'}
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
