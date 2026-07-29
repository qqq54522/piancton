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
  <div className="mt-8 flex items-center justify-between gap-4">
    <div>
      <div className="flex items-baseline gap-2">
        <h2 className="text-xl font-semibold tracking-normal">全部素材</h2>
        {imageCount > 0 && <span className="text-xs text-muted-foreground">{imageCount} 组</span>}
      </div>
    </div>
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="rounded-full bg-white">
          <ArrowUpDown className="size-4" />
          {sortBy === 'downloadCount' ? '下载较多' : '最近上传'}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-40 rounded-xl p-1.5">
        <DropdownMenuItem className="justify-between rounded-lg" onClick={() => onSortByChange('createdAt')}>
          <span>最近上传</span>
          {sortBy === 'createdAt' && <Check className="size-4" />}
        </DropdownMenuItem>
        <DropdownMenuItem className="justify-between rounded-lg" onClick={() => onSortByChange('downloadCount')}>
          <span>下载较多</span>
          {sortBy === 'downloadCount' && <Check className="size-4" />}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
);

export default LocalImageToolbar;
