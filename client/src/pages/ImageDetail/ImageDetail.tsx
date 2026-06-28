import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { ROLE_SUBJECT, useAuth } from '@client/src/lib/auth';
import { useProviderStatus } from '@client/src/features/ai/useProviderStatus';
import { useImageDetail } from '@client/src/features/images/useImageDetail';
import { useImageDetailActions } from '@client/src/features/images/useImageDetailActions';
import { useTags } from '@client/src/features/tags/useTags';
import { useImageUrl } from '@client/src/hooks/useImageUrl';
import ImageDeleteDialog from './ImageDeleteDialog';
import ImageDetailInfoPanel from './ImageDetailInfoPanel';
import RelatedImagesStrip from './RelatedImagesStrip';

const ImageDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const detailQuery = useImageDetail(id);
  const tagsQuery = useTags();
  const detail = detailQuery.data ?? null;
  const allTags = tagsQuery.data ?? [];
  const loading = detailQuery.isLoading || tagsQuery.isLoading;
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
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <div className="mb-4">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          返回
        </button>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        <div className="flex-1 overflow-hidden rounded-xl bg-[#1a1a2e] lg:max-w-[65%]">
          <img
            src={mainImageUrl}
            alt={detail.title}
            className="mx-auto max-h-[70vh] w-full object-contain"
          />
        </div>

        <div className="flex-1 lg:max-w-[35%]">
          <ImageDetailInfoPanel
            detail={detail}
            allTags={allTags}
            isDesigner={isDesigner}
            provider={provider}
            actions={actions}
          />
        </div>
      </div>

      <RelatedImagesStrip images={detail.relatedImages} />

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
