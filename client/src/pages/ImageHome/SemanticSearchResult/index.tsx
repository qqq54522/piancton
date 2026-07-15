import { useMemo, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';

import { submitSearchFeedback } from '@client/src/api/image';
import { Button } from '@client/src/components/ui/button';
import type { SearchFeedbackType, SemanticSearchResponse } from '@client/src/types/api';
import SearchFeedbackPanel from './SearchFeedbackPanel';
import SearchResultGrid from './SearchResultGrid';

interface SemanticSearchResultProps {
  keyword: string;
  result: SemanticSearchResponse;
  onClear: () => void;
  onKeywordClick: (keyword: string) => void;
}

const SemanticSearchResult = ({
  keyword,
  result,
  onClear,
  onKeywordClick,
}: SemanticSearchResultProps) => {
  const [feedbackNote, setFeedbackNote] = useState('');
  const [submittedFeedback, setSubmittedFeedback] = useState<SearchFeedbackType | null>(null);
  const intentions = useMemo(
    () => Array.from(new Set(
      result.searchUnderstanding?.matchedBusinessConcepts.map((item) => item.concept) ?? [],
    )).slice(0, 4),
    [result.searchUnderstanding],
  );
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
            部分搜索增强服务暂不可用，已展示当前可用的最佳结果。
          </span>
        </div>
      )}

      {intentions.length > 1 && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">你可能想找：</span>
          {intentions.map((intent) => (
            <button
              key={intent}
              type="button"
              onClick={() => onKeywordClick(intent)}
              className="rounded-full border border-border bg-background px-3 py-1 text-xs hover:border-primary hover:text-primary"
            >
              {intent}
            </button>
          ))}
        </div>
      )}

      {result.results.length > 0 ? (
        <SearchResultGrid
          items={result.results}
          keyword={keyword}
          searchLogId={result.searchLogId}
        />
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20">
          <p className="text-sm text-muted-foreground">暂时没有找到合适素材</p>
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
