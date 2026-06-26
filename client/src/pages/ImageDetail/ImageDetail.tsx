import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Edit2, Loader2, Check, Download, Trash2, RefreshCw, X } from 'lucide-react';
import { CanRole, useAuth, ROLE_SUBJECT } from '@client/src/lib/auth';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@client/src/components/ui/alert-dialog';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { Badge } from '@client/src/components/ui/badge';
import { Avatar, AvatarFallback } from '@client/src/components/ui/avatar';
import TagTreeSelector from '@client/src/components/TagTreeSelector';
import { useImageUrl } from '@client/src/hooks/useImageUrl';
import type { BusinessLabel, ImageItem, ContentTag, Level2Category } from '@client/src/types/api';
import { useImageDetail } from '@client/src/features/images/useImageDetail';
import { useTags } from '@client/src/features/tags/useTags';
import { useImageDetailActions } from '@client/src/features/images/useImageDetailActions';
import { useProviderStatus } from '@client/src/features/ai/useProviderStatus';

const RelatedImageItem = ({ img }: { img: ImageItem }) => {
  const imgUrl = useImageUrl(img.contentUrl);
  return (
    <Link
      to={`/image/${img.id}`}
      className="group flex-shrink-0 overflow-hidden rounded-lg border border-border shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
      style={{ width: 200 }}
    >
      <div className="aspect-[4/3] overflow-hidden bg-muted">
        <img
          src={imgUrl}
          alt={img.title}
          className="size-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
        />
      </div>
      <div className="p-2">
        <p className="truncate text-xs font-medium text-foreground">
          {img.title}
        </p>
      </div>
    </Link>
  );
};

const ImageDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const detailQuery = useImageDetail(id);
  const tagsQuery = useTags();
  const detail = detailQuery.data ?? null;
  const allTags = tagsQuery.data ?? [];
  const loading = detailQuery.isLoading || tagsQuery.isLoading;
  const mainImageUrl = useImageUrl(detail?.contentUrl ?? '');
  const canDesign = useAuth();
  const isDesigner = !canDesign.isLoading && canDesign.ability.can('designer', ROLE_SUBJECT);
  const provider = useProviderStatus(isDesigner);
  const actions = useImageDetailActions(detail);

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center gap-3">
        <p className="text-muted-foreground">图片不存在</p>
        <Button variant="outline" onClick={() => navigate('/')}>
          返回首页
        </Button>
      </div>
    );
  }

  const manualBusinessLabels = detail.businessLabels.filter((label) => label.origin === 'manual');
  const hasAiBusinessLabelRecords = detail.businessLabels.some((label) => label.origin === 'ai');
  const aiBusinessLabels = detail.businessLabels.filter(
    (label) => label.origin === 'ai' && label.reviewStatus !== 'rejected',
  );
  const latestAnalysisRun = detail.analysisRuns?.[0];
  const latestAnalysisActive =
    latestAnalysisRun?.status === 'queued' || latestAnalysisRun?.status === 'running';
  const analysisStatusText = latestAnalysisRun
    ? ({
        queued: '排队中',
        running: '分析中',
        succeeded: '已完成',
        failed: '失败',
      } as const)[latestAnalysisRun.status]
    : '未分析';
  const analysisStatusClass = latestAnalysisRun
    ? ({
        queued: 'border-amber-200 bg-amber-50 text-amber-700',
        running: 'border-blue-200 bg-blue-50 text-blue-700',
        succeeded: 'border-emerald-200 bg-emerald-50 text-emerald-700',
        failed: 'border-rose-200 bg-rose-50 text-rose-700',
      } as const)[latestAnalysisRun.status]
    : 'border-muted bg-muted text-muted-foreground';
  const reviewStatusLabel = (label: BusinessLabel) => {
    if (label.reviewStatus === 'accepted') return '已接受';
    if (label.reviewStatus === 'rejected') return '已拒绝';
    return '待审核';
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <div className="mb-4">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          返回
        </button>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        <div className="flex-1 overflow-hidden rounded-xl bg-[#1a1a2e] lg:max-w-[65%]">
          <img
            src={mainImageUrl}
            alt={detail.title}
            className="mx-auto max-h-[70vh] w-full object-contain"
          />
        </div>

        <div className="flex-1 lg:max-w-[35%]">
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="flex items-center justify-between">
              {isDesigner && actions.editingTitle ? (
                <div className="flex items-center gap-2 flex-1 mr-3">
                  <Input
                    value={actions.editTitle}
                    onChange={(e) => actions.setEditTitle(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') actions.saveTitle(); if (e.key === 'Escape') actions.setEditingTitle(false); }}
                    className="h-8 text-base"
                    autoFocus
                  />
                  <Button size="sm" onClick={actions.saveTitle} disabled={actions.savingTitle || !actions.editTitle.trim()}>
                    {actions.savingTitle ? <Loader2 className="size-3.5 animate-spin" /> : <Check className="size-3.5" />}
                  </Button>
                </div>
              ) : (
                <h1
                  className={`flex-1 text-xl font-semibold text-foreground mr-3 ${isDesigner ? 'cursor-pointer hover:text-primary transition-colors' : ''}`}
                  onClick={isDesigner ? actions.beginTitleEditing : undefined}
                  title={isDesigner ? '点击编辑名称' : undefined}
                >
                  {detail.title}
                </h1>
              )}
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={actions.download}
                >
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
                    detail.categories.map((cat: string) => (
                      <Badge
                        key={cat}
                        variant="outline"
                        className="text-xs"
                        style={{
                          borderColor: cat === 'scene' ? '#10B981' : '#6366F1',
                          color: cat === 'scene' ? '#10B981' : '#6366F1',
                          backgroundColor: cat === 'scene' ? '#10B98118' : '#6366F118',
                        }}
                      >
                        {cat === 'scene' ? '场景' : '功能'}
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
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          actions.cancelTagEditing();
                        }}
                      >
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
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={actions.beginTagEditing}
                    >
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
                            {tag.parentName ? `${tag.parentName} > ${tag.name || '未命名'}` : (tag.name || '未命名')}
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

            <CanRole roles={['designer']}>
              <div className="mt-5 flex items-center justify-between border-t border-border pt-5">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">AI 分析</span>
                    <Badge variant="outline" className={`text-[11px] ${analysisStatusClass}`}>
                      {latestAnalysisActive && (
                        <Loader2 className="mr-1 size-3 animate-spin" />
                      )}
                      {analysisStatusText}
                    </Badge>
                  </div>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    上传后自动分析；手动重跑会刷新自动匹配、语义总结和隐形内容标签
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!provider.data?.configured || actions.analyzing || latestAnalysisActive}
                  onClick={() => actions.analyze()}
                  title={provider.data?.configured ? '重新执行完整 AI 分析' : 'AI Provider 尚未配置'}
                >
                  <RefreshCw className={`mr-1.5 size-3.5 ${actions.analyzing ? 'animate-spin' : ''}`} />
                  {provider.isLoading
                    ? '检查模型…'
                    : provider.data?.configured
                      ? latestAnalysisActive ? '后台分析中…' : actions.analyzing ? '分析中…' : '重新分析'
                      : 'AI 未配置'}
                </Button>
              </div>

              {detail.imageSummary && (
                <div className="mt-5">
                  <span className="text-sm font-medium text-foreground">语义总结</span>
                  <p className="mt-1.5 rounded-lg border border-primary/10 bg-primary/5 px-3 py-2 text-sm leading-relaxed text-foreground/80">
                    {detail.imageSummary}
                  </p>
                </div>
              )}

              <div className="mt-5">
                <span className="text-sm font-medium text-foreground">AI 自动匹配</span>
                <p className="mt-0.5 text-[11px] text-muted-foreground">
                  来自封闭业务标签目录；接受后会追加为设计师附加标签，不覆盖主标签
                </p>
                {aiBusinessLabels.length > 0 ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {aiBusinessLabels.map((label) => (
                      <div
                        key={label.id}
                        className="inline-flex items-center gap-1 rounded-full border border-purple-200 bg-purple-50 px-2 py-1 text-xs text-purple-700"
                        title={label.reason ?? ''}
                      >
                        {label.systemName ? `${label.systemName} > ${label.tagName}` : label.tagName}
                        {label.confidence != null && (
                          <span className="ml-1 text-[10px] text-purple-400">
                            {Math.round(label.confidence * 100)}
                          </span>
                        )}
                        <span className="ml-1 rounded bg-purple-100 px-1 text-[10px] text-purple-500">
                          {reviewStatusLabel(label)}
                        </span>
                        {label.reviewStatus === 'pending' && (
                          <>
                            <button
                              type="button"
                              className="ml-1 rounded-full bg-emerald-100 p-0.5 text-emerald-700 hover:bg-emerald-200 disabled:opacity-50"
                              onClick={() => actions.reviewBusinessLabel({
                                labelId: label.id,
                                reviewStatus: 'accepted',
                              })}
                              disabled={actions.reviewingBusinessLabel}
                              title="接受并转为设计师附加标签"
                            >
                              <Check className="size-3" />
                            </button>
                            <button
                              type="button"
                              className="rounded-full bg-rose-100 p-0.5 text-rose-700 hover:bg-rose-200 disabled:opacity-50"
                              onClick={() => actions.reviewBusinessLabel({
                                labelId: label.id,
                                reviewStatus: 'rejected',
                              })}
                              disabled={actions.reviewingBusinessLabel}
                              title="拒绝这个 AI 建议"
                            >
                              <X className="size-3" />
                            </button>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                ) : !hasAiBusinessLabelRecords && detail.level2Categories && detail.level2Categories.length > 0 ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {detail.level2Categories.map((cat: Level2Category) => (
                      <Badge
                        key={cat.id}
                        variant="outline"
                        className="cursor-default border-purple-200 bg-purple-50 text-xs text-purple-700"
                        title={cat.reason ?? ''}
                      >
                        {cat.categoryName}
                        <span className="ml-1 text-[10px] text-purple-400">{Math.round(cat.confidence * 100)}</span>
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <span className="mt-1 block text-xs text-muted-foreground">
                    暂无符合证据要求的自动匹配标签
                  </span>
                )}
              </div>

              <div className="mt-5">
                <span className="text-sm font-medium text-foreground">隐形内容标签</span>
                <p className="mt-0.5 text-[11px] text-muted-foreground">
                  约 20 个可检索的中文可见内容描述
                </p>
                {detail.contentTags && detail.contentTags.length > 0 ? (
                  <div className="mt-2 space-y-2">
                    {(() => {
                      const dimensionGroups = new Map<string, ContentTag[]>();
                      for (const ct of detail.contentTags) {
                        const dim = ct.dimension ?? '其他';
                        const list = dimensionGroups.get(dim) ?? [];
                        list.push(ct);
                        dimensionGroups.set(dim, list);
                      }
                      const dimensionOrder = ['人物', '关系', '场景', '动作', '情绪', '产品功能', '业务卖点', '视觉风格', '其他'];
                      const sortedGroups = [...dimensionGroups.entries()].sort(
                        (a, b) => dimensionOrder.indexOf(a[0]) - dimensionOrder.indexOf(b[0]) || a[0].localeCompare(b[0]),
                      );
                      return sortedGroups.map(([dimension, tagsList]) => (
                        <div key={dimension} className="flex flex-wrap items-start gap-1.5">
                          <Badge
                            variant="outline"
                            className="flex-shrink-0 border-primary/20 bg-primary/5 text-[10px] text-primary/60"
                          >
                            {dimension}
                          </Badge>
                          {tagsList.map((ct: ContentTag) => (
                            <Badge
                              key={ct.id}
                              variant="outline"
                              className="cursor-default border-dashed border-primary/30 bg-primary/5 text-xs text-primary/70"
                              title={`置信度: ${Math.round(ct.confidence * 100)}%`}
                            >
                              {ct.tagName}
                              <span className="ml-1 text-[10px] text-primary/40">{Math.round(ct.confidence * 100)}</span>
                            </Badge>
                          ))}
                        </div>
                      ));
                    })()}
                  </div>
                ) : (
                  <span className="mt-1 block text-xs text-muted-foreground">
                    {latestAnalysisActive
                      ? '后台自动分析中，完成后会自动刷新。'
                      : provider.data?.configured
                      ? '暂无隐形标签，点击“重新分析”生成。'
                      : 'AI Provider 尚未配置'}
                  </span>
                )}
              </div>

            </CanRole>
          </div>
        </div>
      </div>

      {detail.relatedImages.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-4 text-lg font-medium text-foreground">相关推荐</h2>
          <div className="flex gap-4 overflow-x-auto pb-4">
            {detail.relatedImages.map((img) => (
              <RelatedImageItem key={img.id} img={img} />
            ))}
          </div>
        </div>
      )}

      <AlertDialog open={actions.showDeleteDialog} onOpenChange={actions.setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除图片「{detail.title}」？</AlertDialogTitle>
            <AlertDialogDescription>
              删除后无法恢复，该图片关联的所有标签也将解除绑定。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => actions.remove()}
              disabled={actions.deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {actions.deleting ? (
                <><Loader2 className="mr-1.5 size-4 animate-spin" />删除中...</>
              ) : (
                '确认删除'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default ImageDetail;
