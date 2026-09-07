import { useEffect } from 'react';
import { Loader2, Network } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';

import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { useBusinessConcepts } from '@client/src/features/assets/useBusinessConcepts';
import ConceptList from './ConceptList';

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
    <div className="page-shell flex lg:h-screen lg:flex-col lg:overflow-hidden">
      <PageHeader
        eyebrow="Selling Point Catalog"
        title="业务卖点管理"
        description="维护 16 个核心卖点的业务归属。当前搜索由火山向量识别卖点，再返回该卖点下的素材。"
      />

      <div className="mt-6 grid gap-5 lg:min-h-0 lg:flex-1 lg:grid-cols-[300px_minmax(0,1fr)]">
        <ConceptList
          concepts={concepts.data ?? []}
          selectedId={selected?.id}
          onSelect={(conceptId) => setParams({ concept: conceptId })}
        />

        {selected ? (
          <main className="surface-card flex min-h-0 flex-col overflow-hidden p-5 sm:p-6">
            <div className="shrink-0 flex flex-col gap-4 border-b border-border pb-5 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-xl font-semibold tracking-tight">{selected.name}</h2>
                  <Badge variant="outline">v{selected.version}</Badge>
                  <Badge variant={selected.status === 'active' ? 'secondary' : 'outline'}>
                    {selected.status}
                  </Badge>
                </div>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                  {selected.definition || '暂未补充卖点定义。'}
                </p>
                <p className="mt-3 text-xs text-muted-foreground">Code：{selected.code}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {selected.systemLinks.map((link) => (
                  <Badge key={link.systemTagId} variant="secondary">
                    <Network className="mr-1 size-3" />{link.systemName}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <section className="rounded-2xl border border-border bg-secondary/25 p-4">
                <p className="text-sm font-semibold">当前搜索角色</p>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  作为火山向量路由命中后的本地素材归属标签。搜索命中该卖点后，系统返回人工确认属于该卖点的图库。
                </p>
              </section>
              <section className="rounded-2xl border border-border bg-secondary/25 p-4">
                <p className="text-sm font-semibold">上传使用方式</p>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  设计师上传主图时只选择主要表达卖点；证明点、证据点和公共话术不再作为上传必填流程。
                </p>
              </section>
            </div>
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
