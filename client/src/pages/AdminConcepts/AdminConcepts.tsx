import { useEffect, useMemo } from 'react';
import { Loader2, Tags } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';

import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { useBusinessConcepts } from '@client/src/features/assets/useBusinessConcepts';
import { useTags } from '@client/src/features/tags/useTags';
import SystemList from './SystemList';

export default function AdminConcepts() {
  const concepts = useBusinessConcepts();
  const tags = useTags();
  const [params, setParams] = useSearchParams();
  const systems = useMemo(
    () => (tags.data ?? [])
      .filter((tag) => tag.nodeType === 'system' && tag.status === 'active')
      .sort((left, right) => left.sortOrder - right.sortOrder),
    [tags.data],
  );
  const selectedId = params.get('system') ?? undefined;
  const selectedSystem = systems.find((system) => system.id === selectedId) ?? systems[0];
  const sellingPoints = useMemo(
    () => (concepts.data ?? []).filter((concept) => concept.systemLinks.some(
      (link) => link.systemTagId === selectedSystem?.id && link.role === 'core',
    )),
    [concepts.data, selectedSystem?.id],
  );

  useEffect(() => {
    if (!selectedId && selectedSystem) {
      setParams({ system: selectedSystem.id }, { replace: true });
    }
  }, [selectedId, selectedSystem, setParams]);

  if (concepts.isLoading || tags.isLoading) {
    return <div className="grid min-h-[60vh] place-items-center"><Loader2 className="size-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="page-shell flex lg:h-screen lg:flex-col lg:overflow-hidden">
      <PageHeader
        eyebrow="Business System Catalog"
        title="业务卖点管理"
        description="左侧选择业务体系，右侧查看这个体系下包含的核心卖点。"
      />

      <div className="mt-6 grid gap-5 lg:min-h-0 lg:flex-1 lg:grid-cols-[300px_minmax(0,1fr)]">
        <SystemList
          systems={systems}
          selectedId={selectedSystem?.id}
          sellingPointCount={(systemId) => (concepts.data ?? []).filter(
            (concept) => concept.systemLinks.some(
              (link) => link.systemTagId === systemId && link.role === 'core',
            ),
          ).length}
          onSelect={(systemId) => setParams({ system: systemId })}
        />

        {selectedSystem ? (
          <main className="surface-card flex min-h-0 flex-col overflow-hidden p-5 sm:p-6">
            <div className="shrink-0 border-b border-border pb-5">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-xl font-semibold tracking-tight">{selectedSystem.name}</h2>
                <Badge variant="secondary">{sellingPoints.length} 个核心卖点</Badge>
              </div>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                下面是当前归属于这个业务体系的卖点。
              </p>
            </div>

            {sellingPoints.length ? (
              <div className="mt-5 grid min-h-0 gap-4 overflow-y-auto pr-1 compact-scrollbar sm:grid-cols-2 xl:grid-cols-3">
                {sellingPoints.map((concept) => (
                  <article key={concept.id} className="rounded-2xl border border-border bg-secondary/20 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-white text-muted-foreground shadow-sm ring-1 ring-border/70">
                        <Tags className="size-4" />
                      </span>
                      <Badge variant={concept.status === 'active' ? 'secondary' : 'outline'}>
                        {concept.status === 'active' ? '启用中' : concept.status}
                      </Badge>
                    </div>
                    <h3 className="mt-4 text-base font-semibold">{concept.name}</h3>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {concept.definition || '暂未补充卖点说明。'}
                    </p>
                    <p className="mt-4 text-[11px] text-muted-foreground">Code：{concept.code}</p>
                  </article>
                ))}
              </div>
            ) : (
              <div className="grid min-h-80 place-items-center text-sm text-muted-foreground">
                这个体系下暂时没有核心卖点
              </div>
            )}
          </main>
        ) : (
          <div className="surface-card grid min-h-80 place-items-center text-sm text-muted-foreground">
            暂无可管理的业务体系
          </div>
        )}
      </div>
    </div>
  );
}
