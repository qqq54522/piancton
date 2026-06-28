import { ArrowUpDown, Search, X } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@client/src/components/ui/dropdown-menu';

interface LocalImageToolbarProps {
  searchInput: string;
  filterCategory?: string;
  sortBy: 'createdAt' | 'downloadCount';
  onSearchInputChange: (value: string) => void;
  onKeywordChange: (value: string) => void;
  onFilterCategoryChange: (value: string | undefined) => void;
  onSortByChange: (value: 'createdAt' | 'downloadCount') => void;
}

const LocalImageToolbar = ({
  searchInput,
  filterCategory,
  sortBy,
  onSearchInputChange,
  onKeywordChange,
  onFilterCategoryChange,
  onSortByChange,
}: LocalImageToolbarProps) => (
  <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
    <div className="relative flex-1">
      <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        placeholder="搜索标题、标签、业务表达..."
        value={searchInput}
        onChange={(event) => onSearchInputChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter') onKeywordChange(searchInput);
        }}
        className="pl-9"
      />
      {searchInput && (
        <button
          type="button"
          onClick={() => {
            onSearchInputChange('');
            onKeywordChange('');
          }}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        >
          <X className="size-4" />
        </button>
      )}
    </div>
    <Button variant="outline" size="sm" onClick={() => onKeywordChange(searchInput)}>
      搜索
    </Button>
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <ArrowUpDown className="mr-1.5 size-4" />
          {filterCategory === 'scene'
            ? '筛选场景'
            : filterCategory === 'function'
            ? '筛选功能'
            : sortBy === 'downloadCount'
            ? '下载量'
            : '最新上传'}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => {
          onSortByChange('createdAt');
          onFilterCategoryChange(undefined);
        }}>
          最新上传
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => {
          onSortByChange('downloadCount');
          onFilterCategoryChange(undefined);
        }}>
          下载量最多
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => onFilterCategoryChange(
            filterCategory === 'scene' ? undefined : 'scene',
          )}
          className={filterCategory === 'scene' ? 'bg-primary/10 font-medium text-primary' : ''}
        >
          筛选场景
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => onFilterCategoryChange(
            filterCategory === 'function' ? undefined : 'function',
          )}
          className={filterCategory === 'function' ? 'bg-primary/10 font-medium text-primary' : ''}
        >
          筛选功能
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
);

export default LocalImageToolbar;
