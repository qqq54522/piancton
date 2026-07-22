import { ChevronDown, Search, SlidersHorizontal, Sparkles, X } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Input } from '@client/src/components/ui/input';
import { Select } from '@client/src/components/ui/select';
import type {
  BusinessConcept,
  BusinessFacetCatalog,
  TagWithCount,
} from '@client/src/types/api';
import {
  activeRefinementCount,
  type SceneImageFilter,
  type SearchRefinementOptions,
  type SearchRefinements,
} from './searchResultFilters';

interface GlobalImageSearchProps {
  input: string;
  systems: TagWithCount[];
  selectedSystemCode: string | null;
  selectedConceptCode: string | null;
  selectedProofPointCode: string | null;
  selectedEvidencePointCode: string | null;
  businessConcepts: BusinessConcept[];
  businessFacets: BusinessFacetCatalog;
  refinementOptions: SearchRefinementOptions;
  refinements: SearchRefinements;
  refinementsReady: boolean;
  onInputChange: (value: string) => void;
  onSystemChange: (value: string | null) => void;
  onConceptChange: (value: string | null) => void;
  onProofPointChange: (value: string | null) => void;
  onEvidencePointChange: (value: string | null) => void;
  onChannelChange: (value: string) => void;
  onStyleChange: (value: string) => void;
  onSceneChange: (value: SceneImageFilter) => void;
  onClear: () => void;
  onSearch: (value?: string) => void;
}

