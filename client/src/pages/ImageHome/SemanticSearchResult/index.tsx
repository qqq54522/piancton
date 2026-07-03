import { useState } from 'react';
import { X, AlertTriangle } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { Button } from '@client/src/components/ui/button';
import { Badge } from '@client/src/components/ui/badge';
import { submitSearchFeedback } from '@client/src/api/image';
import type {
  SearchFeedbackType,
  SearchMode,
  SemanticSearchResponse,
} from '@client/src/types/api';
import SearchFeedbackPanel from './SearchFeedbackPanel';
import SearchResultGrid from './SearchResultGrid';
import SearchUnderstandingPanel from './SearchUnderstandingPanel';
import { MATCH_LEVEL_CONFIG } from './constants';

interface SemanticSearchResultProps {
  keyword: string;
  result: SemanticSearchResponse;
  searchMode: SearchMode;
  onClear: () => void;
  onKeywordClick: (kw: string) => void;
}

const SemanticSearchResult = ({ keyword, result, searchMode, onClear, onKeywordClick }: SemanticSearchResultProps) => {
  const understanding = result.searchUnderstanding;
  const hasResults = result.results.length > 0;
  const [feedbackNote, setFeedbackNote] = useState('');
  const [submittedFeedback, setSubmittedFeedback] = useState<SearchFeedbackType | null>(null);
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

  const groupedResults = {
    S: result.results.filter((r) => r.matchLevel === 'S'),
    A: result.results.filter((r) => r.matchLevel === 'A'),
    B: result.results.filter((r) => r.matchLevel === 'B'),
    C: result.results.filter((r) => r.matchLevel === 'C'),
  };

  return (
    <div className="mt-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-medium text-foreground">
          「{keyword}」的搜索结果
          <Badge className="ml-2 bg-muted text-muted-foreground border-border text-xs">
            {searchMode === 'smart' ? '智能搜索' : '精准搜索'}
          </Badge>
        </h2>
        <Button variant="ghost" size="sm" onClick={onClear}>
          <X className="mr-1 size-3.5" />
          清除搜索
        </Button>
      </div>

      {result.fallback && (
        <div className="mb-4 flex items-center gap-1.5 rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5">
          <AlertTriangle className="size-3.5 text-amber-600" />
          <span className="text-xs text-amber-700">
            智能搜索已降级为精准搜索{result.fallbackReason ? `（${result.fallbackReason}）` : ''}
          </span>
        </div>
      )}

      {understanding && (
        <SearchUnderstandingPanel understanding={understanding} onKeywordClick={onKeywordClick} />
      )}

      {result.matchSummary && (
        <p className="mb-3 text-sm text-muted-foreground">{result.matchSummary}</p>
      )}

      {!hasResults ? (
        <div className="flex flex-col items-center justify-center py-20">
          <p className="text-sm text-muted-foreground">未找到相关图片</p>
        </div>
      ) : (
        <div className="space-y-6">
          {(['S', 'A', 'B', 'C'] as const).map((level) => {
            const items = groupedResults[level];
            if (items.length === 0) return null;
            const config = MATCH_LEVEL_CONFIG[level];
            return (
              <div key={level}>
                <div className="mb-2 flex items-center gap-2">
                  <Badge className={`${config.color} text-xs`}>
                    {level}级 · {config.label}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{items.length} 张</span>
                </div>
                <SearchResultGrid items={items} />
              </div>
            );
          })}
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
