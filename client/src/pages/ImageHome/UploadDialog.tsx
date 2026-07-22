import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, ImagePlus, Info, Loader2, Sparkles } from 'lucide-react';
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
import { Select } from '@client/src/components/ui/select';
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
import { normalizeExpectedSearchWords } from './uploadSearchPhrases';

interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

const UploadDialog = ({ open, onOpenChange, onSuccess }: UploadDialogProps) => {
  const [files, setFiles] = useState<File[]>([]);
  const [title, setTitle] = useState('');
  const [channel, setChannel] = useState('');
  const [styleLabel, setStyleLabel] = useState('');
  const [sceneType, setSceneType] = useState('');
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
    setChannel('');
    setStyleLabel('');
    setSceneType('');
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

  const submit = async () => {
    if (!files.length) return toast.error('请选择图片');
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
          channel,
          styleLabel,
          isSceneImage: sceneType ? sceneType === 'scene' : undefined,
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
            <div className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent text-primary">
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
              <span className="flex size-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">1</span>
              <div>
                <h2 className="text-sm font-semibold">选择图片</h2>
                <p className="mt-0.5 text-xs text-muted-foreground">图片是唯一必填项</p>
              </div>
            </div>
            <UploadAssetPicker
              files={files}
              previews={previews}
              onSelect={setFiles}
              onRemove={(file) => setFiles((items) => items.filter((item) => item !== file))}
            />
            {files.length > 1 && (
              <div className="mt-3 flex gap-2 rounded-xl border border-primary/10 bg-accent/65 px-3 py-2.5 text-xs leading-5 text-accent-foreground">
                <Info className="mt-0.5 size-3.5 shrink-0" />
                右侧渠道、风格、图片类型、卖点和话术会应用到本次选中的全部图片；图片名称默认使用各自文件名。
              </div>
            )}
          </section>

          <section className="p-5 sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <span className="flex size-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">2</span>
              <div>
                <h2 className="text-sm font-semibold">补充素材信息</h2>
                <p className="mt-0.5 text-xs text-muted-foreground">全部可选，留空也能直接发布</p>
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
                    由设计师人工填写，只用于业务端在推荐结果中继续缩小范围，不触发 AI 分析。
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-3">
                  <label className="block">
                    <span className="field-label">使用渠道</span>
                    <Input
                      value={channel}
                      onChange={(event) => setChannel(event.target.value)}
                      placeholder="例如：官网"
                      list="asset-channel-suggestions"
                      maxLength={100}
                    />
                    <datalist id="asset-channel-suggestions">
                      <option value="官网" />
                      <option value="朋友圈" />
                      <option value="公众号" />
                      <option value="小红书" />
                      <option value="线下物料" />
                    </datalist>
                    <span className="field-hint">每个版本填写一个主要渠道</span>
                  </label>
                  <label className="block">
                    <span className="field-label">画面风格</span>
                    <Input
                      value={styleLabel}
                      onChange={(event) => setStyleLabel(event.target.value)}
                      placeholder="例如：官网风格"
                      list="asset-style-suggestions"
                      maxLength={100}
                    />
                    <datalist id="asset-style-suggestions">
                      <option value="官网风格" />
                      <option value="活动专题风格" />
                      <option value="社交媒体风格" />
                      <option value="品牌宣传风格" />
                      <option value="产品功能展示风格" />
                    </datalist>
                    <span className="field-hint">可直接输入新的风格名称</span>
                  </label>
                  <label className="block">
                    <span className="field-label">是否为场景图</span>
                    <Select value={sceneType} onChange={(event) => setSceneType(event.target.value)}>
                      <option value="">暂不标注</option>
                      <option value="scene">是，场景图</option>
                      <option value="nonScene">否，功能或内容图</option>
                    </Select>
                    <span className="field-hint">未标注不会被自动判定</span>
                  </label>
                </div>
              </div>

              <div className="rounded-2xl border border-border/80 bg-card p-4">
                <div className="mb-3">
                  <p className="text-sm font-semibold">业务表达层级</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    依次选择卖点、证明点和作图依据的证据表达点；六大体系会自动带出。
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
                <p className="mt-2 text-[11px] leading-5 text-muted-foreground">
                  证据表达点就是原业务文档绿色区域的作图文案；不知道时可以先留空，之后在素材详情补充。
                </p>
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
                  <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin text-primary" />
                ) : provider.data?.configured ? (
                  <Sparkles className="mt-0.5 size-4 shrink-0 text-primary" />
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
            <CheckCircle2 className="size-4 text-success" />只要选择图片即可发布
          </div>
          <Button variant="outline" onClick={close} disabled={uploading}>取消</Button>
          <Button onClick={submit} disabled={uploading || !files.length} className="min-w-28">
            {uploading && <Loader2 className="size-4 animate-spin" />}
            {uploading ? '正在上传' : files.length > 1 ? `发布 ${files.length} 张` : '上传并发布'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default UploadDialog;
