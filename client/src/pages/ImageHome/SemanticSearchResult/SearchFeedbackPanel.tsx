import { useState } from 'react';
import { Loader2, ThumbsDown, ThumbsUp } from 'lucide-react';
import { type UseMutationResult } from '@tanstack/react-query';

import { Button } from '@client/src/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@client/src/components/ui/dialog';
import type { SearchFeedbackType } from '@client/src/types/api';

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
  const [selected, setSelected] = useState<SearchFeedbackType | null>(null);
  const open = submittedFeedback === null;

  return (
    <Dialog open={open} onOpenChange={() => undefined}>
      <DialogContent
        showCloseButton={false}
        className="max-w-md rounded-3xl border-border/80 p-6 sm:p-7"
        onEscapeKeyDown={(event) => event.preventDefault()}
        onPointerDownOutside={(event) => event.preventDefault()}
      >
        <DialogHeader className="text-left">
          <DialogTitle className="text-xl leading-7">这次搜索结果，你满意吗？</DialogTitle>
          <DialogDescription className="leading-6">
            你的选择会帮助我们继续优化推荐。
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => setSelected('relevant')}
            className={`flex items-center justify-center gap-2 rounded-2xl border px-4 py-4 text-sm font-semibold transition ${
              selected === 'relevant'
                ? 'border-foreground bg-foreground text-background'
                : 'border-border bg-white hover:bg-secondary/70'
            }`}
          >
            <ThumbsUp className="size-4" />满意
          </button>
          <button
            type="button"
            onClick={() => setSelected('not_relevant')}
            className={`flex items-center justify-center gap-2 rounded-2xl border px-4 py-4 text-sm font-semibold transition ${
              selected === 'not_relevant'
                ? 'border-foreground bg-foreground text-background'
                : 'border-border bg-white hover:bg-secondary/70'
            }`}
          >
            <ThumbsDown className="size-4" />不满意
          </button>
        </div>

        <label className="grid gap-2">
          <span className="text-sm font-medium">还有什么值得我们改进？</span>
          <textarea
            value={feedbackNote}
            onChange={(event) => onFeedbackNoteChange(event.target.value)}
            placeholder="可以写下想找的图片、渠道、风格或其它建议（可选）"
            maxLength={500}
            className="min-h-24 resize-none rounded-2xl border border-input bg-white px-4 py-3 text-sm leading-6 outline-none transition focus:border-foreground/50 focus:ring-2 focus:ring-foreground/10"
          />
        </label>

        {feedbackMutation.isError && (
          <p className="text-sm text-destructive">提交失败，请再试一次。</p>
        )}

        <Button
          className="h-11 rounded-2xl"
          disabled={!selected || feedbackMutation.isPending}
          onClick={() => selected && feedbackMutation.mutate(selected)}
        >
          {feedbackMutation.isPending && <Loader2 className="size-4 animate-spin" />}
          提交反馈
        </Button>
      </DialogContent>
    </Dialog>
  );
}

export default SearchFeedbackPanel;
