import { useEffect, useState, type ReactNode } from 'react';
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

export interface FeishuFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  formUrl: string;
  title: string;
  description: ReactNode;
  frameTitle: string;
  dismissible?: boolean;
  footer?: ReactNode;
}

export function FeishuFormDialog({
  open,
  onOpenChange,
  formUrl,
  title,
  description,
  frameTitle,
  dismissible = true,
  footer,
}: FeishuFormDialogProps) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (open) setLoaded(false);
  }, [open]);

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (dismissible || nextOpen) onOpenChange(nextOpen);
      }}
    >
      <DialogContent
        className={`h-[min(820px,calc(100vh-1.5rem))] w-[min(780px,calc(100vw-1.5rem))] max-w-none overflow-hidden p-0 ${footer ? 'grid-rows-[auto_minmax(0,1fr)_auto]' : 'grid-rows-[auto_minmax(0,1fr)]'}`}
        showCloseButton={dismissible}
        onEscapeKeyDown={(event) => {
          if (!dismissible) event.preventDefault();
        }}
        onPointerDownOutside={(event) => {
          if (!dismissible) event.preventDefault();
        }}
      >
        <DialogHeader className="shrink-0 border-b border-border/70 px-6 py-5 pr-16">
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
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
            title={frameTitle}
            src={formUrl}
            className="h-full w-full border-0 bg-white"
            referrerPolicy="strict-origin-when-cross-origin"
            allow="clipboard-write"
            onLoad={() => setLoaded(true)}
          />
        </div>
        {footer}
      </DialogContent>
    </Dialog>
  );
}

interface FeedbackDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function FeedbackDialog({ open, onOpenChange }: FeedbackDialogProps) {
  return (
    <FeishuFormDialog
      open={open}
      onOpenChange={onOpenChange}
      formUrl={PROJECT_FEEDBACK_FORM_URL}
      title="提交反馈"
      description="填写后会直接提交到项目反馈表，无需离开当前页面。"
      frameTitle="项目反馈表"
    />
  );
}
