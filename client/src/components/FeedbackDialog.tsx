import { useEffect, useState } from 'react';
import { LoaderCircle } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@client/src/components/ui/dialog';

export const PROJECT_FEEDBACK_FORM_URL =
  'https://guanghe.feishu.cn/share/base/shrcnPaDC8ZGGfeW6lJ0WKTXgjd';

interface FeedbackDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function FeedbackDialog({ open, onOpenChange }: FeedbackDialogProps) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (open) setLoaded(false);
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="h-[min(820px,calc(100vh-1.5rem))] w-[min(780px,calc(100vw-1.5rem))] max-w-none grid-rows-[auto_minmax(0,1fr)] overflow-hidden p-0">
        <DialogHeader className="shrink-0 border-b border-border/70 px-6 py-5 pr-16">
          <DialogTitle>提交反馈</DialogTitle>
          <DialogDescription>
            填写后会直接提交到项目反馈表，无需离开当前页面。
          </DialogDescription>
        </DialogHeader>
        <div className="relative min-h-0 flex-1 bg-[#f7f7f5]">
          {!loaded && (
            <div
              className="absolute inset-0 z-10 grid place-items-center bg-[#f7f7f5] text-sm text-muted-foreground"
              aria-label="正在加载反馈表"
            >
              <span className="flex items-center gap-2">
                <LoaderCircle className="size-4 animate-spin" />正在加载反馈表…
              </span>
            </div>
          )}
          <iframe
            title="项目反馈表"
            src={PROJECT_FEEDBACK_FORM_URL}
            className="h-full w-full border-0 bg-white"
            referrerPolicy="strict-origin-when-cross-origin"
            allow="clipboard-write"
            onLoad={() => setLoaded(true)}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
