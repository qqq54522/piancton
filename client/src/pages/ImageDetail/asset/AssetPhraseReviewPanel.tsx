import { useState } from 'react';
import { ArrowUpRight, BookOpenText, Check, MessageSquarePlus, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

import { getApiError } from '@client/src/api/client';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import type { AssetGroup } from '@client/src/types/api';
import type { BusinessConcept } from '@client/src/types/api';
import type { useAssetActions } from '@client/src/features/assets/useAssetActions';
import { splitAssetSearchPhrases } from '@client/src/features/assets/assetPhrasePresentation';
import {
  selectInheritedConcepts,
  splitAcceptedConceptPhrases,
} from '@client/src/features/assets/conceptPhrasePresentation';
import { useAuth } from '@client/src/lib/auth';

type AssetActions = ReturnType<typeof useAssetActions>;

function AssetPhraseReviewPanel({
  group,
  concepts,
  actions,
}: {
  group: AssetGroup;
  concepts: BusinessConcept[];
  actions: AssetActions;
}) {
  const { user } = useAuth();
  const [phrase, setPhrase] = useState('');
  const { accepted, pendingAi } = splitAssetSearchPhrases(group.searchPhrases);
  const inherited = selectInheritedConcepts(group.conceptLinks, concepts);

  const addPhrase = async () => {
    if (!phrase.trim()) return;
    try {
      await actions.addPhrase.mutateAsync(phrase.trim());
      setPhrase('');
      toast.success('素材独有搜索语已添加');
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };
  const review = async (phraseId: string, reviewStatus: 'accepted' | 'rejected') => {
    try {
      await actions.reviewPhrase.mutateAsync({ phraseId, reviewStatus });
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  return (
    <section className="surface-card p-5 sm:p-6">
      {inherited.length > 0 && (
        <div className="mb-5 rounded-2xl border border-primary/15 bg-accent/45 p-4">
          <div className="flex items-start gap-2.5">
            <BookOpenText className="mt-0.5 size-4 shrink-0 text-primary" />
            <div className="min-w-0 flex-1">
              <h2 className="text-sm font-semibold">从卖点继承的公共话术</h2>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                这些话术由关联卖点统一维护，不需要在当前素材重复添加。
              </p>
            </div>
          </div>
          <div className="mt-3 space-y-3">
            {inherited.map((concept) => {
              const phrases = splitAcceptedConceptPhrases(concept.searchPhrases);
              return (
                <div key={concept.id} className="rounded-xl bg-card/80 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-semibold">
                      {concept.name} · {phrases.publicPhrases.length} 条公共话术
                    </span>
                    {user?.role === 'admin' && (
                      <Button variant="ghost" size="sm" asChild className="h-7 px-2 text-xs">
                        <Link to={`/admin/concepts?concept=${concept.id}`}>
                          管理 <ArrowUpRight className="size-3" />
                        </Link>
                      </Button>
                    )}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {phrases.publicPhrases.slice(0, 4).map((item) => (
                      <Badge key={item.id} variant="secondary">{item.phrase}</Badge>
                    ))}
                    {phrases.publicPhrases.length > 4 && (
                      <Badge variant="outline">还有 {phrases.publicPhrases.length - 4} 条</Badge>
                    )}
                    {phrases.keywords.length > 0 && (
                      <Badge variant="outline">{phrases.keywords.length} 个辅助关键词</Badge>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">当前素材独有话术</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">只维护这张图区别于同卖点其他素材的画面、文案和使用场景；建议保持在 3～8 条。</p>
        </div>
        <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
          <span className="rounded-full bg-secondary px-2.5 py-1 text-[11px] text-muted-foreground">已确认 {accepted.length}</span>
          {pendingAi.length > 0 && (
            <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[11px] text-primary">待确认 {pendingAi.length}</span>
          )}
        </div>
      </div>
      <div className="mt-4 overflow-hidden rounded-2xl border border-border/80 bg-secondary/20">
        <div className="flex items-center justify-between gap-3 border-b border-border/70 bg-card/80 px-3 py-2">
          <span className="text-xs font-medium text-foreground">话术列表</span>
          <span className="text-[11px] text-muted-foreground">在框内上下滚动查看更多</span>
        </div>
        <div
          className="compact-scrollbar max-h-[22rem] snap-y snap-proximity overflow-y-auto overscroll-contain p-3 pr-2"
          role="region"
          aria-label="素材独有话术列表"
          tabIndex={0}
        >
          <div className="min-h-8 space-y-2">
            {accepted.length > 0
              ? accepted.map((item, index) => (
                <div
                  key={item.id}
                  data-testid="accepted-asset-phrase-row"
                  className="flex snap-start items-start gap-3 rounded-xl border border-border/75 bg-card px-3.5 py-3"
                >
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-secondary text-[11px] font-medium text-muted-foreground">
                    {index + 1}
                  </span>
                  <span className="min-w-0 flex-1 text-sm leading-6 text-foreground">
                    {item.phrase}
                  </span>
                </div>
              ))
              : <span className="text-xs text-muted-foreground">暂无已确认的素材独有搜索语</span>}
          </div>
          {pendingAi.length > 0 && (
            <div className="mt-4 border-t border-border/70 pt-4">
              <div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted-foreground">
                <span>AI 待确认候选</span>
                <span className="rounded-full bg-card px-2 py-0.5">{pendingAi.length} 条</span>
              </div>
              <div className="space-y-2">
                {pendingAi.map((item) => (
                  <div key={item.id} className="flex snap-start items-center gap-2 rounded-xl border bg-card px-3 py-2.5">
                    <span className="min-w-0 flex-1 text-sm leading-5">{item.phrase}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`接受“${item.phrase}”`}
                      title="接受"
                      onClick={() => review(item.id, 'accepted')}
                    >
                      <Check className="size-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`拒绝“${item.phrase}”`}
                      title="拒绝"
                      onClick={() => review(item.id, 'rejected')}
                    >
                      <X className="size-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      <div className="mt-5 rounded-xl border border-border/80 bg-secondary/40 p-3">
        <label className="field-label">添加新说法</label>
        <div className="flex gap-2">
          <Input
            value={phrase}
            onChange={(event) => setPhrase(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && phrase.trim()) addPhrase();
            }}
            placeholder="例如：蓝色竖版学习周报"
            maxLength={300}
            className="bg-card"
          />
          <Button onClick={addPhrase} disabled={!phrase.trim() || actions.addPhrase.isPending}>
            <MessageSquarePlus className="size-4" />添加
          </Button>
        </div>
      </div>
    </section>
  );
}

export default AssetPhraseReviewPanel;
