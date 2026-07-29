import { useEffect, useState } from 'react';
import { Loader2, Save } from 'lucide-react';
import { toast } from 'sonner';

import { getApiError } from '@client/src/api/client';
import { Button } from '@client/src/components/ui/button';
import { BusinessClassificationFields } from '@client/src/features/assets/BusinessClassificationFields';
import type { useAssetActions } from '@client/src/features/assets/useAssetActions';
import type {
  AssetGroup,
  BusinessConcept,
  BusinessFacetCatalog,
} from '@client/src/types/api';

type AssetActions = ReturnType<typeof useAssetActions>;

interface AssetBusinessClassificationPanelProps {
  group: AssetGroup;
  concepts: BusinessConcept[];
  facets: BusinessFacetCatalog;
  actions: AssetActions;
}

function AssetBusinessClassificationPanel({
  group,
  concepts,
  facets,
  actions,
}: AssetBusinessClassificationPanelProps) {
  const expressed = group.conceptLinks.find(
    (link) => link.relationRole === 'expresses' && link.reviewStatus === 'accepted',
  );
  const [conceptId, setConceptId] = useState(expressed?.conceptId ?? '');
  const [proofPointCode, setProofPointCode] = useState(group.primaryProofPointCode ?? '');
  const [evidencePointCode, setEvidencePointCode] = useState(group.primaryEvidencePointCode ?? '');

  useEffect(() => {
    setConceptId(expressed?.conceptId ?? '');
    setProofPointCode(group.primaryProofPointCode ?? '');
    setEvidencePointCode(group.primaryEvidencePointCode ?? '');
  }, [expressed?.conceptId, group.primaryProofPointCode, group.primaryEvidencePointCode]);

  const save = async () => {
    try {
      await actions.updateBusinessClassification.mutateAsync({
        conceptId: conceptId || null,
        proofPointCode: proofPointCode || null,
        evidencePointCode: evidencePointCode || null,
      });
      toast.success('业务表达层级已保存');
    } catch (error) {
      toast.error(getApiError(error).message);
    }
  };

  return (
    <section className="surface-card p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold">业务表达层级</h3>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            标注素材主要属于哪个卖点和证明点。
          </p>
        </div>
        <Button
          size="sm"
          onClick={save}
          disabled={actions.updateBusinessClassification.isPending}
        >
          {actions.updateBusinessClassification.isPending
            ? <Loader2 className="size-4 animate-spin" />
            : <Save className="size-4" />}
          保存层级
        </Button>
      </div>
      <BusinessClassificationFields
        concepts={concepts}
        facets={facets}
        conceptId={conceptId}
        proofPointCode={proofPointCode}
        evidencePointCode={evidencePointCode}
        disabled={actions.updateBusinessClassification.isPending}
        onConceptChange={(value) => {
          setConceptId(value);
          setProofPointCode('');
          setEvidencePointCode('');
        }}
        onProofPointChange={(value) => {
          setProofPointCode(value);
          setEvidencePointCode('');
        }}
        onEvidencePointChange={setEvidencePointCode}
      />
    </section>
  );
}

export default AssetBusinessClassificationPanel;
