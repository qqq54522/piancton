import { ArrowUpDown, Search, X } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@client/src/components/ui/dropdown-menu';

interface LocalImageToolbarProps {
  searchInput: string;
  sortBy: 'createdAt' | 'downloadCount';
  onSearchInputChange: (value: string) => void;
  onKeywordChange: (value: string) => void;
  onSortByChange: (value: 'createdAt' | 'downloadCount') => void;
}

const LocalImageToolbar = ({
  searchInput,
  sortBy,
  onSearchInputChange,
  onKeywordChange,
  onSortByChange,
}: LocalImageToolbarProps) => (
  <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
    <div className="relative flex-1">
      <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        placeholder="按标题、画面内容或业务表达查找..."
        value={searchInput}
        onChange={(event) => onSearchInputChange(event.target.value)}
        onKeyDown={(event) => event.key === 'Enter' && onKeywordChange(searchInput)}
        className="pl-9"
      />
      {searchInput && (
        <button
          type="button"
          onClick={() => { onSearchInputChange(''); onKeywordChange(''); }}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        >
          <X className="size-4" />
        </button>
      )}
    </div>
    <Button variant="outline" size="sm" onClick={() => onKeywordChange(searchInput)}>搜索</Button>
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <ArrowUpDown className="mr-1.5 size-4" />
          {sortBy === 'downloadCount' ? '下载量' : '最新上传'}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => onSortByChange('createdAt')}>最新上传</DropdownMenuItem>
        <DropdownMenuItem onClick={() => onSortByChange('downloadCount')}>下载量最多</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
);

export default LocalImageToolbar;
