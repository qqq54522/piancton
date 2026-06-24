import { useState, useMemo } from 'react';
import { Search, Check, RotateCcw } from 'lucide-react';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@client/src/components/ui/dialog';
import type { TagWithCount } from '@client/src/types/api';

interface FilterDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tags: TagWithCount[];
  onFilter: (tagIds: string[], keyword: string, category?: string) => void;
}

const FilterDialog = ({ open, onOpenChange, tags, onFilter }: FilterDialogProps) => {
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);
  const [filterKeyword, setFilterKeyword] = useState('');
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);

  const rootTags = useMemo(() => tags.filter((t) => !t.parentId), [tags]);

  const selectedAncestorPaths = useMemo(() => {
    if (selectedTagIds.length === 0) return [];
    const paths: string[][] = [];
    const buildPath = (tagId: string): string[] => {
      const chain: string[] = [tagId];
      let current = tags.find((t) => t.id === tagId);
      while (current?.parentId) {
        chain.unshift(current.parentId);
        current = tags.find((t) => t.id === current!.parentId);
      }
      return chain;
    };
    for (const id of selectedTagIds) {
      paths.push(buildPath(id));
    }
    return paths;
  }, [selectedTagIds, tags]);

  const visibleTagLevels = useMemo((): TagWithCount[][] => {
    const levels: TagWithCount[][] = [rootTags];

    if (selectedAncestorPaths.length === 0) return levels;

    const firstPath = selectedAncestorPaths[0];
    for (let depth = 0; depth < firstPath.length; depth++) {
      const children = tags.filter((t) => t.parentId === firstPath[depth]);
      if (children.length > 0) {
        levels.push(children);
      } else {
        break;
      }
    }

    return levels;
  }, [rootTags, selectedAncestorPaths, tags]);

  const handleTagClick = (tag: TagWithCount) => {
    const tagId = tag.id;

    const isSelected = selectedTagIds.includes(tagId);

    if (isSelected) {
      const descendants = new Set<string>();
      const collectDescendants = (id: string) => {
        descendants.add(id);
        tags.filter((t) => t.parentId === id).forEach((child) => collectDescendants(child.id));
      };
      collectDescendants(tagId);
      setSelectedTagIds((prev) => prev.filter((id) => !descendants.has(id)));
      return;
    }

    const depth = getTagDepth(tagId);
    const lowerDepth = selectedTagIds.filter((id) => getTagDepth(id) < depth);

    setSelectedTagIds([...lowerDepth, tagId]);
  };

  const getTagDepth = (tagId: string): number => {
    let depth = 0;
    let current = tags.find((t) => t.id === tagId);
    while (current?.parentId) {
      depth++;
      current = tags.find((t) => t.id === current!.parentId);
    }
    return depth;
  };

  const handleReset = () => {
    setSelectedTagIds([]);
    setFilterKeyword('');
    setSelectedCategories([]);
  };

  const handleConfirm = () => {
    const category = selectedCategories.length === 1 ? selectedCategories[0] : undefined;
    onFilter(selectedTagIds, filterKeyword.trim(), category);
    onOpenChange(false);
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      handleReset();
    }
    onOpenChange(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Search className="size-5" />
            精确查找
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-5 py-2">
          <div>
            <p className="mb-2 text-xs font-medium text-muted-foreground">图片分类（可选，单选）</p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => {
                  setSelectedCategories((prev) =>
                    prev.includes('scene') ? prev.filter((c) => c !== 'scene') : ['scene'],
                  );
                }}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-all ${
                  selectedCategories.includes('scene')
                    ? 'border-amber-400 bg-amber-50 font-medium text-amber-700 shadow-sm'
                    : 'border-border bg-background text-foreground hover:border-foreground/20 hover:bg-accent'
                }`}
              >
                {selectedCategories.includes('scene') && <Check className="size-3.5" />}
                场景
              </button>
              <button
                onClick={() => {
                  setSelectedCategories((prev) =>
                    prev.includes('function') ? prev.filter((c) => c !== 'function') : ['function'],
                  );
                }}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-all ${
                  selectedCategories.includes('function')
                    ? 'border-amber-400 bg-amber-50 font-medium text-amber-700 shadow-sm'
                    : 'border-border bg-background text-foreground hover:border-foreground/20 hover:bg-accent'
                }`}
              >
                {selectedCategories.includes('function') && <Check className="size-3.5" />}
                功能
              </button>
            </div>
          </div>

          {visibleTagLevels.map((levelTags, levelIdx) => (
            <div key={levelIdx}>
              <p className="mb-2 text-xs font-medium text-muted-foreground">
                {levelIdx === 0 ? '一级标签' : `${levelIdx + 1}级标签`}
              </p>
              <div className="flex flex-wrap gap-2">
                {levelTags.map((tag) => {
                  const isSelected = selectedTagIds.includes(tag.id);
                  return (
                    <button
                      key={tag.id}
                      onClick={() => handleTagClick(tag)}
                      className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-all ${
                        isSelected
                          ? 'border-amber-400 bg-amber-50 font-medium text-amber-700 shadow-sm'
                          : 'border-border bg-background text-foreground hover:border-foreground/20 hover:bg-accent'
                      }`}
                    >
                      {isSelected && <Check className="size-3.5" />}
                      {tag.name}
                    </button>
                  );
                })}
              </div>
              {levelIdx < visibleTagLevels.length - 1 && (
                <div className="my-3 border-t border-border/50" />
              )}
            </div>
          ))}

          <div>
            <p className="mb-2 text-xs font-medium text-muted-foreground">模糊搜索（可选）</p>
            <Input
              placeholder="输入关键词搜索图片标题或内容..."
              value={filterKeyword}
              onChange={(e) => setFilterKeyword(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={handleReset}>
            <RotateCcw className="mr-1.5 size-4" />
            重置
          </Button>
          <Button onClick={handleConfirm}>
            <Search className="mr-1.5 size-4" />
            查找对应素材
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default FilterDialog;
