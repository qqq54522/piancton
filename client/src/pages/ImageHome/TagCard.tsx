import { Link } from 'react-router-dom';
import { ChevronRight, FolderOpen } from 'lucide-react';
import type { TagWithCount } from '@client/src/types/api';

interface TagCardProps {
  tag: TagWithCount;
}

const TagCard = ({ tag }: TagCardProps) => {
  const color = tag.color || '#6B7280';

  return (
    <Link
      to={`/tag/${tag.id}`}
      className="group block overflow-hidden rounded-xl border border-border bg-card shadow-sm transition-all duration-200 hover:-translate-y-1 hover:shadow-md"
    >
      <div className="relative aspect-[4/3] overflow-hidden">
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{ background: `linear-gradient(135deg, ${color}, transparent 60%)` }}
        />
        <div className="flex size-full flex-col items-center justify-center gap-3">
          <div
            className="flex size-14 items-center justify-center rounded-2xl shadow-sm"
            style={{ backgroundColor: `${color}18` }}
          >
            <FolderOpen className="size-7" style={{ color }} />
          </div>
          <h3
            className="line-clamp-2 max-w-[80%] text-center text-sm font-semibold text-foreground"
          >
            {tag.name || '未命名'}
          </h3>
        </div>
      </div>
      <div className="flex items-center justify-between px-4 py-2.5">
        <span className="text-xs text-muted-foreground">
          {tag.imageCount} 张图片
        </span>
        <ChevronRight
          className="size-4 text-muted-foreground/50 transition-transform group-hover:translate-x-1"
        />
      </div>
    </Link>
  );
};

export default TagCard;
