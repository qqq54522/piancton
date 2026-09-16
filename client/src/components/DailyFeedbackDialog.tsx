import { useRef, useState } from 'react';
import { CheckCircle2 } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { FeishuFormDialog } from '@client/src/components/FeedbackDialog';

export const DAILY_FEEDBACK_FORM_URL =
  'https://guanghe.feishu.cn/share/base/form/shrcnPICl1dbBjd0KXW5xUCHTFd';

interface DailyFeedbackDialogProps {
  open: boolean;
  onComplete: () => Promise<void>;
}

export default function DailyFeedbackDialog({
  open,
  onComplete,
}: DailyFeedbackDialogProps) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const submittingRef = useRef(false);

  const finish = async () => {
    if (submittingRef.current) return;
    submittingRef.current = true;
    setSubmitting(true);
    setError('');
    try {
      await onComplete();
    } catch {
      setError('暂时无法保存完成状态，请检查网络后重试。');
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  const footer = (
    <div className="border-t border-border/70 bg-card px-6 py-4">
      {error && <p role="alert" className="mb-3 text-sm text-destructive">{error}</p>}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs leading-5 text-muted-foreground">
          提交飞书表单后，请点击右侧按钮完成今天的反馈。
        </p>
        <Button
          type="button"
          className="h-10 shrink-0 rounded-xl"
          disabled={submitting}
          onClick={() => void finish()}
        >
          <CheckCircle2 className="size-4" />
          {submitting ? '正在保存…' : '我已提交，完成今日反馈'}
        </Button>
      </div>
    </div>
  );

  return (
    <FeishuFormDialog
      open={open}
      onOpenChange={() => undefined}
      formUrl={DAILY_FEEDBACK_FORM_URL}
      title="昨日使用反馈"
      description={(
        <>
          请回顾昨天使用卖点智库的体验。<strong className="font-semibold text-foreground">每天只需填写一次</strong>，完成后今天不再弹出。
        </>
      )}
      frameTitle="昨日使用反馈表"
      dismissible={false}
      footer={footer}
    />
  );
}
