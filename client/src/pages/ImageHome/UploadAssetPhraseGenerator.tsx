import { Loader2, Sparkles } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { Select } from '@client/src/components/ui/select';

interface UploadAssetPhraseGeneratorProps {
  count: number;
  onCountChange: (count: number) => void;
  onGenerate: () => void;
  generating: boolean;
  disabled: boolean;
  hint: string;
}

export default function UploadAssetPhraseGenerator({
  count,
  onCountChange,
  onGenerate,
  generating,
  disabled,
  hint,
}: UploadAssetPhraseGeneratorProps) {
  return (
    <div className="mt-3 rounded-xl border border-border/80 bg-[#f7f7f5] p-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-xs font-semibold text-foreground">
            <Sparkles className="size-4 text-foreground/70" />AI 生成业务搜索话术
          </p>
          <p className="mt-1 text-[11px] leading-4 text-muted-foreground">{hint}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <div className="w-28">
            <Select
              aria-label="AI 生成话术数量"
              value={String(count)}
              disabled={generating}
              onChange={(event) => onCountChange(Number(event.target.value))}
              className="h-9 bg-card"
            >
              {[2, 3, 4, 5].map((value) => (
                <option key={value} value={value}>生成 {value} 条</option>
              ))}
            </Select>
          </div>
          <Button
            type="button"
            size="sm"
            className="bg-foreground text-background hover:bg-foreground/88"
            onClick={onGenerate}
            disabled={disabled || generating}
          >
            {generating ? <Loader2 className="animate-spin" /> : <Sparkles />}
            {generating ? '正在分析' : '生成并填充'}
          </Button>
        </div>
      </div>
    </div>
  );
}
