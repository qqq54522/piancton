import { useEffect, useState } from 'react';
import { Loader2, Upload } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@client/src/components/ui/dialog';
import { Input } from '@client/src/components/ui/input';
import { Select } from '@client/src/components/ui/select';

interface AssetVersionDialogProps {
  open: boolean;
  mode: 'variant' | 'replace';
  pending: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (input: {
    file: File;
    title?: string;
    channel?: string;
    role: 'derivative' | 'alternative';
  }) => Promise<void>;
}

function AssetVersionDialog({
  open,
  mode,
  pending,
  onOpenChange,
  onSubmit,
}: AssetVersionDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [role, setRole] = useState<'derivative' | 'alternative'>('derivative');

  useEffect(() => {
    if (!open) {
      setFile(null);
      setTitle('');
      setRole('derivative');
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{mode === 'replace' ? '替换正式主图' : '添加延展版本'}</DialogTitle>
        </DialogHeader>
        <div className="rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          {mode === 'replace'
            ? '新图将成为正式主图并继承原主图渠道，旧主图保留为历史修订版；已确认的素材组概念关系和搜索语不会丢失。'
            : role === 'derivative'
              ? '尺寸延展只上传文件并识别尺寸，不运行 AI 分析；自动继承主图渠道、关系和话术，搜索结果仍只占一个位置。'
              : '同主题备选图会继承主图渠道并单独分析画面，但不会改动素材组已确认关系和话术。'}
        </div>
        <label className="flex cursor-pointer items-center justify-center rounded-lg border-2 border-dashed p-6 text-sm text-muted-foreground hover:bg-muted/50">
          <Upload className="mr-2 size-4" />
          {file ? file.name : '选择图片文件'}
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="名称（留空使用文件名）" />
        {mode === 'variant' && (
          <label className="text-sm">
            <span className="mb-2 block font-medium">版本类型</span>
            <Select
              value={role}
              onChange={(event) => setRole(event.target.value as typeof role)}
            >
              <option value="derivative">尺寸/渠道延展</option>
              <option value="alternative">同主题备选图</option>
            </Select>
          </label>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>取消</Button>
          <Button
            disabled={!file || pending}
            onClick={async () => {
              if (!file) return;
              await onSubmit({ file, title, role });
            }}
          >
            {pending && <Loader2 className="mr-2 size-4 animate-spin" />}
            {mode === 'replace' ? '确认替换' : '添加版本'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default AssetVersionDialog;
