import { Search, Sparkles, X } from 'lucide-react';

import { Input } from '@client/src/components/ui/input';
import type { SearchMode, TagWithCount } from '@client/src/types/api';

interface GlobalImageSearchProps {
  input: string;
  keyword: string;
  mode: SearchMode;
  suggestedTags: TagWithCount[];
  onInputChange: (value: string) => void;
  onModeChange: (value: SearchMode) => void;
  onClear: () => void;
  onSearch: (value?: string) => void;
  onTagSuggestClick: (tag: TagWithCount) => void;
}

const GlobalImageSearch = ({
  input,
  keyword,
  mode,
  suggestedTags,
  onInputChange,
  onModeChange,
  onClear,
  onSearch,
  onTagSuggestClick,
}: GlobalImageSearchProps) => (
  <div className="relative mt-5">
    <div className="relative mx-auto max-w-2xl">
      <Search className="absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted-foreground/60" />
      <Input
        placeholder="搜索标签或图片..."
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
          onClick={onClear}
          className="absolute right-20 top-1/2 z-10 flex h-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground transition-colors hover:text-foreground"
        >
          <X className="size-4" />
        </button>
      )}
      <button
        type="button"
        onClick={() => onSearch()}
        className="absolute right-2 top-1/2 z-10 flex h-8 -translate-y-1/2 items-center whitespace-nowrap rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
      >
        搜索
      </button>
    </div>
    <div className="mx-auto mt-2 flex max-w-2xl items-center justify-center gap-2 text-xs">
      <button
        type="button"
        onClick={() => onModeChange('precise')}
        className={`rounded-full border px-3 py-1 transition-colors ${mode === 'precise' ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background text-muted-foreground hover:text-foreground'}`}
        title="适合搜索完整标题、明确标签、六大体系或二级分类"
      >
        精准搜索
      </button>
      <button
        type="button"
        onClick={() => onModeChange('smart')}
        className={`inline-flex items-center rounded-full border px-3 py-1 transition-colors ${mode === 'smart' ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background text-muted-foreground hover:text-foreground'}`}
        title="适合搜索一句模糊需求、家长痛点或业务表达；不可用时会自动兜底"
      >
        <Sparkles className="mr-1 size-3" />
        智能搜索
      </button>
    </div>
    {input.trim() && suggestedTags.length > 0 && !keyword && (
      <div className="absolute left-0 right-0 z-50 mx-auto mt-1 max-w-2xl overflow-hidden rounded-xl border border-border bg-popover p-2 shadow-lg">
        <p className="mb-1.5 px-2 text-xs font-medium text-muted-foreground">匹配标签</p>
        {suggestedTags.map((tag) => (
          <button
            key={tag.id}
            type="button"
            onClick={() => onTagSuggestClick(tag)}
            className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-accent"
          >
            <span
              className="size-2.5 flex-shrink-0 rounded-full"
              style={{ backgroundColor: tag.color || '#6B7280' }}
            />
            <span className="flex-1 text-sm text-foreground">{tag.name}</span>
            <span className="text-xs text-muted-foreground">{tag.imageCount ?? 0} 张</span>
          </button>
        ))}
      </div>
    )}
  </div>
);

export default GlobalImageSearch;
