import { useState } from 'react';
import { ArrowUpRight, BookOpenText, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

import { getApiError } from '@client/src/api/client';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { useBusinessConceptActions } from '@client/src/features/assets/useBusinessConceptActions';
import { splitAcceptedConceptPhrases } from '@client/src/features/assets/conceptPhrasePresentation';
import { useAuth } from '@client/src/lib/auth';
import type { BusinessConcept } from '@client/src/types/api';

export default function ConceptPhraseInheritancePanel({ concept }: { concept: BusinessConcept }) {
  const { user } = useAuth();
  const actions = useBusinessConceptActions();
  const [phrase, setPhrase] = useState('');
  const accepted = splitAcceptedConceptPhrases(concept.searchPhrases);
  const canManage = user?.role === 'admin';

  const addPhrase = async () => {
    if (!phrase.trim()) return;
    try {
      await actions.addPhrase.mutateAsync({
        conceptId: concept.id,
        input: {
          phrase: phrase.trim(),
          phraseType: 'colloquial',
          origin: 'manual',
          reviewStatus: 'accepted',
        },
      });
      setPhrase('');
      toast.success(`已添加为“${concept.name}”公共话术`);
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  return (
    <section className="rounded-2xl border border-primary/15 bg-accent/45 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 gap-2.5">
          <BookOpenText className="mt-0.5 size-4 shrink-0 text-primary" />
          <div>
            <h3 className="text-sm font-semibold">已继承“{concept.name}”公共话术</h3>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              公共话术只在卖点层维护一次，不需要在当前素材重复填写。
            </p>
          </div>
        </div>
        {canManage && (
          <Button variant="ghost" size="sm" asChild className="shrink-0">
            <Link to={`/admin/concepts?concept=${concept.id}`} target="_blank" rel="noreferrer">
              管理 <ArrowUpRight className="size-3.5" />
            </Link>
          </Button>
        )}
      </div>

      {accepted.publicPhrases.length > 0 ? (
        <div className="mt-3">
          <div className="flex flex-wrap gap-1.5">
            {accepted.publicPhrases.slice(0, 5).map((item) => (
              <Badge key={item.id} variant="secondary">{item.phrase}</Badge>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            共 {accepted.publicPhrases.length} 条已确认公共话术
            {accepted.keywords.length > 0 ? `，另有 ${accepted.keywords.length} 个辅助关键词` : ''}
            {accepted.publicPhrases.length > 5 ? '；这里只展示前 5 条。' : '。'}
          </p>
        </div>
      ) : canManage ? (
        <div className="mt-3 rounded-xl border border-dashed border-primary/25 bg-card/70 p-3">
          <p className="mb-2 text-xs font-medium">这个卖点还没有公共话术，先补充一种通用说法</p>
          <div className="flex gap-2">
            <Input
              value={phrase}
              onChange={(event) => setPhrase(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && phrase.trim()) addPhrase();
              }}
              placeholder={`例如：业务人员可能怎样搜索“${concept.name}”`}
              maxLength={300}
              className="h-9 bg-card"
            />
            <Button size="sm" onClick={addPhrase} disabled={!phrase.trim() || actions.addPhrase.isPending}>
              <Plus className="size-4" />添加
            </Button>
          </div>
        </div>
      ) : (
        <p className="mt-3 rounded-xl border border-dashed px-3 py-2 text-xs text-muted-foreground">
          暂无已确认公共话术；可以继续上传，之后由管理员在卖点管理中补充。
        </p>
      )}
    </section>
  );
}
