import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import { Plus, Trash2, Loader2, ChevronRight, ChevronDown } from 'lucide-react';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { Badge } from '@client/src/components/ui/badge';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@client/src/components/ui/sheet';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@client/src/components/ui/alert-dialog';
import type { TagWithCount } from '@client/src/types/api';
import { buildTagTree, type TagTreeNode } from '@client/src/utils/tagTree';
import * as imageApi from '@client/src/api/image';
import type { TagDeleteImpact } from '@client/src/types/api';

const TAG_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
  '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1',
];

interface TagPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tags: TagWithCount[];
  selectedTagIds: string[];
  onTagClick: (tagId: string) => void;
  onTagsChanged: () => void;
}

const TagTreeItem = ({
  node,
  onDelete,
  onTagClick,
  deletingId,
  selectedTagIds,
  onAddChild,
}: {
  node: TagTreeNode;
  onDelete: (tag: TagTreeNode) => void;
  onTagClick: (tagId: string) => void;
  deletingId: string | null;
  selectedTagIds: string[];
  onAddChild: (parentId: string) => void;
}) => {
  const [expanded, setExpanded] = useState(true);
  const selected = selectedTagIds.includes(node.id);
  const hasChildren = node.children.length > 0;

  return (
    <div>
      <div
        className={`flex items-center gap-1 rounded-lg border px-2 py-1.5 transition-colors ${
          selected ? 'border-primary bg-accent' : 'border-border hover:bg-secondary'
        }`}
        style={{ marginLeft: node.depth * 16 }}
      >
        {hasChildren ? (
          <button
            onClick={() => setExpanded(!expanded)}
            className="rounded p-0.5 text-muted-foreground hover:text-foreground"
          >
            {expanded ? (
              <ChevronDown className="size-3.5" />
            ) : (
              <ChevronRight className="size-3.5" />
            )}
          </button>
        ) : (
          <span className="w-4.5" />
        )}

        <button
          className="flex flex-1 items-center gap-2 text-left"
          onClick={() => onTagClick(node.id)}
        >
          <Badge
            variant="secondary"
            className="text-xs font-normal"
            style={{ backgroundColor: `${node.color}18`, color: node.color }}
          >
            {node.name}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {node.imageCount} 张
          </span>
        </button>

        <div className="flex items-center gap-0.5">
          <button
            onClick={() => onAddChild(node.id)}
            className="rounded p-1 text-muted-foreground transition-colors hover:text-primary"
            title="添加子标签"
          >
            <Plus className="size-3" />
          </button>
          <button
            onClick={() => onDelete(node)}
            disabled={deletingId === node.id}
            className="rounded p-1 text-muted-foreground transition-colors hover:text-destructive disabled:opacity-30"
          >
            {deletingId === node.id ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Trash2 className="size-3.5" />
            )}
          </button>
        </div>
      </div>

      {hasChildren && expanded && (
        <div className="mt-1 space-y-1">
          {node.children.map((child) => (
            <TagTreeItem
              key={child.id}
              node={child}
              onDelete={onDelete}
              onTagClick={onTagClick}
              deletingId={deletingId}
              selectedTagIds={selectedTagIds}
              onAddChild={onAddChild}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const TagPanel = ({
  open,
  onOpenChange,
  tags,
  selectedTagIds,
  onTagClick,
  onTagsChanged,
}: TagPanelProps) => {
  const [newName, setNewName] = useState('');
  const [parentId, setParentId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<TagTreeNode | null>(null);
  const [deleteImpact, setDeleteImpact] = useState<TagDeleteImpact | null>(null);
  const [loadingImpact, setLoadingImpact] = useState(false);

  const tree = buildTagTree(tags);
  const handleCreate = useCallback(async () => {
    if (!newName.trim()) return;
    if (tags.some((t) => t.name === newName.trim() && t.parentId === parentId)) {
      toast.error('同级下标签名称已存在');
      return;
    }
    setCreating(true);
    try {
      const color = TAG_COLORS[tags.length % TAG_COLORS.length];
      await imageApi.createTag({ name: newName.trim(), color, parentId });
      toast.success('标签创建成功');
      setNewName('');
      onTagsChanged();
    } catch (err) {
      console.error('创建标签失败:', String(err));
      toast.error('创建标签失败');
    } finally {
      setCreating(false);
    }
  }, [newName, parentId, tags, onTagsChanged]);

  const handleDelete = useCallback(async (tag: TagTreeNode) => {
    setDeleteConfirm(tag);
    setDeleteImpact(null);
    setLoadingImpact(true);
    try {
      setDeleteImpact(await imageApi.fetchTagDeleteImpact(tag.id));
    } catch (err) {
      console.error('读取标签删除影响失败:', String(err));
      toast.error('无法读取删除影响，请稍后重试');
      setDeleteConfirm(null);
    } finally {
      setLoadingImpact(false);
    }
  }, []);

  const confirmDelete = useCallback(async () => {
    if (!deleteConfirm) return;
    const tag = deleteConfirm;
    setDeleteConfirm(null);
    setDeletingId(tag.id);
    try {
      await imageApi.deleteTag(tag.id);
      toast.success(deleteImpact?.affectedImageCount
        ? `标签已删除；${deleteImpact.affectedImageCount} 张相关图片不会被删除`
        : '标签已删除');
      onTagsChanged();
    } catch (err) {
      console.error('删除标签失败:', String(err));
      toast.error('删除标签失败');
    } finally {
      setDeletingId(null);
    }
  }, [deleteConfirm, deleteImpact, onTagsChanged]);

  const handleAddChild = useCallback((parentTagId: string) => {
    setParentId(parentTagId);
    setNewName('');
  }, []);

  const parentTag = parentId ? tags.find((t) => t.id === parentId) : null;

  return (
    <>
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-80 overflow-y-auto">
        <SheetHeader>
          <SheetTitle>标签管理</SheetTitle>
        </SheetHeader>

        <div className="mt-4 space-y-4">
          <div>
            {parentTag && (
              <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                <span>在</span>
                <Badge
                  variant="secondary"
                  className="text-xs"
                  style={{ backgroundColor: `${parentTag.color}18`, color: parentTag.color }}
                >
                  {parentTag.name}
                </Badge>
                <span>下创建</span>
                <button
                  onClick={() => setParentId(null)}
                  className="ml-auto text-primary hover:underline"
                >
                  切换为顶级
                </button>
              </div>
            )}
            <div className="flex gap-2">
              <Input
                placeholder={parentTag ? `在「${parentTag.name}」下添加子标签` : '新标签名称'}
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              />
              <Button
                size="icon"
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
              >
                {creating ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
              </Button>
            </div>
          </div>

          <div className="space-y-1">
            {tree.map((node) => (
              <TagTreeItem
                key={node.id}
                node={node}
                onDelete={handleDelete}
                onTagClick={onTagClick}
                deletingId={deletingId}
                selectedTagIds={selectedTagIds}
                onAddChild={handleAddChild}
              />
            ))}
          </div>

          {tags.length === 0 && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              暂无标签，请先创建
            </p>
          )}
        </div>
      </SheetContent>
    </Sheet>

    <AlertDialog open={!!deleteConfirm} onOpenChange={(open) => { if (!open) setDeleteConfirm(null); }}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>确认删除标签「{deleteConfirm?.name}」？</AlertDialogTitle>
          <AlertDialogDescription>
            {loadingImpact ? (
              '正在计算该操作会影响的标签和图片...'
            ) : deleteImpact ? (
              <>
                将删除 {deleteImpact.subtreeTagCount} 个标签
                {deleteImpact.subtreeTagCount > 1 ? '（包含子标签）' : ''}
                ；{deleteImpact.affectedImageCount} 张相关图片会保留，但会解除该自定义标签关联。
                标准体系标签不能直接删除，只能通过目录版本治理调整。
              </>
            ) : (
              '删除前无法获取影响范围，请关闭后重试。'
            )}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={confirmDelete}
            disabled={loadingImpact || !deleteImpact}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {loadingImpact ? '计算中...' : '确认删除'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
    </>
  );
};

export default TagPanel;
