import { Loader2 } from 'lucide-react';

import { useAssetActions } from '@client/src/features/assets/useAssetActions';
import { useAssetGroup } from '@client/src/features/assets/useAssetGroup';
import { useBusinessConcepts } from '@client/src/features/assets/useBusinessConcepts';
import { useBusinessFacets } from '@client/src/features/assets/useBusinessFacets';
import AssetBusinessClassificationPanel from './AssetBusinessClassificationPanel';
import AssetConceptReviewPanel from './AssetConceptReviewPanel';
import AssetPhraseReviewPanel from './AssetPhraseReviewPanel';
import AssetVersionsPanel from './AssetVersionsPanel';

interface AssetWorkspacePanelProps {
  groupId: string;
  editable: boolean;
  onPrimaryChanged: (imageId: string) => void;
}

function AssetWorkspacePanel({ groupId, editable, onPrimaryChanged }: AssetWorkspacePanelProps) {
  const group = useAssetGroup(groupId);
  const concepts = useBusinessConcepts(editable);
  const facets = useBusinessFacets(editable);
  const actions = useAssetActions(groupId);

  if (group.isLoading) {
    return (
      <div className="surface-card mt-6 flex justify-center py-10">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!group.data) return null;

  return (
    <div className="mt-10 space-y-5">
      <div>
        <p className="section-kicker">Asset Workspace</p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight">素材工作台</h2>
        <p className="mt-1 text-sm text-muted-foreground">在这里持续维护版本、业务卖点和后续收集到的搜索话术。</p>
      </div>
      <AssetVersionsPanel
        group={group.data}
        editable={editable}
        actions={actions}
        onPrimaryChanged={onPrimaryChanged}
      />
      {editable && (
        <>
          <AssetBusinessClassificationPanel
            group={group.data}
            concepts={concepts.data ?? []}
            facets={facets.data ?? { proofPoints: [], evidencePoints: [] }}
            actions={actions}
          />
          <AssetConceptReviewPanel
            group={group.data}
            concepts={concepts.data ?? []}
            actions={actions}
          />
          <AssetPhraseReviewPanel
            group={group.data}
            concepts={concepts.data ?? []}
            actions={actions}
          />
        </>
      )}
    </div>
  );
}

export default AssetWorkspacePanel;
