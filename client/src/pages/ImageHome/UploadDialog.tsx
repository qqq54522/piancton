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
import { useBusinessConcepts } from '@client/src/features/assets/useBusinessConcepts';
import UploadAssetPicker from './UploadAssetPicker';
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
  const [conceptId, setConceptId] = useState('');
  const [expectedSearchWords, setExpectedSearchWords] = useState(['']);
  const [uploading, setUploading] = useState(false);
  const provider = useProviderStatus(open);
  const concepts = useBusinessConcepts(open);
  const previews = useMemo(
    () => files.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [files],
  );

  useEffect(() => () => {
    previews.forEach((item) => URL.revokeObjectURL(item.url));
  }, [previews]);

  const reset = () => {
    setFiles([]);
    setTitle('');
    setChannel('');
    setConceptId('');
    setExpectedSearchWords(['']);
  };
  const close = () => {
    reset();
    onOpenChange(false);
  };

  const submit = async () => {
    if (!files.length) return toast.error('请选择图片');
    setUploading(true);
    try {
      for (const [index, file] of files.entries()) {
        const fileTitle = files.length === 1 && title.trim()
          ? title.trim()
          : file.name.replace(/\.[^.]+$/, '') || `图片 ${index + 1}`;
        const image = await imageApi.uploadImage({
          file,
          title: fileTitle,
          channel,
          expectedSearchWords: normalizeExpectedSearchWords(expectedSearchWords),
          autoAnalyze: true,
        });
        if (conceptId && image.assetGroupId) {
          await assetApi.confirmAssetConcept(image.assetGroupId, conceptId, 'expresses');
        }
      }
      toast.success(
        provider.data?.configured
          ? `已上传 ${files.length} 张主图，AI 正在后台分析`
          : `已上传 ${files.length} 张主图`,
      );
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
                右侧渠道、卖点和话术会应用到本次选中的全部图片；图片名称默认使用各自文件名。
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
              {files.length === 1 && (
                <label className="block">
                  <span className="field-label">素材名称</span>
                  <Input
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    placeholder={files[0]?.name.replace(/\.[^.]+$/, '') || '留空则使用文件名'}
                    maxLength={200}
                  />
                </label>
              )}

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className="field-label">使用渠道</span>
                  <Input
                    value={channel}
                    onChange={(event) => setChannel(event.target.value)}
                    placeholder="官网、朋友圈、公众号"
                    maxLength={100}
                  />
                  <span className="field-hint">用于筛选合适尺寸和使用场景</span>
                </label>
                <label className="block">
                  <span className="field-label">主要表达卖点</span>
                  <Select value={conceptId} onChange={(event) => setConceptId(event.target.value)}>
                    <option value="">交给 AI 建议或稍后确认</option>
                    {(concepts.data ?? []).map((concept) => (
                      <option key={concept.id} value={concept.id}>{concept.name}</option>
                    ))}
                  </Select>
                  <span className="field-hint">选择具体卖点；六大体系关系会自动复用</span>
                </label>
              </div>

              <UploadSearchPhraseFields values={expectedSearchWords} onChange={setExpectedSearchWords} />

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
                      ? '发布后会在后台执行 OCR、画面分析、卖点建议和搜索索引更新，不会阻塞当前上传。'
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
