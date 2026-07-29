import { useEffect, useMemo, useState } from 'react';
import { Check, Loader2, MessageSquareText, Search } from 'lucide-react';
import { toast } from 'sonner';

import { getApiError } from '@client/src/api/client';
import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { useBusinessConceptActions } from '@client/src/features/assets/useBusinessConceptActions';
import { useBusinessConcepts } from '@client/src/features/assets/useBusinessConcepts';
import type { BusinessConcept } from '@client/src/types/api';

export default function AdminRecommendations() {
  const concepts = useBusinessConcepts();
  const actions = useBusinessConceptActions();
  const [query, setQuery] = useState('');
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  useEffect(() => {
    const next: Record<string, string> = {};
    (concepts.data ?? []).forEach((concept) => {
      next[concept.id] = concept.recommendationText ?? '';
    });
    setDrafts(next);
  }, [concepts.data]);

  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return concepts.data ?? [];
    return (concepts.data ?? []).filter((concept) => (
      concept.name.toLowerCase().includes(keyword)
      || concept.code.toLowerCase().includes(keyword)
    ));
  }, [concepts.data, query]);

  const save = async (concept: BusinessConcept) => {
    try {
      await actions.updateConcept.mutateAsync({
        conceptId: concept.id,
        input: {
          recommendationText: drafts[concept.id]?.trim() || null,
        },
      });
      toast.success('推荐语已保存');
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  if (concepts.isLoading) {
    return (
      <div className="grid min-h-[60vh] place-items-center">
        <Loader2 className="size-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="page-shell">
      <PageHeader
        eyebrow="Result Recommendation Copy"
        title="结果推荐语"
        description="维护每个卖点在搜索结果卡片里的人工推荐文案；卡片只展示当前搜索命中的卖点。"
      />

      <div className="mt-6 rounded-2xl border border-border bg-white">
        <div className="flex flex-col gap-3 border-b border-border px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold">卖点推荐语</p>
            <p className="mt-1 text-xs text-muted-foreground">
              共 {(concepts.data ?? []).length} 个卖点，留空时搜索结果沿用系统兜底解释。
            </p>
          </div>
          <div className="relative sm:w-72">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="搜索卖点"
              className="pl-9"
            />
          </div>
        </div>

        <div className="divide-y divide-border">
          {filtered.map((concept) => {
            const draft = splitRecommendationDraft(drafts[concept.id] ?? '');
            const unchanged = draft.trim() === (concept.recommendationText ?? '').trim();
            const saving = actions.updateConcept.isPending;
            return (
              <section key={concept.id} className="grid gap-4 px-4 py-4 lg:grid-cols-[260px_minmax(0,1fr)_auto] lg:items-start">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <MessageSquareText className="size-4 text-muted-foreground" />
                    <h2 className="truncate text-sm font-semibold">{concept.name}</h2>
                    {concept.recommendationText?.trim() ? (
                      <Badge variant="secondary">已维护</Badge>
                    ) : (
                      <Badge variant="outline">未维护</Badge>
                    )}
                  </div>
                  <p className="mt-1 truncate text-xs text-muted-foreground">{concept.code}</p>
                </div>
                <div className="space-y-2">
                  <Input
                    value={draft.primary}
                    onChange={(event) => updateDraftPart(
                      setDrafts,
                      concept.id,
                      { primary: event.target.value },
                    )}
                    maxLength={5000}
                    className="h-10 bg-secondary/25"
                    placeholder={`核心表达：业务方搜索命中“${concept.name}”时优先看到的主句`}
                  />
                  <textarea
                    value={draft.secondary}
                    onChange={(event) => updateDraftPart(
                      setDrafts,
                      concept.id,
                      { secondary: event.target.value },
                    )}
                    maxLength={5000}
                    className="min-h-20 w-full resize-y rounded-xl border border-border bg-secondary/25 px-3 py-2 text-sm leading-6 text-muted-foreground outline-none transition focus:border-primary focus:bg-white focus:text-foreground focus:ring-2 focus:ring-primary/15"
                    placeholder="补充说明：可选，展示为二级灰色说明"
                  />
                </div>
                <Button
                  className="lg:mt-0"
                  variant={unchanged ? 'outline' : 'default'}
                  disabled={unchanged || saving}
                  onClick={() => save(concept)}
                >
                  {saving ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}
                  保存
                </Button>
              </section>
            );
          })}
          {filtered.length === 0 && (
            <div className="grid min-h-48 place-items-center text-sm text-muted-foreground">
              没有找到对应卖点
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function splitRecommendationDraft(value: string): {
  primary: string;
  secondary: string;
  trim: () => string;
} {
  const [primary = '', ...secondary] = value.split(/\r?\n/);
  return {
    primary,
    secondary: secondary.join('\n'),
    trim: () => joinRecommendationDraft(primary, secondary.join('\n')).trim(),
  };
}

function joinRecommendationDraft(primary: string, secondary: string): string {
  return [primary.trim(), secondary.trim()].filter(Boolean).join('\n');
}

function updateDraftPart(
  setDrafts: React.Dispatch<React.SetStateAction<Record<string, string>>>,
  conceptId: string,
  patch: { primary?: string; secondary?: string },
) {
  setDrafts((items) => {
    const current = splitRecommendationDraft(items[conceptId] ?? '');
    return {
      ...items,
      [conceptId]: joinRecommendationDraft(
        patch.primary ?? current.primary,
        patch.secondary ?? current.secondary,
      ),
    };
  });
}
