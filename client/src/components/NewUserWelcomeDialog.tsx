import { useRef, useState } from 'react';
import {
  BotMessageSquare,
  FolderOpen,
  Lightbulb,
  UserRound,
  Sparkles,
} from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@client/src/components/ui/dialog';

interface NewUserWelcomeDialogProps {
  open: boolean;
  onComplete: () => Promise<void>;
}

const Question = ({ children }: { children: string }) => (
  <p className="rounded-xl border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-semibold leading-5 text-sky-950">“{children}”</p>
);

export default function NewUserWelcomeDialog({
  open,
  onComplete,
}: NewUserWelcomeDialogProps) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const submittingRef = useRef(false);

  const finishOnboarding = async () => {
    if (submittingRef.current) return;
    submittingRef.current = true;
    setSubmitting(true);
    setError('');
    try {
      await onComplete();
    } catch {
      setError('暂时无法保存引导状态，请稍后再试。');
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) void finishOnboarding();
      }}
    >
      <DialogContent className="max-h-[calc(100vh-1.5rem)] w-[min(980px,calc(100vw-1.5rem))] max-w-none gap-0 overflow-y-auto rounded-[28px] p-0">
        <DialogHeader className="border-b border-border/70 bg-gradient-to-br from-secondary/80 via-card to-card px-6 pb-6 pt-7 text-left sm:px-8">
          <div className="mb-4 flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-white/80 px-3 py-1 text-xs font-semibold text-muted-foreground shadow-sm">
              <Sparkles className="size-3.5" />内测版
            </span>
          </div>
          <DialogTitle className="text-2xl tracking-tight sm:text-3xl">欢迎来到卖点智库</DialogTitle>
          <DialogDescription className="max-w-3xl text-sm leading-6 sm:text-base">
            右侧 <strong className="font-bold text-sky-900">Agent 是你的洋葱学园专属助手</strong>。直接像聊天一样问它，了解洋葱学园、继续追问，或让它帮你找图库中的图片。
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 px-6 py-6 md:grid-cols-3 sm:px-8 sm:py-8">
          <article className="rounded-2xl border border-border/75 bg-card p-5 shadow-sm">
            <BotMessageSquare className="size-6 text-sky-700" />
            <h2 className="mt-4 text-base font-bold">先问，再接着聊</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">不知道从哪里开始？<strong className="text-foreground">直接问右侧 Agent</strong>，回答后可以继续追问。</p>
            <div className="mt-4 space-y-2"><Question>洋葱学园的六大体系是什么？</Question><Question>详细讲讲同步自学体系。</Question><Question>同步课和培优课有什么区别？</Question></div>
          </article>
          <article className="rounded-2xl border border-border/75 bg-card p-5 shadow-sm">
            <FolderOpen className="size-6 text-emerald-700" />
            <h2 className="mt-4 text-base font-bold">找图有两种方式</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground"><strong className="text-foreground">手动点渠道和下级目录</strong>，浏览已有图片；也可以直接告诉 Agent 你想找什么。</p>
            <div className="mt-4 space-y-2"><Question>帮我找新疆合作的案例图。</Question><p className="text-xs leading-5 text-muted-foreground">找到图库里已有的素材时，点击图片卡片即可看详情。</p></div>
          </article>
          <article className="rounded-2xl border border-sky-200 bg-sky-50/40 p-5 shadow-sm">
            <Lightbulb className="size-6 text-amber-700" />
            <h2 className="mt-4 text-base font-bold">复杂需求，可以两步问</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">如果需要判断业务含义，<strong className="text-sky-900">先聊清楚卖点，再接着找图</strong>，Agent 会沿用这段对话。</p>
            <div className="mt-4 space-y-2"><Question>洋葱学园的拍题精学让孩子学一题会一类，涉及哪几个卖点？</Question><Question>帮我找这两个卖点下的图片。</Question></div>
          </article>
        </div>

        <div className="mx-6 flex items-start gap-3 rounded-2xl bg-secondary/70 px-5 py-4 sm:mx-8">
          <UserRound className="mt-0.5 size-5 shrink-0 text-sky-800" />
          <p className="text-sm leading-6 text-foreground/80">
            <strong className="text-sky-900">右上角是你的账号头像，点它可以查看我的喜欢、我的收藏和消息。</strong> 你还可以在那里更换头像或提交反馈。
          </p>
        </div>

        {error && <p role="alert" className="px-6 pt-4 text-sm text-destructive sm:px-8">{error}</p>}

        <DialogFooter className="px-6 pb-6 pt-5 sm:px-8 sm:pb-8">
          <Button className="h-11 min-w-44 rounded-xl" disabled={submitting} onClick={() => void finishOnboarding()}>
            {submitting ? '正在进入…' : '知道了，开始使用'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
