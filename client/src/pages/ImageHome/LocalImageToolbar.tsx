import { ArrowUpDown, Check } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@client/src/components/ui/dropdown-menu';

interface LocalImageToolbarProps {
  imageCount: number;
  sortBy: 'createdAt' | 'downloadCount';
  onSortByChange: (value: 'createdAt' | 'downloadCount') => void;
}

const LocalImageToolbar = ({ imageCount, sortBy, onSortByChange }: LocalImageToolbarProps) => (
  <div className="mt-9 flex items-end justify-between gap-4">
    <div>
      <p className="section-kicker">Browse</p>
      <div className="mt-1 flex items-baseline gap-2">
        <h2 className="text-xl font-semibold tracking-tight">全部素材</h2>
        {imageCount > 0 && <span className="text-xs text-muted-foreground">已加载 {imageCount} 组</span>}
      </div>
    </div>
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <ArrowUpDown className="size-4" />
          {sortBy === 'downloadCount' ? '下载较多' : '最近上传'}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-40 rounded-xl p-1.5">
        <DropdownMenuItem className="rounded-lg" onClick={() => onSortByChange('createdAt')}>
          {sortBy === 'createdAt' && <Check className="size-4" />}最近上传
        </DropdownMenuItem>
        <DropdownMenuItem className="rounded-lg" onClick={() => onSortByChange('downloadCount')}>
          {sortBy === 'downloadCount' && <Check className="size-4" />}下载较多
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
);

export default LocalImageToolbar;
