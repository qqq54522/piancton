import { Search, X } from 'lucide-react';

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
  <section className="mt-5 rounded-2xl border border-border bg-card px-4 py-5 shadow-sm">
    <div className="relative mx-auto max-w-2xl">
      <Search className="absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted-foreground/60" />
      <Input
        aria-label="搜索业务素材"
        placeholder="描述你想找的业务点、用户痛点或画面，例如：家长不用盯学习"
        value={input}
        onChange={(event) => onInputChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') onSearch();
        }}
        className="h-12 rounded-xl pl-11 pr-20 text-base shadow-sm md:text-base"
      />
      {input && (
        <button
          type="button"
          aria-label="清空搜索"
          onClick={onClear}
          className="absolute right-20 top-1/2 z-10 flex h-8 -translate-y-1/2 items-center text-muted-foreground hover:text-foreground"
        >
          <X className="size-4" />
        </button>
      )}
      <button
        type="button"
        onClick={() => onSearch()}
        className="absolute right-2 top-1/2 z-10 flex h-8 -translate-y-1/2 items-center rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground"
      >
        搜索
      </button>
    </div>
    <div className="mx-auto mt-3 flex max-w-4xl flex-wrap justify-center gap-2" aria-label="六大体系筛选">
      <button
        type="button"
        onClick={() => onSystemChange(null)}
        className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${selectedSystemCode === null ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background text-muted-foreground hover:text-foreground'}`}
      >
        全部体系
      </button>
      {systems.map((system) => (
        <button
          key={system.id}
          type="button"
          onClick={() => onSystemChange(system.code ?? null)}
          className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${selectedSystemCode === system.code ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background text-muted-foreground hover:text-foreground'}`}
        >
          {system.name}
        </button>
      ))}
    </div>
    <p className="mt-2 text-center text-xs text-muted-foreground">
      体系筛选是可选的；不选择时会同时查找所有相关素材。
    </p>
  </section>
);

export default GlobalImageSearch;
