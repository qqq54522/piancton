import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, ImagePlus, Images, Info, Loader2, Plus, Upload, X } from 'lucide-react';
import { toast } from 'sonner';

import * as assetApi from '@client/src/api/asset';
import { getApiError } from '@client/src/api/client';
import * as imageApi from '@client/src/api/image';
import { Button } from '@client/src/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@client/src/components/ui/dialog';
import { Input } from '@client/src/components/ui/input';
import { useBusinessConcepts } from '@client/src/features/assets/useBusinessConcepts';
import { SellingPointRelationFields } from '@client/src/features/assets/SellingPointRelationFields';
import { useImageChannelOptions } from '@client/src/features/images/hooks/useImageListQuery';
import { useImageTitleResolution } from '@client/src/features/images/useImageTitleResolution';
import UploadAssetPicker from './UploadAssetPicker';
import { addCustomChannel, useChannelOptions } from './channelOptions';
import { joinChannelValues } from './channelValue';
import { mergeUploadFiles, runUploadBatch, titleForUpload } from './uploadBatch';

export type UploadMode = 'single' | 'batch';

interface UploadDialogProps {
  initialMode?: UploadMode;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

const UploadDialog = ({ initialMode = 'single', open, onOpenChange, onSuccess }: UploadDialogProps) => {
  const [mode, setMode] = useState<UploadMode>(initialMode);
  const [files, setFiles] = useState<File[]>([]);
  const [title, setTitle] = useState('');
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [addingChannel, setAddingChannel] = useState(false);
  const [draftChannel, setDraftChannel] = useState('');
  const [styleLabel, setStyleLabel] = useState('');
  const [isSceneImage, setIsSceneImage] = useState(false);
  const [primaryConceptId, setPrimaryConceptId] = useState('');
  const [supportConceptIds, setSupportConceptIds] = useState<string[]>([]);
  const [debouncedTitle, setDebouncedTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{
    completed: number;
    currentFileName: string;
    total: number;
  } | null>(null);
  const concepts = useBusinessConcepts(open);
  const remoteChannels = useImageChannelOptions(open);
  const channelOptions = useChannelOptions(remoteChannels.data?.channels ?? []);
  const previews = useMemo(
    () => files.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [files],
  );
  const fileRiskHints = useMemo(() => fileRiskWarnings(files), [files]);
  const requestedTitle = useMemo(() => {
    if (files.length !== 1) return '';
    return (title.trim() || files[0].name.replace(/\.[^.]+$/, '')).slice(0, 255);
  }, [files, title]);
  const titleResolution = useImageTitleResolution(
    debouncedTitle,
    open && files.length === 1,
  );
  const visibleResolution = debouncedTitle === requestedTitle
    ? titleResolution.data
    : undefined;

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedTitle(requestedTitle), 350);
    return () => window.clearTimeout(timer);
  }, [requestedTitle]);

  useEffect(() => {
    if (open) setMode(initialMode);
  }, [initialMode, open]);

  useEffect(() => () => {
    previews.forEach((item) => URL.revokeObjectURL(item.url));
  }, [previews]);

  const reset = () => {
    setFiles([]);
    setTitle('');
    setSelectedChannels([]);
    setAddingChannel(false);
    setDraftChannel('');
    setStyleLabel('');
    setIsSceneImage(false);
    setPrimaryConceptId('');
    setSupportConceptIds([]);
    setDebouncedTitle('');
    setUploadProgress(null);
  };
  const close = () => {
    reset();
    onOpenChange(false);
  };
  const submitCustomChannel = () => {
    const nextChannel = addCustomChannel(draftChannel);
    if (!nextChannel) return;
    setSelectedChannels((items) => [...new Set([...items, nextChannel])]);
    setDraftChannel('');
    setAddingChannel(false);
  };
  const selectFiles = (selected: File[]) => {
    setFiles((current) => (
      mode === 'batch'
        ? mergeUploadFiles(current, selected)
        : selected.slice(0, 1)
    ));
  };
  const changeMode = (nextMode: UploadMode) => {
    if (uploading || nextMode === mode) return;
    if (nextMode === 'single' && files.length > 1) {
      toast.error('已选择多张图片，请先移除到只剩一张再切换单张上传');
      return;
    }
    if (nextMode === 'batch') {
      setTitle('');
      setStyleLabel('');
      setIsSceneImage(false);
    }
    setMode(nextMode);
  };

  const submit = async () => {
    if (!files.length) return toast.error('请选择图片');
    if (selectedChannels.length === 0) return toast.error('请先选择使用渠道');
    setUploading(true);
    setUploadProgress({ completed: 0, currentFileName: files[0].name, total: files.length });
    try {
      const result = await runUploadBatch(files, async (file, index) => {
        const fileTitle = titleForUpload(file, index, files.length, title);
        const image = await imageApi.uploadImage({
          file,
          title: fileTitle,
          channel: joinChannelValues(selectedChannels),
          styleLabel: styleLabel.trim() || undefined,
          isSceneImage,
          autoAnalyze: false,
        });
        let relationError: string | null = null;
        if (image.assetGroupId && (primaryConceptId || supportConceptIds.length > 0)) {
          try {
            await assetApi.replaceAssetConceptRelations(image.assetGroupId, [
              ...(primaryConceptId
                ? [{ conceptId: primaryConceptId, relationRole: 'expresses' as const }]
                : []),
              ...supportConceptIds.map((id) => ({
                conceptId: id,
                relationRole: 'supports' as const,
              })),
            ]);
          } catch (error) {
            relationError = getApiError(error).message;
          }
        }
        return { fileTitle, image, relationError };
      }, ({ completed, currentFile, total }) => {
        setUploadProgress({ completed, currentFileName: currentFile.name, total });
      });
      const automaticRenames = result.successes
        .filter(({ value }) => value.image.title !== value.fileTitle.trim().slice(0, 255))
        .map(({ value }) => value.image.title);
      const identityCodes = result.successes
        .map(({ value }) => value.image.identityCode)
        .filter((value): value is string => Boolean(value));
      const relationFailures = result.successes.filter(({ value }) => value.relationError);
      const uploadedCount = result.successes.length;
      if (uploadedCount > 0) onSuccess();

      if (result.failures.length > 0) {
        setFiles(result.failures.map(({ file }) => file));
        const firstError = getApiError(result.failures[0].error).message;
        toast.error(
          `已成功 ${uploadedCount} 张，失败 ${result.failures.length} 张；失败图片已保留，可直接重试。${firstError ? `首个错误：${firstError}` : ''}`,
        );
        if (relationFailures.length > 0) {
          toast.warning(`${relationFailures.length} 张图片已发布，但卖点关系写入失败，请在素材详情补充`);
        }
        return;
      }

      const baseMessage = `已上传 ${uploadedCount} 张主图`;
      const renameMessage = automaticRenames.length
        ? `；重名素材已自动保存为 ${automaticRenames.slice(0, 3).join('、')}${automaticRenames.length > 3 ? ` 等 ${automaticRenames.length} 个名称` : ''}`
        : '';
      const codeMessage = identityCodes.length === 1
        ? `；身份码 ${identityCodes[0]}`
        : '；每张图片已自动分配身份码';
      toast.success(`${baseMessage}${renameMessage}${codeMessage}`);
      if (relationFailures.length > 0) {
        toast.warning(`${relationFailures.length} 张图片已发布，但卖点关系写入失败，请在素材详情补充`);
      }
      close();
    } finally {
      setUploading(false);
      setUploadProgress(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(value) => (value ? onOpenChange(true) : close())}>
      <DialogContent
        showCloseButton={!uploading}
        className="grid max-h-[92vh] w-[calc(100%-1.25rem)] max-w-5xl grid-rows-[auto_minmax(0,1fr)_auto] gap-0 overflow-hidden border-0 p-0"
      >
        <DialogHeader className="border-b border-border/80 px-5 py-4 pr-14 sm:px-6 sm:py-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-start gap-3">
            <div className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-xl bg-[#f1f1ef] text-foreground">
              {mode === 'batch' ? <Images className="size-5" /> : <ImagePlus className="size-5" />}
            </div>
            <div>
              <DialogTitle className="text-xl tracking-tight">
                {mode === 'batch' ? '批量上传主图' : '上传单张主图'}
              </DialogTitle>
              <DialogDescription className="mt-1.5 leading-5">
                {mode === 'batch'
                  ? '一次选择多张图片，统一设置渠道和卖点关系。'
                  : '上传一张主图，并补充它的业务筛选信息。'}
              </DialogDescription>
            </div>
            </div>
            <div className="inline-flex w-fit rounded-xl bg-secondary p-1" aria-label="上传方式">
              <button
                type="button"
                disabled={uploading}
                aria-pressed={mode === 'single'}
                className={`flex h-8 items-center gap-1.5 rounded-lg px-3 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${mode === 'single' ? 'bg-white text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
                onClick={() => changeMode('single')}
              >
                <Upload className="size-3.5" />单张上传
              </button>
              <button
                type="button"
                disabled={uploading}
                aria-pressed={mode === 'batch'}
                className={`flex h-8 items-center gap-1.5 rounded-lg px-3 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${mode === 'batch' ? 'bg-white text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
                onClick={() => changeMode('batch')}
              >
                <Images className="size-3.5" />批量上传
              </button>
            </div>
          </div>
        </DialogHeader>

        <div className="grid min-h-0 overflow-y-auto lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
          <section className="border-b border-border/80 bg-secondary/35 p-5 sm:p-6 lg:border-b-0 lg:border-r">
            <div className="mb-4 flex items-center gap-3">
              <span className="flex size-7 items-center justify-center rounded-full bg-foreground text-xs font-semibold text-background">1</span>
              <div>
                <h2 className="text-sm font-semibold">选择图片</h2>
                <p className="mt-0.5 text-xs text-muted-foreground">图片和使用渠道为必填项</p>
              </div>
            </div>
            <UploadAssetPicker
              disabled={uploading}
              files={files}
              multiple={mode === 'batch'}
              previews={previews}
              onSelect={selectFiles}
              onRemove={(file) => setFiles((items) => items.filter((item) => item !== file))}
            />
            {mode === 'batch' && (
              <div className="mt-3 flex gap-2 rounded-xl border border-border/80 bg-[#f7f7f5] px-3 py-2.5 text-xs leading-5 text-foreground/70">
                <Info className="mt-0.5 size-3.5 shrink-0" />
                整批图片共用右侧渠道和卖点，名称自动取各自文件名。如果图片卖点不同，请分成多批上传。
              </div>
            )}
            {uploadProgress && (
              <div className="mt-3 rounded-xl border border-border bg-white px-3 py-3" role="status" aria-live="polite">
                <div className="flex items-center justify-between gap-3 text-xs font-medium text-foreground">
                  <span className="truncate">正在上传：{uploadProgress.currentFileName}</span>
                  <span className="shrink-0">{uploadProgress.completed}/{uploadProgress.total}</span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-secondary">
                  <div
                    className="h-full rounded-full bg-foreground transition-[width]"
                    style={{ width: `${Math.round((uploadProgress.completed / uploadProgress.total) * 100)}%` }}
                  />
                </div>
              </div>
            )}
            {fileRiskHints.length > 0 && (
              <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs leading-5 text-amber-800">
                <div className="flex items-center gap-2 font-semibold">
                  <AlertTriangle className="size-3.5 shrink-0" />
                  上传前检查
                </div>
                <ul className="mt-1.5 space-y-1">
                  {fileRiskHints.map((hint) => (
                    <li key={hint}>{hint}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          <section className="p-5 sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <span className="flex size-7 items-center justify-center rounded-full bg-foreground text-xs font-semibold text-background">2</span>
              <div>
                <h2 className="text-sm font-semibold">补充素材信息</h2>
                <p className="mt-0.5 text-xs text-muted-foreground">使用渠道必填，卖点关系可一次多选</p>
              </div>
            </div>

            <div className="space-y-5">
              {mode === 'single' && (
                <label className="block">
                  <span className="field-label">素材名称</span>
                  <Input
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    placeholder={files[0]?.name.replace(/\.[^.]+$/, '') || '可先填写，留空则使用文件名'}
                    maxLength={255}
                  />
                  {requestedTitle && debouncedTitle !== requestedTitle ? (
                    <span className="field-hint">正在检查名称…</span>
                  ) : titleResolution.isFetching ? (
                    <span className="field-hint">正在检查名称…</span>
                  ) : visibleResolution?.changed ? (
                    <span className="field-hint text-amber-700">
                      名称已存在，发布时将自动保存为“{visibleResolution.resolvedTitle}”
                    </span>
                  ) : (
                    <span className="field-hint">
                      单张上传可以在这里修改名称；仅重名时自动追加 001、002…
                    </span>
                  )}
                </label>
              )}

              <div className="rounded-2xl border border-border/80 bg-secondary/25 p-4">
                <div className="mb-3">
                  <p className="text-sm font-semibold">业务筛选信息</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    使用渠道由设计师人工确认，用于业务端按渠道精确找图，不触发 AI 分析。
                  </p>
                </div>
                <div className="space-y-4">
                  <div>
                    <span className="field-label">使用渠道</span>
                    <div className="mt-1.5 flex flex-wrap gap-2">
                      {channelOptions.map((item) => (
                        <Button
                          key={item}
                          type="button"
                          variant={selectedChannels.includes(item) ? 'default' : 'outline'}
                          size="sm"
                          disabled={uploading}
                          className={selectedChannels.includes(item) ? 'bg-foreground text-background hover:bg-foreground/88' : undefined}
                          onClick={() => setSelectedChannels((items) => (
                            items.includes(item)
                              ? items.filter((channel) => channel !== item)
                              : [...items, item]
                          ))}
                        >
                          {item}
                        </Button>
                      ))}
                      {addingChannel ? (
                        <div className="flex min-w-44 items-center gap-1 rounded-xl border border-border bg-white px-2 py-1">
                          <Input
                            value={draftChannel}
                            onChange={(event) => setDraftChannel(event.target.value)}
                            onKeyDown={(event) => {
                              if (event.key === 'Enter') submitCustomChannel();
                              if (event.key === 'Escape') {
                                setDraftChannel('');
                                setAddingChannel(false);
                              }
                            }}
                            placeholder="新增渠道"
                            maxLength={24}
                            disabled={uploading}
                            className="h-7 border-0 bg-transparent px-1 text-xs shadow-none focus-visible:ring-0"
                            autoFocus
                          />
                          <Button
                            type="button"
                            size="sm"
                            className="h-7 bg-foreground px-2 text-xs text-background hover:bg-foreground/88"
                            disabled={uploading || !draftChannel.trim()}
                            onClick={submitCustomChannel}
                          >
                            添加
                          </Button>
                          <button
                            type="button"
                            aria-label="取消新增渠道"
                            disabled={uploading}
                            onClick={() => {
                              setDraftChannel('');
                              setAddingChannel(false);
                            }}
                            className="flex size-7 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <X className="size-3.5" />
                          </button>
                        </div>
                      ) : (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={uploading}
                          onClick={() => setAddingChannel(true)}
                        >
                          <Plus className="size-3.5" />添加渠道
                        </Button>
                      )}
                    </div>
                    <span className="field-hint">每张主图至少选择一个适用渠道；可多选，新增渠道会同步出现在首页筛选里。</span>
                  </div>
                  {mode === 'single' && <label className="block">
                    <span className="field-label">画面风格</span>
                    <Input
                      value={styleLabel}
                      maxLength={100}
                      disabled={uploading}
                      placeholder="例如：官网风格、数据卡片、轻插画"
                      onChange={(event) => setStyleLabel(event.target.value)}
                    />
                    <span className="field-hint">可选，用于业务端按画面风格继续缩小结果。</span>
                  </label>}
                  {mode === 'single' && <div className="flex items-center gap-3">
                    <span className="field-label mb-0">场景图</span>
                    <button
                      type="button"
                      role="switch"
                      aria-label="场景图"
                      aria-checked={isSceneImage}
                      disabled={uploading}
                      onClick={() => setIsSceneImage((value) => !value)}
                      className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full border transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${isSceneImage ? 'border-foreground bg-foreground' : 'border-border bg-muted'}`}
                    >
                      <span className={`absolute left-1 size-5 rounded-full bg-white shadow-sm transition-transform ${isSceneImage ? 'translate-x-5' : 'translate-x-0'}`} />
                    </button>
                  </div>}
                </div>
              </div>

              <div className="rounded-2xl border border-border/80 bg-card p-4">
                <div className="mb-3">
                  <p className="text-sm font-semibold">卖点关系</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    选择一个主要表达卖点，也可以同时选择它还能支持的其他卖点。
                  </p>
                </div>
                <SellingPointRelationFields
                  concepts={concepts.data ?? []}
                  primaryConceptId={primaryConceptId}
                  supportConceptIds={supportConceptIds}
                  disabled={uploading}
                  onPrimaryConceptChange={setPrimaryConceptId}
                  onSupportConceptIdsChange={setSupportConceptIds}
                />
              </div>
            </div>
          </section>
        </div>

        <DialogFooter className="border-t border-border/80 bg-card px-5 py-4 sm:px-6">
          <div className="mr-auto hidden items-center gap-2 text-xs text-muted-foreground sm:flex">
            <CheckCircle2 className="size-4 text-success" />
            {mode === 'batch' ? '选择多张图片和使用渠道即可整批发布' : '选择图片和使用渠道即可发布'}
          </div>
          <Button variant="outline" onClick={close} disabled={uploading}>取消</Button>
          <Button onClick={submit} disabled={uploading || !files.length || selectedChannels.length === 0} className="min-w-28 bg-foreground text-background hover:bg-foreground/88">
            {uploading && <Loader2 className="size-4 animate-spin" />}
            {uploading
              ? `正在上传 ${uploadProgress?.completed ?? 0}/${files.length}`
              : mode === 'batch'
              ? `批量发布 ${files.length} 张`
              : '上传并发布'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default UploadDialog;

function fileRiskWarnings(files: File[]): string[] {
  const warnings: string[] = [];
  const gifFiles = files.filter((file) => isGifFile(file));
  const largeGifs = gifFiles.filter((file) => file.size >= 8 * 1024 * 1024);
  const largeImages = files.filter((file) => file.size >= 20 * 1024 * 1024);
  if (gifFiles.length > 0) {
    warnings.push('GIF 会在列表里保留动画预览，数量多时会比静态图更吃加载。');
  }
  if (largeGifs.length > 0) {
    warnings.push(`有 ${largeGifs.length} 个 GIF 超过 8MB，建议压缩或补静态替代图。`);
  }
  if (largeImages.length > 0) {
    warnings.push(`有 ${largeImages.length} 张图片超过 20MB，上传后会进入素材资产巡检。`);
  }
  if (files.length > 1) {
    warnings.push('批量上传会共用右侧业务信息；如果卖点不同，建议分批上传。');
  }
  return warnings;
}

function isGifFile(file: File): boolean {
  return file.type === 'image/gif' || file.name.toLowerCase().endsWith('.gif');
}
