import { Loader2 } from 'lucide-react';

import { useAssetActions } from '@client/src/features/assets/useAssetActions';
import { useAssetGroup } from '@client/src/features/assets/useAssetGroup';
import { useBusinessConcepts } from '@client/src/features/assets/useBusinessConcepts';
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
  const actions = useAssetActions(groupId);

  if (group.isLoading) {
    return (
      <div className="mt-6 flex justify-center rounded-xl border py-10">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!group.data) return null;

  return (
    <div className="mt-6 space-y-5">
      <AssetVersionsPanel
        group={group.data}
        editable={editable}
        actions={actions}
        onPrimaryChanged={onPrimaryChanged}
      />
      {editable && (
        <>
          <AssetConceptReviewPanel
            group={group.data}
            concepts={concepts.data ?? []}
            actions={actions}
          />
          <AssetPhraseReviewPanel group={group.data} actions={actions} />
        </>
      )}
    </div>
  );
}

export default AssetWorkspacePanel;
