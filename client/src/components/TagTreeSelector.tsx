import { useState, useMemo } from 'react';
import { ChevronRight, ChevronDown, Check, X } from 'lucide-react';
import { Badge } from '@client/src/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@client/src/components/ui/popover';
import type { TagWithCount } from '@client/src/types/api';
import { buildTagTree, type TagTreeNode } from '@client/src/utils/tagTree';

interface TagTreeSelectorProps {
  tags: TagWithCount[];
  selectedIds: string[];
  onToggle: (tagId: string) => void;
  placeholder?: string;
  expandable?: boolean;
  assignableOnly?: boolean;
}

const TagTreeNodeItem = ({
  node,
  selectedIds,
  onToggle,
  assignableOnly,
}: {
  node: TagTreeNode;
  selectedIds: string[];
  onToggle: (id: string) => void;
  assignableOnly: boolean;
}) => {
  const [expanded, setExpanded] = useState(true);
  const selected = selectedIds.includes(node.id);
  const hasChildren = node.children.length > 0;
  const selectable = !assignableOnly || (node.assignable && node.status === 'active');

  return (
    <div>
      <div
        className="flex items-center gap-1.5 rounded-md px-2 py-1.5"
        style={{ paddingLeft: `${node.depth * 16 + 8}px` }}
      >
        {hasChildren ? (
          <button
            type="button"
            aria-label={`${expanded ? '收起' : '展开'}${node.name || '未命名标签'}`}
            aria-expanded={expanded}
            onClick={() => setExpanded(!expanded)}
            className="rounded p-0.5 text-muted-foreground hover:text-foreground"
          >
            {expanded
              ? <ChevronDown className="size-3.5" />
              : <ChevronRight className="size-3.5" />}
          </button>
        ) : (
          <span className="w-4.5" />
        )}
        <button
          type="button"
          role="checkbox"
          aria-checked={selected}
          aria-label={`${selectable ? (selected ? '取消选择' : '选择') : '不可选择'}标签：${node.name || '未命名'}`}
          disabled={!selectable}
          title={selectable ? undefined : '该标签当前不可直接用于图片打标'}
          onClick={() => onToggle(node.id)}
          className={`flex min-w-0 flex-1 items-center gap-1.5 rounded px-1 py-0.5 text-left transition-colors ${
            selectable ? 'cursor-pointer hover:bg-accent' : 'cursor-not-allowed opacity-70'
          }`}
        >
          <span
            aria-hidden="true"
            className={`flex size-4 shrink-0 items-center justify-center rounded border text-[10px] transition-colors ${
              selected
                ? 'border-primary bg-primary text-primary-foreground'
                : selectable ? 'border-muted-foreground/30' : 'border-muted-foreground/10 bg-muted'
            }`}
          >
            {selected && <Check className="size-3" />}
          </span>
          <span
            className="flex-1 truncate text-xs"
            style={{ color: node.color || '#6B7280' }}
          >
            {node.name || '未命名'}
          </span>
        </button>
      </div>
      {hasChildren && expanded && node.children.map((child) => (
        <TagTreeNodeItem
          key={child.id}
          node={child}
          selectedIds={selectedIds}
          onToggle={onToggle}
          assignableOnly={assignableOnly}
        />
      ))}
    </div>
  );
};

const TagTreeSelector = ({
  tags,
  selectedIds,
  onToggle,
  placeholder = '选择标签',
  expandable = false,
  assignableOnly = false,
}: TagTreeSelectorProps) => {
  const [open, setOpen] = useState(false);
  const tree = buildTagTree(tags);
  const tagMap = useMemo(() => {
    const m = new Map(tags.map((t) => [t.id, t]));
    return m;
  }, [tags]);

  const selectedTags = useMemo(() => {
    const childParentIds = new Set(
      tags.filter((t) => t.parentId && selectedIds.includes(t.id)).map((t) => t.parentId!),
    );
    return tags
      .filter((t) => selectedIds.includes(t.id) && !childParentIds.has(t.id))
      .map((t) => ({
        ...t,
        parentName: t.parentId ? tagMap.get(t.parentId)?.name : undefined,
      }));
  }, [tags, selectedIds, tagMap]);

  const treeContent = (
    <div className="space-y-0.5">
      {tree.map((node) => (
        <TagTreeNodeItem
          key={node.id}
          node={node}
          selectedIds={selectedIds}
          onToggle={onToggle}
          assignableOnly={assignableOnly}
        />
      ))}
      {tags.length === 0 && (
        <p className="py-4 text-center text-xs text-muted-foreground">暂无标签</p>
      )}
    </div>
  );

  if (expandable) {
    return (
      <div
        role="group"
        aria-label="标签树，只能选择允许打标的标签"
        className="max-h-48 overflow-y-auto rounded-md border border-border p-2"
      >
        {treeContent}
      </div>
    );
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={selectedTags.length ? `已选择 ${selectedTags.length} 个标签` : placeholder}
          className="flex min-h-[36px] w-full cursor-pointer flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-3 py-1.5 text-sm transition-colors hover:bg-accent"
        >
          {selectedTags.length === 0 ? (
            <span className="text-muted-foreground">{placeholder}</span>
          ) : (
            selectedTags.map((tag) => (
              <Badge
                key={tag.id}
                variant="secondary"
                className="text-[11px]"
                style={{
                  backgroundColor: `${tag.color || '#6B7280'}18`,
                  color: tag.color || '#6B7280',
                }}
                onClick={(e) => { e.stopPropagation(); onToggle(tag.id); }}
              >
                {tag.parentName ? `${tag.parentName} > ${tag.name || '未命名'}` : (tag.name || '未命名')}
                <X className="ml-1 size-3" />
              </Badge>
            ))
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent className="max-h-64 w-56 overflow-y-auto p-2" align="start">
        {treeContent}
      </PopoverContent>
    </Popover>
  );
};

export default TagTreeSelector;
