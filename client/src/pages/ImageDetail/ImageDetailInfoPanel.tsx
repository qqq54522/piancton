import { Link } from 'react-router-dom';
import { Check, Download, Edit2, Loader2, Trash2 } from 'lucide-react';

import { Avatar, AvatarFallback } from '@client/src/components/ui/avatar';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import TagTreeSelector from '@client/src/components/TagTreeSelector';
import { CanRole } from '@client/src/lib/auth';
import type { useProviderStatus } from '@client/src/features/ai/useProviderStatus';
import type { useImageDetailActions } from '@client/src/features/images/useImageDetailActions';
import type {
  ImageDetail,
  TagWithCount,
} from '@client/src/types/api';
import ImageAiAnalysisPanel from './ImageAiAnalysisPanel';

type ImageDetailActions = ReturnType<typeof useImageDetailActions>;
type ProviderStatusQuery = ReturnType<typeof useProviderStatus>;

interface ImageDetailInfoPanelProps {
  detail: ImageDetail;
  allTags: TagWithCount[];
  isDesigner: boolean;
  provider: ProviderStatusQuery;
  actions: ImageDetailActions;
}

const ImageDetailInfoPanel = ({
  detail,
  allTags,
  isDesigner,
  provider,
  actions,
}: ImageDetailInfoPanelProps) => {
  const manualBusinessLabels = detail.businessLabels.filter((label) => label.origin === 'manual');

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-center justify-between">
        {isDesigner && actions.editingTitle ? (
          <div className="mr-3 flex flex-1 items-center gap-2">
            <Input
              value={actions.editTitle}
              onChange={(event) => actions.setEditTitle(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') actions.saveTitle();
                if (event.key === 'Escape') actions.setEditingTitle(false);
              }}
              className="h-8 text-base"
              autoFocus
            />
            <Button
              size="sm"
              onClick={actions.saveTitle}
              disabled={actions.savingTitle || !actions.editTitle.trim()}
            >
              {actions.savingTitle ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Check className="size-3.5" />
              )}
            </Button>
          </div>
        ) : (
          <h1
            className={`mr-3 flex-1 text-xl font-semibold text-foreground ${isDesigner ? 'cursor-pointer transition-colors hover:text-primary' : ''}`}
            onClick={isDesigner ? actions.beginTitleEditing : undefined}
            title={isDesigner ? '点击编辑名称' : undefined}
          >
            {detail.title}
          </h1>
        )}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={actions.download}>
            <Download className="mr-1.5 size-4" />
            下载
          </Button>
          <CanRole roles={['designer']}>
            <Button
              variant="outline"
              size="sm"
              className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
              onClick={() => actions.setShowDeleteDialog(true)}
            >
              <Trash2 className="mr-1.5 size-4" />
              删除
            </Button>
          </CanRole>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <Avatar className="size-7">
          <AvatarFallback className="bg-secondary text-[10px] text-secondary-foreground">
            U
          </AvatarFallback>
        </Avatar>
        <span className="text-xs text-muted-foreground">
          {new Date(detail.createdAt).toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}
        </span>
      </div>

      <CanRole roles={['designer']}>
        <div className="mt-5">
          <span className="text-sm font-medium text-foreground">分类</span>
          <div className="mt-2 flex flex-wrap gap-2">
            {detail.categories && detail.categories.length > 0 ? (
              detail.categories.map((category: string) => (
                <Badge
                  key={category}
                  variant="outline"
                  className="text-xs"
                  style={{
                    borderColor: category === 'scene' ? '#10B981' : '#6366F1',
                    color: category === 'scene' ? '#10B981' : '#6366F1',
                    backgroundColor: category === 'scene' ? '#10B98118' : '#6366F118',
                  }}
                >
                  {category === 'scene' ? '场景' : '功能'}
                </Badge>
              ))
            ) : (
              <span className="text-xs text-muted-foreground">未分类</span>
            )}
          </div>
        </div>
      </CanRole>

      <div className="mt-5">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-foreground">标签</span>
          <CanRole roles={['designer']}>
            {actions.editingTags ? (
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="sm" onClick={actions.cancelTagEditing}>
                  取消
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => actions.saveTags()}
                  disabled={actions.savingTags || actions.editTagIds.length === 0}
                >
                  <Check className="mr-1 size-3.5" />
                  保存
                </Button>
              </div>
            ) : (
              <Button variant="ghost" size="sm" onClick={actions.beginTagEditing}>
                <Edit2 className="mr-1 size-3.5" />
                编辑
              </Button>
            )}
          </CanRole>
        </div>

        {actions.editingTags ? (
          <div className="mt-2 space-y-3">
            <TagTreeSelector
              tags={allTags}
              selectedIds={actions.editTagIds}
              onToggle={actions.toggleEditTag}
              placeholder="选择标签"
              expandable
              assignableOnly
            />
            {actions.editTagIds.length === 0 && (
              <p className="text-xs text-destructive">
                图片必须至少保留一个允许打标的标签。
              </p>
            )}
          </div>
        ) : (
          <div className="mt-2">
            {actions.flatDisplayTags.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {actions.flatDisplayTags.map((tag) => (
                  <Link key={tag.id} to={`/?tag=${tag.id}`}>
                    <Badge
                      variant="secondary"
                      className="cursor-pointer text-xs transition-opacity hover:opacity-80"
                      style={{
                        backgroundColor: `${tag.color || '#6B7280'}18`,
                        color: tag.color || '#6B7280',
                      }}
                    >
                      {tag.parentName
                        ? `${tag.parentName} > ${tag.name || '未命名'}`
                        : (tag.name || '未命名')}
                    </Badge>
                  </Link>
                ))}
              </div>
            ) : (
              <span className="text-xs text-muted-foreground">暂无标签</span>
            )}
            {manualBusinessLabels.length > 0 && (
              <div className="mt-3 rounded-lg border border-border bg-muted/30 px-3 py-2">
                <p className="mb-1.5 text-[11px] text-muted-foreground">
                  设计师归属（用于搜索权重）
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {manualBusinessLabels.map((label) => (
                    <Badge
                      key={label.id}
                      variant={label.role === 'primary' ? 'default' : 'outline'}
                      className="text-[11px]"
                    >
                      {label.systemName ? `${label.systemName} > ${label.tagName}` : label.tagName}
                      <span className="ml-1 opacity-70">
                        {label.role === 'primary' ? '主' : '附加'}
                      </span>
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <ImageAiAnalysisPanel
        detail={detail}
        provider={provider}
        actions={actions}
      />
    </div>
  );
};

export default ImageDetailInfoPanel;
