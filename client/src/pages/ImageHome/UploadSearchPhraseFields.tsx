import { Plus, X } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { INITIAL_UPLOAD_SEARCH_PHRASE_LIMIT } from './uploadSearchPhrases';

interface UploadSearchPhraseFieldsProps {
  values: string[];
  onChange: (values: string[]) => void;
}

export default function UploadSearchPhraseFields({ values, onChange }: UploadSearchPhraseFieldsProps) {
  const update = (index: number, value: string) => {
    onChange(values.map((item, itemIndex) => (itemIndex === index ? value : item)));
  };
  const remove = (index: number) => {
    onChange(values.filter((_, itemIndex) => itemIndex !== index));
  };
  const atLimit = values.length >= INITIAL_UPLOAD_SEARCH_PHRASE_LIMIT;

  return (
    <div className="rounded-2xl border border-border/80 bg-secondary/45 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold">当前素材独有话术</h3>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            只写这张图片区别于同卖点其他素材的画面、文案或场景说法。
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-card px-2.5 py-1 text-[11px] text-muted-foreground shadow-xs">
          首次 {values.length}/{INITIAL_UPLOAD_SEARCH_PHRASE_LIMIT}
        </span>
      </div>

      <div className="mt-3 space-y-2">
        {values.map((value, index) => (
          <div key={index} className="flex items-center gap-2">
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-card text-xs font-semibold text-muted-foreground shadow-xs">
              {index + 1}
            </span>
            <Input
              value={value}
              onChange={(event) => update(index, event.target.value)}
              aria-label={`搜索话术 ${index + 1}`}
              placeholder={index === 0 ? '例如：孩子拍题只抄答案怎么办' : '再补充一种可能的搜索说法'}
              maxLength={300}
              className="bg-card"
            />
            {values.length > 1 && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="size-9 shrink-0"
                aria-label={`删除第 ${index + 1} 条搜索话术`}
                onClick={() => remove(index)}
              >
                <X className="size-4" />
              </Button>
            )}
          </div>
        ))}
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onChange([...values, ''])}
          disabled={atLimit}
        >
          <Plus className="size-4" />添加另一种说法
        </Button>
        <span className="text-[11px] text-muted-foreground">
          {atLimit ? '已达首次上限；发布后可在详情继续维护' : '建议 3～5 条，通用说法不要在这里重复填写'}
        </span>
      </div>
    </div>
  );
}
