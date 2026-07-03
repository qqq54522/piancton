import { MessageSquare } from 'lucide-react';
import { type UseMutationResult } from '@tanstack/react-query';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import type { SearchFeedbackType } from '@client/src/types/api';
import { FEEDBACK_OPTIONS } from './constants';

interface SearchFeedbackPanelProps {
  feedbackNote: string;
  feedbackMutation: UseMutationResult<void, Error, SearchFeedbackType>;
  submittedFeedback: SearchFeedbackType | null;
  onFeedbackNoteChange: (value: string) => void;
}

function SearchFeedbackPanel({
  feedbackNote,
  feedbackMutation,
  submittedFeedback,
  onFeedbackNoteChange,
}: SearchFeedbackPanelProps) {
  return (
    <div className="mt-6 border-t border-border pt-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <MessageSquare className="size-4" />
          <span>这次搜索结果是否满足需求？</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {FEEDBACK_OPTIONS.map((option) => (
            <Button
              key={option.type}
              variant={submittedFeedback === option.type ? 'default' : 'outline'}
              size="sm"
              disabled={feedbackMutation.isPending}
              onClick={() => feedbackMutation.mutate(option.type)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <Input
          value={feedbackNote}
          onChange={(event) => onFeedbackNoteChange(event.target.value)}
          placeholder="可选：补充你想找的画面、风格或业务话术"
          className="h-9 text-sm"
          maxLength={200}
        />
        <Button
          variant="ghost"
          size="sm"
          disabled={!feedbackNote.trim() || feedbackMutation.isPending}
          onClick={() => feedbackMutation.mutate('asset_request')}
        >
          提交说明
        </Button>
      </div>
      {submittedFeedback && (
        <p className="mt-2 text-xs text-emerald-600">已记录反馈，管理员会在搜索运营里看到。</p>
      )}
    </div>
  );
}

export default SearchFeedbackPanel;
