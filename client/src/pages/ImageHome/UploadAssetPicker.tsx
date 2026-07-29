import { FileImage, Images, Upload, X } from 'lucide-react';

interface PreviewItem {
  file: File;
  url: string;
}

interface UploadAssetPickerProps {
  files: File[];
  previews: PreviewItem[];
  onSelect: (files: File[]) => void;
  onRemove: (file: File) => void;
}

export default function UploadAssetPicker({ files, previews, onSelect, onRemove }: UploadAssetPickerProps) {
  if (!files.length) {
    return (
      <label className="group flex min-h-72 cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-foreground/15 bg-card px-6 text-center transition hover:border-foreground/35 hover:bg-[#f7f7f5]">
        <div className="flex size-12 items-center justify-center rounded-2xl bg-[#f1f1ef] text-foreground transition-transform group-hover:scale-105">
          <Upload className="size-5" />
        </div>
        <span className="mt-4 text-sm font-semibold text-foreground">选择主图</span>
        <span className="mt-1.5 max-w-xs text-xs leading-5 text-muted-foreground">
          支持一次选择多张图片；每张图片会建立独立素材组。
        </span>
        <span className="mt-4 rounded-full border border-border bg-secondary px-3 py-1.5 text-xs font-medium text-foreground">
          浏览文件
        </span>
        <input
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(event) => onSelect(Array.from(event.target.files || []))}
        />
      </label>
    );
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Images className="size-4 text-foreground" />已选择 {files.length} 张
        </div>
        <label className="cursor-pointer text-xs font-medium text-foreground hover:underline">
          重新选择
          <input
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(event) => onSelect(Array.from(event.target.files || []))}
          />
        </label>
      </div>

      <div className={previews.length === 1 ? '' : 'grid grid-cols-2 gap-3'}>
        {previews.map(({ file, url }) => (
          <figure key={`${file.name}-${file.lastModified}`} className="group relative overflow-hidden rounded-2xl border border-border bg-white shadow-sm">
            <img
              src={url}
              alt={file.name}
              className={previews.length === 1 ? 'h-[310px] w-full object-contain' : 'aspect-square w-full object-cover'}
            />
            <button
              type="button"
              aria-label={`移除 ${file.name}`}
              className="absolute right-2 top-2 flex size-8 items-center justify-center rounded-full bg-slate-950/65 text-white opacity-90 backdrop-blur transition hover:bg-slate-950"
              onClick={() => onRemove(file)}
            >
              <X className="size-4" />
            </button>
            <figcaption className="flex items-center gap-2 border-t border-border/70 bg-card px-3 py-2 text-xs text-muted-foreground">
              <FileImage className="size-3.5 shrink-0" />
              <span className="truncate">{file.name}</span>
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}
