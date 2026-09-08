import { Download, Loader2 } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { useAssetActions } from '@client/src/features/assets/useAssetActions';
import { useAssetGroup } from '@client/src/features/assets/useAssetGroup';
import { useBusinessConcepts } from '@client/src/features/assets/useBusinessConcepts';
import AssetConceptReviewPanel from './AssetConceptReviewPanel';
import AssetSourceLinksPanel from './AssetSourceLinksPanel';
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
      <div className="surface-card mt-6 flex justify-center py-10">
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!group.data) return null;

  return (
    <div className="mt-10 space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="section-kicker">Asset Workspace</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight">素材工作台</h2>
          <p className="mt-1 text-sm text-muted-foreground">在这里持续维护版本、来源和业务卖点归属。</p>
        </div>
        {editable && (
          <Button variant="outline" size="sm" asChild>
            <a href={`/api/asset-groups/${groupId}/export`}>
              <Download className="size-4" />导出素材包
            </a>
          </Button>
        )}
      </div>
      <AssetVersionsPanel
        group={group.data}
        editable={editable}
        actions={actions}
        onPrimaryChanged={onPrimaryChanged}
      />
      {editable && (
        <>
          <AssetSourceLinksPanel group={group.data} actions={actions} />
          <AssetConceptReviewPanel
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
