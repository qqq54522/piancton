import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Images, Loader2 } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';

import { fetchBusinessConceptAssets } from '@client/src/api/asset';
import { getApiError } from '@client/src/api/client';
import EmptyState from '@client/src/components/EmptyState';
import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { useBusinessConcepts } from '@client/src/features/assets/useBusinessConcepts';
import { previewUrlFor } from '@client/src/features/images/imagePreview';
import { useTags } from '@client/src/features/tags/useTags';
import { useImageUrl } from '@client/src/hooks/useImageUrl';
import type { BusinessConcept, BusinessConceptAsset } from '@client/src/types/api';
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
  const conceptsBySystem = useMemo(() => {
    const grouped = new Map<string, BusinessConcept[]>();
    systems.forEach((system) => {
      grouped.set(
        system.id,
        (concepts.data ?? []).filter((concept) => concept.systemLinks.some(
          (link) => link.systemTagId === system.id && link.role === 'core',
        )),
      );
    });
    return grouped;
  }, [concepts.data, systems]);

  const requestedSystemId = params.get('system') ?? undefined;
  const requestedConceptId = params.get('concept') ?? undefined;
  const selectedSystem = systems.find((system) => system.id === requestedSystemId) ?? systems[0];
  const selectedConcepts = selectedSystem ? conceptsBySystem.get(selectedSystem.id) ?? [] : [];
  const selectedConcept = selectedConcepts.find((concept) => concept.id === requestedConceptId)
    ?? selectedConcepts[0];
  const [expandedSystemIds, setExpandedSystemIds] = useState<Set<string>>(new Set());
  const assets = useQuery({
    queryKey: ['business-concept-assets', selectedConcept?.id],
    queryFn: () => fetchBusinessConceptAssets(selectedConcept!.id),
    enabled: Boolean(selectedConcept),
  });

  useEffect(() => {
    if (!selectedSystem || !selectedConcept) return;
    setExpandedSystemIds((current) => {
      if (current.has(selectedSystem.id)) return current;
      return new Set([...current, selectedSystem.id]);
    });
    if (requestedSystemId !== selectedSystem.id || requestedConceptId !== selectedConcept.id) {
      setParams({ system: selectedSystem.id, concept: selectedConcept.id }, { replace: true });
    }
  }, [requestedConceptId, requestedSystemId, selectedConcept, selectedSystem, setParams]);

  if (concepts.isLoading || tags.isLoading) {
    return <div className="grid min-h-[60vh] place-items-center"><Loader2 className="size-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="page-shell flex lg:h-screen lg:flex-col lg:overflow-hidden">
      <PageHeader title="业务卖点管理" />

      <div
        aria-label="业务体系和核心卖点"
        className="mt-6 grid gap-5 lg:min-h-0 lg:flex-1 lg:grid-cols-[320px_minmax(0,1fr)]"
      >
        <SystemList
          systems={systems}
          conceptsBySystem={conceptsBySystem}
          selectedSystemId={selectedSystem?.id}
          selectedConceptId={selectedConcept?.id}
          expandedSystemIds={expandedSystemIds}
          onToggleSystem={(systemId) => setExpandedSystemIds((current) => {
            const next = new Set(current);
            if (next.has(systemId)) next.delete(systemId);
            else next.add(systemId);
            return next;
          })}
          onSelectConcept={(systemId, conceptId) => {
            setExpandedSystemIds((current) => new Set([...current, systemId]));
            setParams({ system: systemId, concept: conceptId });
          }}
        />

        {selectedSystem && selectedConcept ? (
          <main className="surface-card flex min-h-0 flex-col overflow-hidden">
            <div className="shrink-0 border-b border-border px-5 py-5 sm:px-6">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{selectedSystem.name}</Badge>
                <Badge variant="secondary">{assets.data?.length ?? 0} 张图片</Badge>
              </div>
              <h2 className="mt-3 text-xl font-semibold tracking-tight">{selectedConcept.name}</h2>
              {selectedConcept.definition && (
                <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
                  {selectedConcept.definition}
                </p>
              )}
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto p-5 compact-scrollbar sm:p-6">
              {assets.isLoading ? (
                <div className="grid min-h-72 place-items-center"><Loader2 className="size-5 animate-spin text-muted-foreground" /></div>
              ) : assets.isError ? (
                <p className="text-sm text-destructive">{getApiError(assets.error).message}</p>
              ) : assets.data?.length ? (
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                  {assets.data.map((asset) => <ConceptAssetCard key={asset.image.id} asset={asset} />)}
                </div>
              ) : (
                <EmptyState
                  icon={<Images className="size-5" />}
                  title="这个卖点还没有对应图片"
                />
              )}
            </div>
          </main>
        ) : (
          <div className="surface-card grid min-h-80 place-items-center text-sm text-muted-foreground">
            暂无可管理的业务卖点
          </div>
        )}
      </div>
    </div>
  );
}

function ConceptAssetCard({ asset }: { asset: BusinessConceptAsset }) {
  const { image } = asset;
  const preview = useImageUrl(previewUrlFor(image));
  const dimensions = image.width && image.height ? `${image.width} × ${image.height}` : '尺寸未知';
  return (
    <Link
      to={`/image/${image.id}`}
      className="group overflow-hidden rounded-2xl border border-border/80 bg-white transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="aspect-[4/3] overflow-hidden bg-secondary">
        <img
          src={preview}
          alt={image.title}
          loading="lazy"
          className="size-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
        />
      </div>
      <div className="p-3.5">
        <div className="flex items-start justify-between gap-3">
          <h3 className="min-w-0 flex-1 truncate text-sm font-semibold">{image.title}</h3>
          <Badge variant={asset.relationRole === 'expresses' ? 'default' : 'outline'} className="shrink-0 text-[10px]">
            {asset.relationRole === 'expresses' ? '主要表达' : '可以支持'}
          </Badge>
        </div>
        <p className="mt-2 font-mono text-xs text-foreground/80">{image.identityCode || '暂无身份码'}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {[image.channel, dimensions].filter(Boolean).join(' · ')}
        </p>
      </div>
    </Link>
  );
}
