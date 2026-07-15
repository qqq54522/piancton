import { useEffect } from 'react';
import { Loader2, Network, Sparkles } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';

import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { useBusinessConcepts } from '@client/src/features/assets/useBusinessConcepts';
import ConceptList from './ConceptList';
import ConceptPhraseEditor from './ConceptPhraseEditor';

export default function AdminConcepts() {
  const concepts = useBusinessConcepts();
  const [params, setParams] = useSearchParams();
  const selectedId = params.get('concept') ?? undefined;
  const selected = concepts.data?.find((concept) => concept.id === selectedId)
    ?? concepts.data?.[0];

  useEffect(() => {
    if (!selectedId && selected) setParams({ concept: selected.id }, { replace: true });
  }, [selected, selectedId, setParams]);

  if (concepts.isLoading) {
    return <div className="grid min-h-[60vh] place-items-center"><Loader2 className="size-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="page-shell">
      <PageHeader
        eyebrow="Selling Point Language"
        title="卖点与公共话术"
        description="公共话术在卖点层只维护一次，所有关联素材自动继承；单张图片的画面和文案差异继续留在素材详情。"
      />

      <div className="mt-6 grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
        <ConceptList
          concepts={concepts.data ?? []}
          selectedId={selected?.id}
          onSelect={(conceptId) => setParams({ concept: conceptId })}
        />

        {selected ? (
          <main className="surface-card p-5 sm:p-6">
            <div className="flex flex-col gap-4 border-b border-border pb-5 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-xl font-semibold tracking-tight">{selected.name}</h2>
                  <Badge variant="outline">v{selected.version}</Badge>
                </div>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                  {selected.definition || '暂未补充卖点定义。公共话术应描述业务人员可能如何表达这个卖点。'}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {selected.systemLinks.map((link) => (
                  <Badge key={link.systemTagId} variant="secondary">
                    <Network className="mr-1 size-3" />{link.systemName}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="my-5 flex gap-3 rounded-2xl border border-blue-100 bg-blue-50/70 px-4 py-3 text-sm leading-6 text-blue-900">
              <Sparkles className="mt-1 size-4 shrink-0 text-blue-600" />
              <p>AI建议和搜索反馈只作为候选来源；确认、修改或停用后，才会进入正式公共话术并影响关联素材搜索。</p>
            </div>

            <ConceptPhraseEditor concept={selected} />
          </main>
        ) : (
          <div className="surface-card grid min-h-80 place-items-center text-sm text-muted-foreground">
            暂无可管理的卖点概念
          </div>
        )}
      </div>
    </div>
  );
}
