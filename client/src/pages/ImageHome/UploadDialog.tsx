import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, ImagePlus, Info, Loader2, Plus, Sparkles, X } from 'lucide-react';
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
import { useProviderStatus } from '@client/src/features/ai/useProviderStatus';
import { useAssetPhraseSuggestions } from '@client/src/features/ai/useAssetPhraseSuggestions';
import { useBusinessConcepts } from '@client/src/features/assets/useBusinessConcepts';
import { useBusinessFacets } from '@client/src/features/assets/useBusinessFacets';
import { BusinessClassificationFields } from '@client/src/features/assets/BusinessClassificationFields';
import { useImageTitleResolution } from '@client/src/features/images/useImageTitleResolution';
import UploadAssetPicker from './UploadAssetPicker';
import UploadAssetPhraseGenerator from './UploadAssetPhraseGenerator';
import ConceptPhraseInheritancePanel from './ConceptPhraseInheritancePanel';
import UploadSearchPhraseFields from './UploadSearchPhraseFields';
import { addCustomChannel, useChannelOptions } from './channelOptions';
import { joinChannelValues } from './channelValue';
import { normalizeExpectedSearchWords } from './uploadSearchPhrases';

interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

const UploadDialog = ({ open, onOpenChange, onSuccess }: UploadDialogProps) => {
  const [files, setFiles] = useState<File[]>([]);
  const [title, setTitle] = useState('');
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [addingChannel, setAddingChannel] = useState(false);
  const [draftChannel, setDraftChannel] = useState('');
  const [styleLabel, setStyleLabel] = useState('');
  const [isSceneImage, setIsSceneImage] = useState(false);
  const [conceptId, setConceptId] = useState('');
  const [proofPointCode, setProofPointCode] = useState('');
  const [evidencePointCode, setEvidencePointCode] = useState('');
  const [expectedSearchWords, setExpectedSearchWords] = useState(['']);
  const [aiPhraseCount, setAiPhraseCount] = useState(5);
  const [debouncedTitle, setDebouncedTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const phraseSuggestions = useAssetPhraseSuggestions();
  const provider = useProviderStatus(open);
  const concepts = useBusinessConcepts(open);
  const facets = useBusinessFacets(open);
  const channelOptions = useChannelOptions();
  const selectedConcept = concepts.data?.find((concept) => concept.id === conceptId);
  const previews = useMemo(
    () => files.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [files],
  );
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
    setConceptId('');
    setProofPointCode('');
    setEvidencePointCode('');
    setExpectedSearchWords(['']);
    setAiPhraseCount(5);
    setDebouncedTitle('');
    phraseSuggestions.reset();
  };

  const generatePhrases = async () => {
    if (files.length !== 1) {
      toast.error(files.length ? '批量上传时请分别为每张图片生成话术' : '请先选择一张图片');
      return;
    }
    try {
      const file = files[0];
      const result = await phraseSuggestions.mutateAsync({
        file,
        count: aiPhraseCount,
        title: title.trim() || file.name.replace(/\.[^.]+$/, ''),
        conceptCode: selectedConcept?.code,
      });
      setExpectedSearchWords(result.phrases);
      toast.success(`AI 已生成 ${result.phrases.length} 条素材独有话术，可继续修改`);
    } catch (error) {
      toast.error(getApiError(error).message);
    }
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

  const submit = async () => {
    if (!files.length) return toast.error('请选择图片');
    if (selectedChannels.length === 0) return toast.error('请先选择使用渠道');
    setUploading(true);
    try {
      const automaticRenames: string[] = [];
      for (const [index, file] of files.entries()) {
        const fileTitle = files.length === 1 && title.trim()
          ? title.trim()
          : file.name.replace(/\.[^.]+$/, '') || `图片 ${index + 1}`;
        const image = await imageApi.uploadImage({
          file,
          title: fileTitle,
          channel: joinChannelValues(selectedChannels),
          styleLabel: styleLabel.trim() || undefined,
          isSceneImage,
          expectedSearchWords: normalizeExpectedSearchWords(expectedSearchWords),
          autoAnalyze: true,
        });
        if (image.title !== fileTitle.trim().slice(0, 255)) {
          automaticRenames.push(image.title);
        }
        if ((conceptId || proofPointCode || evidencePointCode) && image.assetGroupId) {
          await assetApi.updateAssetBusinessClassification(image.assetGroupId, {
            conceptId: conceptId || null,
            proofPointCode: proofPointCode || null,
            evidencePointCode: evidencePointCode || null,
          });
        }
      }
      const baseMessage = provider.data?.configured
        ? `已上传 ${files.length} 张主图，AI 正在后台分析`
        : `已上传 ${files.length} 张主图`;
      const renameMessage = automaticRenames.length
        ? `；重名素材已自动保存为 ${automaticRenames.slice(0, 3).join('、')}${automaticRenames.length > 3 ? ` 等 ${automaticRenames.length} 个名称` : ''}`
        : '';
      toast.success(`${baseMessage}${renameMessage}`);
      onSuccess();
      close();
    } catch (error) {
      toast.error(getApiError(error).message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(value) => (value ? onOpenChange(true) : close())}>
      <DialogContent
        showCloseButton={!uploading}
        className="grid max-h-[92vh] w-[calc(100%-1.25rem)] max-w-5xl grid-rows-[auto_minmax(0,1fr)_auto] gap-0 overflow-hidden border-0 p-0"
      >
        <DialogHeader className="border-b border-border/80 px-5 py-4 pr-14 sm:px-6 sm:py-5">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-xl bg-[#f1f1ef] text-foreground">
              <ImagePlus className="size-5" />
            </div>
            <div>
              <DialogTitle className="text-xl tracking-tight">上传主图</DialogTitle>
              <DialogDescription className="mt-1.5 leading-5">
                先把已审核图片放进素材库。卖点、话术和延展版本都可以发布后继续完善。
              </DialogDescription>
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
              files={files}
              previews={previews}
              onSelect={setFiles}
              onRemove={(file) => setFiles((items) => items.filter((item) => item !== file))}
            />
            {files.length > 1 && (
              <div className="mt-3 flex gap-2 rounded-xl border border-border/80 bg-[#f7f7f5] px-3 py-2.5 text-xs leading-5 text-foreground/70">
                <Info className="mt-0.5 size-3.5 shrink-0" />
                右侧渠道、场景图、卖点和话术会应用到本次选中的全部图片；图片名称默认使用各自文件名。
              </div>
            )}
          </section>

          <section className="p-5 sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <span className="flex size-7 items-center justify-center rounded-full bg-foreground text-xs font-semibold text-background">2</span>
              <div>
                <h2 className="text-sm font-semibold">补充素材信息</h2>
                <p className="mt-0.5 text-xs text-muted-foreground">使用渠道必填，卖点和话术可发布后继续完善</p>
              </div>
            </div>

            <div className="space-y-5">
              {files.length <= 1 && (
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
                  <label className="block">
                    <span className="field-label">画面风格</span>
                    <Input
                      value={styleLabel}
                      maxLength={100}
                      disabled={uploading}
                      placeholder="例如：官网风格、数据卡片、轻插画"
                      onChange={(event) => setStyleLabel(event.target.value)}
                    />
                    <span className="field-hint">可选，用于业务端按画面风格继续缩小结果。</span>
                  </label>
                  <div className="flex items-center gap-3">
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
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-border/80 bg-card p-4">
                <div className="mb-3">
                  <p className="text-sm font-semibold">业务表达层级</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    选择素材主要表达的卖点和证明点；六大体系会自动带出。
                  </p>
                </div>
                <BusinessClassificationFields
                  concepts={concepts.data ?? []}
                  facets={facets.data ?? { proofPoints: [], evidencePoints: [] }}
                  conceptId={conceptId}
                  proofPointCode={proofPointCode}
                  evidencePointCode={evidencePointCode}
                  disabled={uploading}
                  onConceptChange={(value) => {
                    setConceptId(value);
                    setProofPointCode('');
                    setEvidencePointCode('');
                  }}
                  onProofPointChange={(value) => {
                    setProofPointCode(value);
                    setEvidencePointCode('');
                  }}
                  onEvidencePointChange={setEvidencePointCode}
                />
              </div>

              {selectedConcept && (
                <ConceptPhraseInheritancePanel concept={selectedConcept} />
              )}

              <UploadSearchPhraseFields
                values={expectedSearchWords}
                onChange={setExpectedSearchWords}
                generator={(
                  <UploadAssetPhraseGenerator
                    count={aiPhraseCount}
                    onCountChange={setAiPhraseCount}
                    onGenerate={generatePhrases}
                    generating={phraseSuggestions.isPending}
                    disabled={
                      uploading
                      || files.length !== 1
                      || !provider.data?.configured
                    }
                    hint={
                      !provider.data?.configured
                        ? '当前未配置 AI，仍可手动填写'
                        : files.length !== 1
                          ? '请选择单张图片；批量上传不会共用一组 AI 话术'
                          : '读取当前图片和已选卖点；生成后请检查，上传即视为确认'
                    }
                  />
                )}
              />

              <div className="flex items-start gap-2.5 rounded-xl border border-border/80 bg-card px-3.5 py-3 text-xs leading-5 text-muted-foreground">
                {provider.isLoading ? (
                  <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin text-foreground" />
                ) : provider.data?.configured ? (
                  <Sparkles className="mt-0.5 size-4 shrink-0 text-foreground" />
                ) : (
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" />
                )}
                <span>
                  {provider.isLoading
                    ? '正在检查智能分析服务…'
                    : provider.data?.configured
                      ? '发布后会在后台执行画面分析、卖点建议和搜索索引更新，不会阻塞当前上传。'
                      : '当前未配置 AI，仍可正常上传和发布；之后可在详情页补做分析。'}
                </span>
              </div>
            </div>
          </section>
        </div>

        <DialogFooter className="border-t border-border/80 bg-card px-5 py-4 sm:px-6">
          <div className="mr-auto hidden items-center gap-2 text-xs text-muted-foreground sm:flex">
            <CheckCircle2 className="size-4 text-success" />选择图片和使用渠道即可发布
          </div>
          <Button variant="outline" onClick={close} disabled={uploading}>取消</Button>
          <Button onClick={submit} disabled={uploading || !files.length || selectedChannels.length === 0} className="min-w-28 bg-foreground text-background hover:bg-foreground/88">
            {uploading && <Loader2 className="size-4 animate-spin" />}
            {uploading ? '正在上传' : files.length > 1 ? `发布 ${files.length} 张` : '上传并发布'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default UploadDialog;
