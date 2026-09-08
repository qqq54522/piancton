import { useEffect, useMemo, useState } from 'react';
import { Loader2, Save } from 'lucide-react';
import { toast } from 'sonner';

import { getApiError } from '@client/src/api/client';
import { Button } from '@client/src/components/ui/button';
import { SellingPointRelationFields } from '@client/src/features/assets/SellingPointRelationFields';
import type { useAssetActions } from '@client/src/features/assets/useAssetActions';
import type { AssetGroup, BusinessConcept } from '@client/src/types/api';

type AssetActions = ReturnType<typeof useAssetActions>;

interface AssetConceptReviewPanelProps {
  group: AssetGroup;
  concepts: BusinessConcept[];
  actions: AssetActions;
}

function AssetConceptReviewPanel({ group, concepts, actions }: AssetConceptReviewPanelProps) {
  const confirmed = useMemo(() => group.conceptLinks.filter(
    (item) => item.origin === 'manual' && item.reviewStatus === 'accepted',
  ), [group.conceptLinks]);
  const initialPrimary = confirmed.find((item) => item.relationRole === 'expresses')?.conceptId ?? '';
  const supportKey = confirmed
    .filter((item) => item.relationRole === 'supports')
    .map((item) => item.conceptId)
    .join('|');
  const [primaryConceptId, setPrimaryConceptId] = useState(initialPrimary);
  const [supportConceptIds, setSupportConceptIds] = useState(
    supportKey ? supportKey.split('|') : [],
  );

  useEffect(() => {
    setPrimaryConceptId(initialPrimary);
    setSupportConceptIds(supportKey ? supportKey.split('|') : []);
  }, [initialPrimary, supportKey]);

  const save = async () => {
    try {
      await actions.replaceConceptRelations.mutateAsync([
        ...(primaryConceptId
          ? [{ conceptId: primaryConceptId, relationRole: 'expresses' as const }]
          : []),
        ...supportConceptIds.map((conceptId) => ({
          conceptId,
          relationRole: 'supports' as const,
        })),
      ]);
      toast.success('卖点关系已保存');
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  return (
    <section className="surface-card p-5 sm:p-6">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">卖点关系</h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            一次确认这张素材主要表达什么、还能支持什么；这不是图片质量评分。
          </p>
        </div>
        <Button
          size="sm"
          onClick={save}
          disabled={actions.replaceConceptRelations.isPending}
        >
          {actions.replaceConceptRelations.isPending
            ? <Loader2 className="size-4 animate-spin" />
            : <Save className="size-4" />}
          保存卖点关系
        </Button>
      </div>

      <SellingPointRelationFields
        concepts={concepts}
        primaryConceptId={primaryConceptId}
        supportConceptIds={supportConceptIds}
        disabled={actions.replaceConceptRelations.isPending}
        onPrimaryConceptChange={setPrimaryConceptId}
        onSupportConceptIdsChange={setSupportConceptIds}
      />
    </section>
  );
}

export default AssetConceptReviewPanel;
