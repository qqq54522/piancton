import { Search, SlidersHorizontal, Sparkles, X } from 'lucide-react';

import { Input } from '@client/src/components/ui/input';
import type { TagWithCount } from '@client/src/types/api';

interface GlobalImageSearchProps {
  input: string;
  systems: TagWithCount[];
  selectedSystemCode: string | null;
  onInputChange: (value: string) => void;
  onSystemChange: (value: string | null) => void;
  onClear: () => void;
  onSearch: (value?: string) => void;
}

const GlobalImageSearch = ({
  input,
  systems,
  selectedSystemCode,
  onInputChange,
  onSystemChange,
  onClear,
  onSearch,
}: GlobalImageSearchProps) => (
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
    </div>
  </section>
);

export default GlobalImageSearch;
