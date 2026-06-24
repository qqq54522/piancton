import { useMemo, useState } from 'react';
import { Loader2, Upload, X } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@client/src/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@client/src/components/ui/dialog';
import { Input } from '@client/src/components/ui/input';
import TagTreeSelector from '@client/src/components/TagTreeSelector';
import type { TagWithCount } from '@client/src/types/api';
import * as imageApi from '@client/src/api/image';
import { getApiError } from '@client/src/api/client';
import { useProviderStatus } from '@client/src/features/ai/useProviderStatus';


interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tags: TagWithCount[];
  onSuccess: () => void;
}

const UploadDialog = ({ open, onOpenChange, tags, onSuccess }: UploadDialogProps) => {
  const [files, setFiles] = useState<File[]>([]);
  const [title, setTitle] = useState('');
  const [primaryTagId, setPrimaryTagId] = useState<string | null>(null);
  const [additionalTagIds, setAdditionalTagIds] = useState<string[]>([]);
  const [categories, setCategories] = useState<string[]>(['function']);
  const [uploading, setUploading] = useState(false);
  const provider = useProviderStatus(open);

  const previews = useMemo(
    () => files.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [files],
  );

  const reset = () => {
    previews.forEach((item) => URL.revokeObjectURL(item.url));
    setFiles([]);
    setTitle('');
    setPrimaryTagId(null);
    setAdditionalTagIds([]);
    setCategories(['function']);
  };

  const close = () => {
    reset();
    onOpenChange(false);
  };

  const toggleTag = (tagId: string) => {
    if (tagId === primaryTagId) return;
    setAdditionalTagIds((current) =>
      current.includes(tagId)
        ? current.filter((id) => id !== tagId)
        : [...current, tagId],
    );
  };

  const selectPrimaryTag = (tagId: string) => {
    setPrimaryTagId((current) => {
      const next = current === tagId ? null : tagId;
      if (next) {
        setAdditionalTagIds((items) => items.filter((id) => id !== next));
      }
      return next;
    });
  };

  const toggleCategory = (category: string) => {
    setCategories((current) =>
      current.includes(category)
        ? current.filter((item) => item !== category)
        : [...current, category],
    );
  };

  const submit = async () => {
    if (!files.length) return toast.error('请选择图片');
    if (!primaryTagId) return toast.error('请选择一个主业务标签');
    if (!categories.length) return toast.error('请至少选择一个分类');

    setUploading(true);
    try {
      let providerConfigured = provider.data?.configured ?? false;
      try {
        providerConfigured = (await imageApi.fetchProviderStatus()).configured;
      } catch {
        // 上传接口会在后端再次判断是否已配置模型，这里只影响提示文案。
      }
      for (const [index, file] of files.entries()) {
        const fileTitle =
          files.length === 1 && title.trim()
            ? title.trim()
            : file.name.replace(/\.[^.]+$/, '');
        await imageApi.uploadImage(
          file,
          fileTitle || `图片 ${index + 1}`,
          [primaryTagId, ...additionalTagIds.filter((id) => id !== primaryTagId)],
          primaryTagId,
          categories,
          true,
        );
      }
      if (providerConfigured) {
        toast.success(`成功上传 ${files.length} 张图片，AI 正在后台自动分析`);
      } else {
        toast.success(`成功上传 ${files.length} 张图片，AI 已由后端判断是否自动分析`);
      }
      onSuccess();
      close();
    } catch (error) {
      console.error(error);
      toast.error(getApiError(error).message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(value) => (value ? onOpenChange(true) : close())}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>上传图片</DialogTitle>
        </DialogHeader>

        <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-border p-8 transition-colors hover:bg-muted/50">
          <Upload className="size-8 text-muted-foreground" />
          <span className="mt-2 text-sm text-muted-foreground">点击选择本地图片，可多选</span>
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
            placeholder="图片标题（留空则使用文件名）"
          />
        )}

        <div>
          <p className="mb-2 text-sm font-medium">主业务标签</p>
          <p className="mb-2 text-xs text-muted-foreground">
            选择图片最核心的业务归属，系统会按这个标签保存设计师原始意图。
          </p>
          <TagTreeSelector
            tags={tags}
            selectedIds={primaryTagId ? [primaryTagId] : []}
            onToggle={selectPrimaryTag}
            placeholder="选择主业务标签"
            expandable
            assignableOnly
          />
        </div>

        <div>
          <p className="mb-2 text-sm font-medium">附加标签（可选）</p>
          <p className="mb-2 text-xs text-muted-foreground">
            如果这张图还适合其他业务表达，可以在这里补充；AI 分析后也会给出自动建议。
          </p>
          <TagTreeSelector
            tags={tags}
            selectedIds={additionalTagIds.filter((id) => id !== primaryTagId)}
            onToggle={toggleTag}
            placeholder="选择附加标签"
            expandable
            assignableOnly
          />
        </div>

        <div>
          <p className="mb-2 text-sm font-medium">分类</p>
          <div className="flex gap-2">
            {[
              ['scene', '场景'],
              ['function', '功能'],
            ].map(([value, label]) => (
              <Button
                key={value}
                type="button"
                size="sm"
                variant={categories.includes(value) ? 'default' : 'outline'}
                onClick={() => toggleCategory(value)}
              >
                {label}
              </Button>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          {provider.isLoading
            ? '正在检查 AI 分析服务…'
            : provider.data?.configured
              ? '上传成功后将自动生成语义总结、约 20 个隐形内容标签，并匹配封闭业务标签。'
              : 'AI 服务未配置，本次只上传图片，不会生成自动分析结果。'}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={close} disabled={uploading}>
            取消
          </Button>
          <Button
            onClick={submit}
            disabled={
              uploading
              || !files.length
              || !primaryTagId
              || !categories.length
            }
          >
            {uploading && <Loader2 className="mr-2 size-4 animate-spin" />}
            上传
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default UploadDialog;
