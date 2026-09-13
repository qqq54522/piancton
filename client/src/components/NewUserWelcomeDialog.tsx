import { useRef, useState } from 'react';
import {
  BotMessageSquare,
  FolderHeart,
  Heart,
  LibraryBig,
  Search,
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

const welcomeCards = [
  {
    title: '把业务需求变成可用素材',
    description:
      '卖点智库把业务体系、核心卖点和已确认素材连接起来。直接描述你要表达的内容，就能更快找到真正适合使用的卖点图。',
    icon: LibraryBig,
    accent: 'bg-amber-50 text-amber-800',
  },
  {
    title: '顶部找图，右侧继续问',
    description:
      '找素材时使用顶部搜索栏；想了解卖点、判断一张图怎么用，或继续追问业务问题时，打开右侧 Piancton Agent。',
    icon: Search,
    accent: 'bg-sky-50 text-sky-800',
  },
  {
    title: '喜欢随手留，收藏按画板整理',
    description:
      '“喜欢”集中保存你常用的图片；“收藏”可以新建画板，按项目、渠道或使用场景整理素材，之后从头像菜单随时找回。',
    icon: Heart,
    accent: 'bg-rose-50 text-rose-800',
  },
] as const;

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
          <DialogDescription className="max-w-2xl text-sm leading-6 sm:text-base">
            用一分钟认识三个最常用的入口，之后就可以直接开始找图。
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 px-6 py-6 sm:grid-cols-3 sm:px-8 sm:py-8">
          {welcomeCards.map(({ title, description, icon: Icon, accent }, index) => (
            <article key={title} className="rounded-2xl border border-border/75 bg-card p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className={`flex size-10 items-center justify-center rounded-xl ${accent}`}>
                  <Icon className="size-5" />
                </span>
                <span className="text-xs font-semibold text-muted-foreground">0{index + 1}</span>
              </div>
              <h2 className="mt-5 text-base font-semibold tracking-tight">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
              {index === 1 && (
                <div className="mt-4 flex items-center gap-2 text-xs font-medium text-foreground/75">
                  <Search className="size-3.5" />搜索素材
                  <span className="text-border">·</span>
                  <BotMessageSquare className="size-3.5" />理解与追问
                </div>
              )}
              {index === 2 && (
                <div className="mt-4 flex items-center gap-2 text-xs font-medium text-foreground/75">
                  <Heart className="size-3.5" />我的喜欢
                  <span className="text-border">·</span>
                  <FolderHeart className="size-3.5" />我的收藏
                </div>
              )}
            </article>
          ))}
        </div>

        <div className="mx-6 rounded-2xl bg-secondary/70 px-5 py-4 sm:mx-8">
          <p className="text-sm leading-6 text-foreground/80">
            卖点智库目前仍处于内测阶段。我们会结合真实使用行为持续优化搜索与推荐，也难免有不完善之处，感谢你的理解和共建。遇到问题或有新的想法，请点击头像中的“提交反馈”告诉我们；提交时尽量留下联系人，方便我们快速确认并跟进。
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
