import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { ROLE_SUBJECT, useAuth } from '@client/src/lib/auth';
import { useProviderStatus } from '@client/src/features/ai/useProviderStatus';
import { useAssetGroup } from '@client/src/features/assets/useAssetGroup';
import { useImageDetail } from '@client/src/features/images/useImageDetail';
import { useImageDetailActions } from '@client/src/features/images/useImageDetailActions';
import { useImageUrl } from '@client/src/hooks/useImageUrl';
import BusinessImageDetailRecommendations, {
  BusinessImageDetailSideRecommendations,
} from './BusinessImageDetailRecommendations';
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
  const assetGroupQuery = useAssetGroup(detail?.assetGroupId);
  const loading = detailQuery.isLoading;
  const mainImageUrl = useImageUrl(detail?.contentUrl ?? '');
  const canDesign = useAuth();
  const isDesigner = !canDesign.isLoading && canDesign.ability.can('designer', ROLE_SUBJECT);
  const provider = useProviderStatus(isDesigner);
  const actions = useImageDetailActions(detail);
  const imageFrameRef = useRef<HTMLDivElement | null>(null);
  const businessRelatedRef = useRef<HTMLDivElement | null>(null);
  const businessSideRef = useRef<HTMLElement | null>(null);
  const [infoPanelHeight, setInfoPanelHeight] = useState<number | null>(null);
  const [sideRecommendationsMaxHeight, setSideRecommendationsMaxHeight] = useState<number | null>(null);

  useEffect(() => {
    const frame = imageFrameRef.current;
    if (!frame) return undefined;

    const syncPanelHeight = () => {
      if (window.innerWidth < 1024) {
        setInfoPanelHeight(null);
        return;
      }
      setInfoPanelHeight(Math.round(frame.getBoundingClientRect().height));
    };

    syncPanelHeight();
    const observer = new ResizeObserver(syncPanelHeight);
    observer.observe(frame);
    window.addEventListener('resize', syncPanelHeight);

    return () => {
      observer.disconnect();
      window.removeEventListener('resize', syncPanelHeight);
    };
  }, [detail?.id, mainImageUrl]);

  useEffect(() => {
    if (isDesigner) return undefined;

    let animationFrame = 0;
    const syncSideScrollHeight = () => {
      window.cancelAnimationFrame(animationFrame);
      animationFrame = window.requestAnimationFrame(() => {
        const related = businessRelatedRef.current;
        const side = businessSideRef.current;
        if (!related || !side || window.innerWidth < 1280) {
          setSideRecommendationsMaxHeight((current) => (current === null ? current : null));
          return;
        }

        const relatedBottom = related.getBoundingClientRect().bottom;
        const sideTop = side.getBoundingClientRect().top;
        const nextHeight = Math.max(260, Math.floor(relatedBottom - sideTop));
        setSideRecommendationsMaxHeight((current) => {
          if (current !== null && Math.abs(current - nextHeight) <= 1) return current;
          return nextHeight;
        });
      });
    };

    syncSideScrollHeight();
    const observer = new ResizeObserver(syncSideScrollHeight);
    if (businessRelatedRef.current) observer.observe(businessRelatedRef.current);
    window.addEventListener('resize', syncSideScrollHeight);
    window.addEventListener('scroll', syncSideScrollHeight, { passive: true });

    return () => {
      window.cancelAnimationFrame(animationFrame);
      observer.disconnect();
      window.removeEventListener('resize', syncSideScrollHeight);
      window.removeEventListener('scroll', syncSideScrollHeight);
    };
  }, [detail?.id, isDesigner]);

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

  if (!isDesigner) {
    return (
      <div className="mx-auto w-full max-w-[1720px] px-4 py-7 sm:px-6 lg:px-8 lg:py-9">
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

        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <main className="min-w-0 space-y-6">
            <section className="surface-card overflow-hidden">
              <div className="grid lg:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.65fr)]">
                <div
                  className="flex items-center justify-center overflow-hidden bg-[linear-gradient(135deg,#f1f5f9_25%,transparent_25%),linear-gradient(225deg,#f1f5f9_25%,transparent_25%),linear-gradient(45deg,#f1f5f9_25%,transparent_25%),linear-gradient(315deg,#f1f5f9_25%,#fff_25%)] bg-[length:24px_24px] bg-[position:12px_0,12px_0,0_0,0_0] lg:border-r lg:border-border/70"
                  style={{ height: 'clamp(520px, calc(100vh - 150px), 760px)' }}
                >
                  <img
                    src={mainImageUrl}
                    alt={detail.title}
                    className="max-h-full max-w-full object-contain"
                  />
                </div>

                <ImageDetailInfoPanel
                  detail={detail}
                  embedded
                  isDesigner={false}
                  provider={provider}
                  actions={actions}
                  panelHeight={null}
                  variants={assetGroupQuery.data?.images}
                />
              </div>
            </section>

            <div ref={businessRelatedRef}>
              <BusinessImageDetailRecommendations
                detail={detail}
              />
            </div>
          </main>

          <aside ref={businessSideRef} className="min-w-0 space-y-5 xl:sticky xl:top-6">
            <BusinessImageDetailSideRecommendations
              detail={detail}
              maxHeight={sideRecommendationsMaxHeight}
            />
          </aside>
        </div>

        <ImageDeleteDialog
          title={detail.title}
          open={actions.showDeleteDialog}
          deleting={actions.deleting}
          onOpenChange={actions.setShowDeleteDialog}
          onConfirm={() => actions.remove()}
        />
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

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.55fr)_minmax(340px,0.75fr)]">
        <div
          ref={imageFrameRef}
          className="surface-card flex items-center justify-center overflow-hidden bg-[linear-gradient(135deg,#f1f5f9_25%,transparent_25%),linear-gradient(225deg,#f1f5f9_25%,transparent_25%),linear-gradient(45deg,#f1f5f9_25%,transparent_25%),linear-gradient(315deg,#f1f5f9_25%,#fff_25%)] bg-[length:24px_24px] bg-[position:12px_0,12px_0,0_0,0_0]"
          style={{ aspectRatio: detail.width && detail.height ? `${detail.width} / ${detail.height}` : '4 / 3' }}
        >
          <img
            src={mainImageUrl}
            alt={detail.title}
            className="max-h-full max-w-full object-contain"
          />
        </div>

        <div className="min-h-0">
          <ImageDetailInfoPanel
            detail={detail}
            isDesigner={isDesigner}
            provider={provider}
            actions={actions}
            panelHeight={isDesigner ? infoPanelHeight : null}
            variants={assetGroupQuery.data?.images}
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
