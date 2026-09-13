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
    title: '把业务需求变成可用的卖点图',
    description:
      '直接用日常语言描述你想表达的内容。卖点智库会先理解需求对应的业务卖点，再从已确认素材中优先找到真正适用的图片；如果库里暂时没有合适素材，也会如实告诉你。',
    icon: LibraryBig,
    accent: 'bg-amber-50 text-amber-800',
  },
  {
    title: '顶部直接找图，右侧深入理解',
    description:
      '已经知道要找什么时，优先使用顶部搜索，例如“新疆合作案例”。当需求需要语义理解、卖点判断，或你还想继续追问时，使用右侧 Agent；它会先理解你的需求，再结合卖点帮你回答或找图。',
    icon: Search,
    accent: 'bg-sky-50 text-sky-800',
  },
  {
    title: '喜欢随手留，收藏按画板整理',
    description:
      '常用图片可以点“喜欢”，之后从头像里的“我的喜欢”快速找回。需要分类时，再收藏到画板；你可以按项目、渠道或使用场景建立多个独立素材集。',
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
          <DialogDescription className="max-w-3xl text-sm leading-6 sm:text-base">
            卖点智库基于公司的六大业务体系与核心卖点，帮你更快找到适合业务需求的素材。不熟悉这些体系和卖点也没关系：打开右侧 Agent 直接提问，就能了解相关背景、卖点含义和适用场景。
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
                <div className="mt-4 space-y-2 rounded-xl bg-secondary/60 p-3 text-xs font-medium text-foreground/75">
                  <div className="flex items-center gap-2">
                    <Search className="size-3.5" />目标明确：顶部搜索
                  </div>
                  <div className="flex items-center gap-2">
                    <BotMessageSquare className="size-3.5" />需要理解或追问：Agent
                  </div>
                </div>
              )}
              {index === 2 && (
                <div className="mt-4 space-y-2 rounded-xl bg-secondary/60 p-3 text-xs font-medium text-foreground/75">
                  <div className="flex items-center gap-2">
                    <Heart className="size-3.5" />喜欢：快速找回常用图片
                  </div>
                  <div className="flex items-center gap-2">
                    <FolderHeart className="size-3.5" />收藏：按画板分类整理
                  </div>
                </div>
              )}
            </article>
          ))}
        </div>

        <div className="mx-6 rounded-2xl bg-secondary/70 px-5 py-4 sm:mx-8">
          <p className="text-sm leading-6 text-foreground/80">
            卖点智库目前处于内测阶段，搜索和推荐仍在持续优化。你的真实使用和反馈会帮助我们更快发现问题、改进体验。遇到问题或有任何想法，请点击头像里的“提交反馈”；提交时尽量留下联系人，方便我们尽快与你确认并跟进。感谢你的理解与共建。
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