const GlobalImageSearch = ({
  input,
  systems,
  selectedSystemCode,
  selectedConceptCode,
  selectedProofPointCode,
  selectedEvidencePointCode,
  businessConcepts,
  businessFacets,
  refinementOptions,
  refinements,
  refinementsReady,
  onInputChange,
  onSystemChange,
  onConceptChange,
  onProofPointChange,
  onEvidencePointChange,
  onChannelChange,
  onStyleChange,
  onSceneChange,
  onClear,
  onSearch,
}: GlobalImageSearchProps) => {
  const [refinementsOpen, setRefinementsOpen] = useState(false);
  const activeCount = activeRefinementCount(refinements);
  const selectedSystem = systems.find((system) => system.code === selectedSystemCode);
  const visibleConcepts = selectedSystem
    ? businessConcepts.filter((concept) => concept.systemLinks.some(
      (link) => link.systemTagId === selectedSystem.id && link.status === 'active',
    ))
    : businessConcepts;
  const visibleProofPoints = businessFacets.proofPoints.filter(
    (point) => point.conceptCode === selectedConceptCode,
  );
  const visibleEvidencePoints = businessFacets.evidencePoints.filter(
    (point) => point.proofPointCode === selectedProofPointCode,
  );
  useEffect(() => {
    if (activeCount > 0) setRefinementsOpen(true);
  }, [activeCount]);

  return (
  <section className="relative mt-7 overflow-hidden rounded-[28px] border border-primary/10 bg-gradient-to-br from-indigo-50 via-card to-sky-50/70 px-4 py-5 shadow-sm sm:px-6 sm:py-6">
    <div className="pointer-events-none absolute -right-16 -top-20 size-56 rounded-full bg-primary/8 blur-3xl" />
    <div className="relative">
      <div className="mb-3 flex items-center gap-2 text-xs font-medium text-accent-foreground">
        <Sparkles className="size-4" />统一搜索会自动理解卖点、痛点、画面与使用场景
      </div>
      <div className="relative max-w-4xl">
        <Search className="absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted-foreground/70" />
        <Input
          aria-label="搜索业务素材"
          placeholder="例如：家长不用盯学习、蓝色竖版学习周报、孩子拍题只抄答案"
          value={input}
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') onSearch();
          }}
          className="h-14 rounded-2xl border-white/80 bg-white pl-12 pr-28 text-base shadow-md shadow-slate-900/5 md:text-base"
        />
        {input && (
          <button
            type="button"
            aria-label="清空搜索"
            onClick={onClear}
            className="absolute right-24 top-1/2 z-10 flex size-8 -translate-y-1/2 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            <X className="size-4" />
          </button>
        )}
        <button
          type="button"
          onClick={() => onSearch()}
          className="absolute right-2 top-1/2 z-10 flex h-10 -translate-y-1/2 items-center rounded-xl bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition hover:brightness-[0.97] active:translate-y-[calc(-50%+1px)]"
        >
          搜索素材
        </button>
      </div>

      <div className="mt-4 flex flex-col gap-2.5 lg:flex-row lg:items-center" aria-label="六大体系筛选">
        <div className="flex shrink-0 items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <SlidersHorizontal className="size-3.5" />按体系缩小范围
          <span className="font-normal text-muted-foreground/70">（可选）</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onSystemChange(null)}
            className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-all ${selectedSystemCode === null ? 'border-primary/20 bg-primary text-primary-foreground shadow-sm' : 'border-white bg-white/80 text-muted-foreground hover:border-primary/25 hover:text-foreground'}`}
          >
            全部体系
          </button>
          {systems.map((system) => (
            <button
              key={system.id}
              type="button"
              onClick={() => onSystemChange(system.code ?? null)}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-all ${selectedSystemCode === system.code ? 'border-primary/20 bg-primary text-primary-foreground shadow-sm' : 'border-white bg-white/80 text-muted-foreground hover:border-primary/25 hover:text-foreground'}`}
            >
              {system.name.replace(/体系$/, '')}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 grid gap-3 border-t border-primary/10 pt-3 sm:grid-cols-3">
        <label className="block">
          <span className="field-label">卖点</span>
          <Select
            aria-label="按卖点筛选"
            value={selectedConceptCode ?? ''}
            onChange={(event) => onConceptChange(event.target.value || null)}
          >
            <option value="">全部卖点</option>
            {visibleConcepts.map((concept) => (
              <option key={concept.code} value={concept.code}>{concept.name}</option>
            ))}
          </Select>
        </label>
        <label className="block">
          <span className="field-label">证明点</span>
          <Select
            aria-label="按证明点筛选"
            value={selectedProofPointCode ?? ''}
            disabled={!selectedConceptCode}
            onChange={(event) => onProofPointChange(event.target.value || null)}
          >
            <option value="">全部证明点</option>
            {visibleProofPoints.map((point) => (
              <option key={point.code} value={point.code}>{point.name}</option>
            ))}
          </Select>
        </label>
        <label className="block">
          <span className="field-label">证据表达点</span>
          <Select
            aria-label="按证据表达点筛选"
            value={selectedEvidencePointCode ?? ''}
            disabled={!selectedProofPointCode}
            onChange={(event) => onEvidencePointChange(event.target.value || null)}
          >
            <option value="">全部证据表达点</option>
            {visibleEvidencePoints.map((point) => (
              <option key={point.code} value={point.code}>{point.name}</option>
            ))}
          </Select>
        </label>
        <p className="text-[11px] leading-5 text-muted-foreground sm:col-span-3">
          搜索会自动选中识别到的业务层级；不准确时可在这里逐层改选，结果会按所选层级重新匹配。
        </p>
      </div>

      <div className="mt-3 border-t border-primary/10 pt-3">
        <button
          type="button"
          aria-expanded={refinementsOpen}
          onClick={() => setRefinementsOpen((value) => !value)}
          className="flex w-full items-center justify-between gap-3 rounded-xl px-1 py-1 text-left"
        >
          <span className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <SlidersHorizontal className="size-3.5" />精细筛选
            <span className="font-normal text-muted-foreground/70">（推荐结果后再缩小）</span>
            {activeCount > 0 && (
              <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-primary-foreground">
                已选 {activeCount}
              </span>
            )}
          </span>
          <ChevronDown className={`mr-1 size-4 text-muted-foreground transition-transform ${refinementsOpen ? 'rotate-180' : ''}`} />
        </button>

        {refinementsOpen && (
          <div className="mt-3 grid gap-3 rounded-2xl border border-white/90 bg-white/65 p-3 shadow-sm sm:grid-cols-3">
            <label className="block">
              <span className="field-label">使用渠道</span>
              <Select
                aria-label="按使用渠道筛选"
                value={refinements.channel}
                disabled={!refinementsReady || refinementOptions.channels.length === 0}
                onChange={(event) => onChannelChange(event.target.value)}
              >
                <option value="">全部渠道</option>
                {refinementOptions.channels.map((channel) => (
                  <option key={channel} value={channel}>{channel}</option>
                ))}
              </Select>
            </label>
            <label className="block">
              <span className="field-label">画面风格</span>
              <Select
                aria-label="按画面风格筛选"
                value={refinements.style}
                disabled={!refinementsReady || refinementOptions.styles.length === 0}
                onChange={(event) => onStyleChange(event.target.value)}
              >
                <option value="">全部风格</option>
                {refinementOptions.styles.map((style) => (
                  <option key={style} value={style}>{style}</option>
                ))}
              </Select>
            </label>
            <label className="block">
              <span className="field-label">图片类型</span>
              <Select
                aria-label="按场景图筛选"
                value={refinements.scene}
                disabled={!refinementsReady || !refinementOptions.hasKnownSceneType}
                onChange={(event) => onSceneChange(event.target.value as SceneImageFilter)}
              >
                <option value="all">全部类型</option>
                <option value="scene">只看场景图</option>
                <option value="nonScene">只看非场景图</option>
              </Select>
            </label>
            <p className="text-[11px] leading-5 text-muted-foreground sm:col-span-3">
              {refinementsReady
                ? '筛选不会重新调用 AI，也不会改变推荐顺序；未标注的素材不会被误判为“非场景图”。'
                : '完成一次搜索后，可按设计师人工维护的渠道、风格和场景图标记继续筛选。'}
            </p>
          </div>
        )}
      </div>
    </div>
  </section>
  );
};

export default GlobalImageSearch;
