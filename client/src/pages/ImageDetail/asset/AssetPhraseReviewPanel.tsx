import { useState } from 'react';
import { Check, MessageSquarePlus, X } from 'lucide-react';
import { toast } from 'sonner';

import { getApiError } from '@client/src/api/client';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import type { AssetGroup } from '@client/src/types/api';
import type { useAssetActions } from '@client/src/features/assets/useAssetActions';

type AssetActions = ReturnType<typeof useAssetActions>;

function AssetPhraseReviewPanel({ group, actions }: { group: AssetGroup; actions: AssetActions }) {
  const [phrase, setPhrase] = useState('');
  const accepted = group.searchPhrases.filter((item) => item.reviewStatus === 'accepted');
  const pending = group.searchPhrases.filter(
    (item) => item.origin === 'ai' && item.reviewStatus === 'pending',
  );

  const addPhrase = async () => {
    if (!phrase.trim()) return;
    try {
      await actions.addPhrase.mutateAsync(phrase.trim());
      setPhrase('');
      toast.success('素材独有搜索语已添加');
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };
  const review = async (phraseId: string, reviewStatus: 'accepted' | 'rejected') => {
    try {
      await actions.reviewPhrase.mutateAsync({ phraseId, reviewStatus });
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  return (
    <section className="surface-card p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">素材独有搜索话术</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">发布后可以随搜索反馈持续补充，不受首次 5 条限制；通用话术留在卖点概念层复用。</p>
        </div>
        <span className="rounded-full bg-secondary px-2.5 py-1 text-[11px] text-muted-foreground">已确认 {accepted.length}</span>
      </div>
      <div className="mt-4 flex min-h-8 flex-wrap gap-2">
        {accepted.length > 0
          ? accepted.map((item) => <Badge key={item.id} variant="secondary">{item.phrase}</Badge>)
          : <span className="text-xs text-muted-foreground">暂无已确认的素材独有搜索语</span>}
      </div>
      {pending.length > 0 && (
        <div className="mt-4 space-y-2">
          {pending.map((item) => (
            <div key={item.id} className="flex items-center gap-2 rounded-lg border px-3 py-2">
              <span className="flex-1 text-sm">{item.phrase}</span>
              <Button variant="ghost" size="sm" onClick={() => review(item.id, 'accepted')}><Check className="size-3.5" /></Button>
              <Button variant="ghost" size="sm" onClick={() => review(item.id, 'rejected')}><X className="size-3.5" /></Button>
            </div>
          ))}
        </div>
      )}
      <div className="mt-5 rounded-xl border border-border/80 bg-secondary/40 p-3">
        <label className="field-label">添加新说法</label>
        <div className="flex gap-2">
          <Input
            value={phrase}
            onChange={(event) => setPhrase(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && phrase.trim()) addPhrase();
            }}
            placeholder="例如：蓝色竖版学习周报"
            maxLength={300}
            className="bg-card"
          />
          <Button onClick={addPhrase} disabled={!phrase.trim() || actions.addPhrase.isPending}>
            <MessageSquarePlus className="size-4" />添加
          </Button>
        </div>
      </div>
    </section>
  );
}

export default AssetPhraseReviewPanel;
