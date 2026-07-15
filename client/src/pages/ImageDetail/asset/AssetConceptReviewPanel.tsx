import { useMemo, useState } from 'react';
import { Check, Loader2, X } from 'lucide-react';
import { toast } from 'sonner';

import type { AssetRelationRole } from '@client/src/api/asset';
import { getApiError } from '@client/src/api/client';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import type { AssetGroup, BusinessConcept } from '@client/src/types/api';
import type { useAssetActions } from '@client/src/features/assets/useAssetActions';

type AssetActions = ReturnType<typeof useAssetActions>;

const ROLE_LABELS: Record<AssetRelationRole, string> = {
  expresses: '主要表达',
  supports: '可以支持',
  visual_related: '画面相关',
  excludes: '不适用 / 排除',
};

interface AssetConceptReviewPanelProps {
  group: AssetGroup;
  concepts: BusinessConcept[];
  actions: AssetActions;
}

function AssetConceptReviewPanel({ group, concepts, actions }: AssetConceptReviewPanelProps) {
  const [conceptId, setConceptId] = useState('');
  const [relationRole, setRelationRole] = useState<AssetRelationRole>('supports');
  const pending = group.conceptLinks.filter(
    (item) => item.origin === 'ai' && item.reviewStatus === 'pending',
  );
  const confirmed = group.conceptLinks.filter(
    (item) => item.origin === 'manual' && item.reviewStatus === 'accepted',
  );
  const availableConcepts = useMemo(() => {
    const confirmedIds = new Set(confirmed.map((item) => item.conceptId));
    return concepts.filter((concept) => !confirmedIds.has(concept.id));
  }, [concepts, confirmed]);

  const confirmManual = async () => {
    if (!conceptId) return;
    try {
      await actions.confirmConcept.mutateAsync({ conceptId, relationRole });
      setConceptId('');
      toast.success('业务概念关系已确认');
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };
  const reviewOne = async (linkId: string, status: 'accepted' | 'rejected') => {
    try {
      await actions.reviewConcept.mutateAsync({ linkId, reviewStatus: status });
      toast.success(status === 'accepted' ? '已接受概念建议' : '已标记为不适用');
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };
  const acceptAll = async () => {
    try {
      await actions.reviewConcepts.mutateAsync({
        linkIds: pending.map((item) => item.id),
        reviewStatus: 'accepted',
      });
      toast.success(`已批量接受 ${pending.length} 条概念建议`);
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">业务概念关系确认</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            这里只确认图片表达什么，不对图片质量打分。
          </p>
        </div>
        {pending.length > 1 && (
          <Button size="sm" variant="outline" onClick={acceptAll} disabled={actions.reviewConcepts.isPending}>
            {actions.reviewConcepts.isPending && <Loader2 className="mr-1.5 size-3.5 animate-spin" />}
            全部接受
          </Button>
        )}
      </div>

      <div className="mt-4">
        <p className="text-xs font-medium text-muted-foreground">负责人已确认</p>
        <div className="mt-2 flex min-h-8 flex-wrap gap-2">
          {confirmed.length > 0 ? confirmed.map((item) => (
            <Badge key={item.id} variant={item.relationRole === 'expresses' ? 'default' : 'outline'}>
              {item.conceptName} · {ROLE_LABELS[item.relationRole]}
            </Badge>
          )) : <span className="text-xs text-muted-foreground">尚未确认，可先发布并稍后补充。</span>}
        </div>
      </div>

      {pending.length > 0 && (
        <div className="mt-5 space-y-2">
          <p className="text-xs font-medium text-muted-foreground">AI 待确认建议</p>
          {pending.map((item) => (
            <div key={item.id} className="flex flex-col gap-2 rounded-lg border border-border px-3 py-2 sm:flex-row sm:items-center">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{item.conceptName}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  建议关系：{ROLE_LABELS[item.relationRole]}
                  {item.evidenceReason ? ` · ${item.evidenceReason}` : ''}
                </p>
              </div>
              <div className="flex gap-1">
                <Button size="sm" onClick={() => reviewOne(item.id, 'accepted')} disabled={actions.reviewConcept.isPending}>
                  <Check className="mr-1 size-3.5" />接受
                </Button>
                <Button size="sm" variant="outline" onClick={() => reviewOne(item.id, 'rejected')} disabled={actions.reviewConcept.isPending}>
                  <X className="mr-1 size-3.5" />不适用
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-5 border-t border-border pt-4">
        <p className="text-xs font-medium text-muted-foreground">手动补充确认关系</p>
        <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_150px_auto]">
          <select
            value={conceptId}
            onChange={(event) => setConceptId(event.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="">选择业务概念</option>
            {availableConcepts.map((concept) => (
              <option key={concept.id} value={concept.id}>{concept.name}</option>
            ))}
          </select>
          <select
            value={relationRole}
            onChange={(event) => setRelationRole(event.target.value as AssetRelationRole)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            {Object.entries(ROLE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <Button size="sm" onClick={confirmManual} disabled={!conceptId || actions.confirmConcept.isPending}>
            确认关系
          </Button>
        </div>
      </div>
    </section>
  );
}

export default AssetConceptReviewPanel;
