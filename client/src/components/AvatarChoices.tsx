import { useEffect, useState } from 'react';
import { Camera } from 'lucide-react';

import { AVATAR_PRESETS, PresetAvatar, type AvatarPresetId } from './AccountAvatar';

interface AvatarChoicesProps {
  presetId: AvatarPresetId;
  onPresetChange: (id: AvatarPresetId) => void;
  file: File | null;
  onFileChange: (file: File | null) => void;
  disabled?: boolean;
}

export default function AvatarChoices({ presetId, onPresetChange, file, onFileChange, disabled }: AvatarChoicesProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!file) { setPreviewUrl(null); return; }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  return (
    <fieldset disabled={disabled} className="space-y-3">
      <legend className="text-sm font-semibold">选一个自己的头像</legend>
      <p className="text-xs text-muted-foreground">先选喜欢的颜色，也可以上传自己的照片。以后点账号头像还能更换。</p>
      <div className="flex flex-wrap gap-2" aria-label="预设头像">
        {AVATAR_PRESETS.map(({ id, label }) => (
          <button key={id} type="button" aria-label={`选择${label}头像`} aria-pressed={!file && presetId === id}
            onClick={() => { onPresetChange(id); onFileChange(null); }}
            className={`rounded-full p-0.5 transition hover:scale-105 ${!file && presetId === id ? 'ring-2 ring-foreground ring-offset-2' : 'ring-1 ring-border'}`}>
            <PresetAvatar id={id} />
          </button>
        ))}
        <label className={`flex size-12 cursor-pointer items-center justify-center overflow-hidden rounded-full border border-dashed border-foreground/50 bg-secondary/60 text-foreground hover:bg-secondary ${file ? 'ring-2 ring-foreground ring-offset-2' : ''}`} title="上传自己的头像">
          {previewUrl ? <img src={previewUrl} alt="待上传头像预览" className="size-full object-cover" /> : <Camera className="size-5" />}
          <input aria-label="上传自己的头像" type="file" accept="image/jpeg,image/png,image/webp,image/gif" className="sr-only"
            onChange={(event) => onFileChange(event.target.files?.[0] || null)} />
        </label>
      </div>
      {file && <p className="text-xs text-foreground">已选 {file.name} · 登录后保存到你的账号</p>}
      <p className="text-xs text-muted-foreground">自定义头像支持 JPG、PNG、WebP、GIF，文件不超过 2 MB。</p>
    </fieldset>
  );
}
