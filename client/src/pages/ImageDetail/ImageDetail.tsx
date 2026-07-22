import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { ROLE_SUBJECT, useAuth } from '@client/src/lib/auth';
import { useProviderStatus } from '@client/src/features/ai/useProviderStatus';
import { useImageDetail } from '@client/src/features/images/useImageDetail';
import { useImageDetailActions } from '@client/src/features/images/useImageDetailActions';
import { useImageUrl } from '@client/src/hooks/useImageUrl';
import ImageDeleteDialog from './ImageDeleteDialog';
import ImageDetailInfoPanel from './ImageDetailInfoPanel';
import RelatedImagesStrip from './RelatedImagesStrip';
import AssetWorkspacePanel from './asset/AssetWorkspacePanel';

const ImageDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const returnTo = (location.state as { from?: string } | null)?.from;
  const detailQuery = useImageDetail(id);
  const detail = detailQuery.data ?? null;
  const loading = detailQuery.isLoading;
  const mainImageUrl = useImageUrl(detail?.contentUrl ?? '');
  const canDesign = useAuth();
  const isDesigner = !canDesign.isLoading && canDesign.ability.can('designer', ROLE_SUBJECT);
  const provider = useProviderStatus(isDesigner);
  const actions = useImageDetailActions(detail);

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center gap-3">
        <p className="text-muted-foreground">图片不存在</p>
        <Button variant="outline" onClick={() => navigate('/')}>
          返回首页
        </Button>
      </div>
    );
  }

  return (
    <div className="page-shell">
      <div className="mb-5 flex items-center gap-2 text-sm">
        <button
          type="button"
          onClick={() => (returnTo ? navigate(returnTo) : navigate(-1))}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          素材库
        </button>
        <span className="text-border">/</span>
        <span className="max-w-64 truncate text-muted-foreground">{detail.title}</span>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.55fr)_minmax(340px,0.75fr)]">
        <div className="surface-card flex min-h-[420px] items-center justify-center overflow-hidden bg-[linear-gradient(135deg,#f1f5f9_25%,transparent_25%),linear-gradient(225deg,#f1f5f9_25%,transparent_25%),linear-gradient(45deg,#f1f5f9_25%,transparent_25%),linear-gradient(315deg,#f1f5f9_25%,#fff_25%)] bg-[length:24px_24px] bg-[position:12px_0,12px_0,0_0,0_0] p-4">
          <img
            src={mainImageUrl}
            alt={detail.title}
            className="mx-auto max-h-[72vh] w-full rounded-xl object-contain shadow-sm"
          />
        </div>

        <div>
          <ImageDetailInfoPanel
            detail={detail}
            isDesigner={isDesigner}
            provider={provider}
            actions={actions}
          />
        </div>
      </div>

      <RelatedImagesStrip images={detail.relatedImages} />

      {detail.assetGroupId && (
        <AssetWorkspacePanel
          groupId={detail.assetGroupId}
          editable={isDesigner}
          onPrimaryChanged={(imageId) => navigate(`/image/${imageId}`, { replace: true })}
        />
      )}

      <ImageDeleteDialog
        title={detail.title}
        open={actions.showDeleteDialog}
        deleting={actions.deleting}
        onOpenChange={actions.setShowDeleteDialog}
        onConfirm={() => actions.remove()}
      />
    </div>
  );
};

export default ImageDetail;
