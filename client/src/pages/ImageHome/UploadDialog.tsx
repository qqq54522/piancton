import { useEffect, useMemo, useState } from 'react';
import { Loader2, Upload, X } from 'lucide-react';
import { toast } from 'sonner';

import * as assetApi from '@client/src/api/asset';
import { getApiError } from '@client/src/api/client';
import * as imageApi from '@client/src/api/image';
import { Button } from '@client/src/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@client/src/components/ui/dialog';
import { Input } from '@client/src/components/ui/input';
import { useProviderStatus } from '@client/src/features/ai/useProviderStatus';
import { useBusinessConcepts } from '@client/src/features/assets/useBusinessConcepts';

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
  const [expectedSearchWords, setExpectedSearchWords] = useState('');
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
    setExpectedSearchWords('');
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
          expectedSearchWords: expectedSearchWords
            .split('\n')
            .map((item) => item.trim())
            .filter(Boolean)
            .slice(0, 5),
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
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>上传主图</DialogTitle>
        </DialogHeader>

        <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800">
          只选图片即可发布。业务概念、渠道和搜索话术都可以稍后在素材详情中补充。
        </div>

        <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-border p-8 transition-colors hover:bg-muted/50">
          <Upload className="size-8 text-muted-foreground" />
          <span className="mt-2 text-sm text-muted-foreground">点击选择主图，可多选</span>
          <input
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(event) => setFiles(Array.from(event.target.files || []))}
          />
        </label>

        {previews.length > 0 && (
          <div className="grid grid-cols-3 gap-3">
            {previews.map(({ file, url }) => (
              <div key={`${file.name}-${file.lastModified}`} className="group relative overflow-hidden rounded-lg border">
                <img src={url} alt={file.name} className="aspect-square size-full object-cover" />
                <button
                  type="button"
                  aria-label={`移除 ${file.name}`}
                  className="absolute right-1 top-1 rounded-full bg-black/60 p-1 text-white"
                  onClick={() => setFiles((items) => items.filter((item) => item !== file))}
                >
                  <X className="size-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        {files.length === 1 && (
          <Input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="图片名称（留空则使用文件名）"
          />
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-2 text-sm font-medium">
            <span>使用渠道（可选）</span>
            <Input
              value={channel}
              onChange={(event) => setChannel(event.target.value)}
              placeholder="例如：官网、朋友圈、公众号"
              maxLength={100}
            />
          </label>
          <label className="space-y-2 text-sm font-medium">
            <span>主要表达概念（可选）</span>
            <select
              value={conceptId}
              onChange={(event) => setConceptId(event.target.value)}
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">交给 AI 建议或稍后确认</option>
              {(concepts.data ?? []).map((concept) => (
                <option key={concept.id} value={concept.id}>{concept.name}</option>
              ))}
            </select>
          </label>
        </div>

        <label className="block">
          <span className="mb-2 block text-sm font-medium">业务人员可能怎么搜索（可选）</span>
          <textarea
            value={expectedSearchWords}
            onChange={(event) => setExpectedSearchWords(event.target.value)}
            className="min-h-20 w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
            placeholder={'每行一句，例如：\n孩子拍题只抄答案怎么办\n整理错题太费时间'}
            maxLength={500}
          />
        </label>

        <p className="text-xs text-muted-foreground">
          {provider.isLoading
            ? '正在检查 AI 分析服务…'
            : provider.data?.configured
              ? '上传后自动执行 OCR、客观画面分析、概念建议和搜索索引更新。'
              : 'AI 未配置时仍可正常上传和发布，之后可以补做分析。'}
        </p>

        <DialogFooter>
          <Button variant="outline" onClick={close} disabled={uploading}>取消</Button>
          <Button onClick={submit} disabled={uploading || !files.length}>
            {uploading && <Loader2 className="mr-2 size-4 animate-spin" />}
            上传并发布
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default UploadDialog;
