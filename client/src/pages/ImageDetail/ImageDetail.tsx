import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';

import { Button } from '@client/src/components/ui/button';
import { ROLE_SUBJECT, useAuth } from '@client/src/lib/auth';
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
  const [showOriginalImage, setShowOriginalImage] = useState(false);
  const canDesign = useAuth();
  const isDesigner = !canDesign.isLoading && canDesign.ability.can('designer', ROLE_SUBJECT);
  const actions = useImageDetailActions(detail);
  const isTallImage = Boolean(
    detail?.width && detail.height && detail.height / detail.width > 1.65,
  );
  const mainImageUrl = useImageUrl(
    isTallImage && !showOriginalImage
      ? detail?.thumbnailUrl ?? detail?.contentUrl ?? ''
      : detail?.contentUrl ?? '',
  );
  const useScrollableTallPreview = isTallImage;
  const previewBackgroundClassName = 'bg-[linear-gradient(135deg,#f1f5f9_25%,transparent_25%),linear-gradient(225deg,#f1f5f9_25%,transparent_25%),linear-gradient(45deg,#f1f5f9_25%,transparent_25%),linear-gradient(315deg,#f1f5f9_25%,#fff_25%)] bg-[length:24px_24px] bg-[position:12px_0,12px_0,0_0,0_0]';
  const previewFrameModeClassName = useScrollableTallPreview
    ? 'overflow-y-auto overflow-x-hidden overscroll-contain p-4 sm:p-5'
    : 'flex items-center justify-center overflow-hidden';
  const previewImageClassName = useScrollableTallPreview
    ? 'mx-auto h-auto w-full max-w-full'
    : 'max-h-full max-w-full object-contain';
  const imageFrameRef = useRef<HTMLDivElement | null>(null);
  const businessRelatedRef = useRef<HTMLDivElement | null>(null);
  const businessSideRef = useRef<HTMLElement | null>(null);
  const [infoPanelHeight, setInfoPanelHeight] = useState<number | null>(null);
  const [sideRecommendationsMaxHeight, setSideRecommendationsMaxHeight] = useState<number | null>(null);

  useEffect(() => {
    setShowOriginalImage(false);
  }, [detail?.id]);

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
                  className={`relative ${previewBackgroundClassName} ${previewFrameModeClassName} lg:border-r lg:border-border/70`}
                  style={{ height: 'clamp(520px, calc(100vh - 150px), 760px)' }}
                >
                  <LongImageLoadControl
                    active={useScrollableTallPreview}
                    showingOriginal={showOriginalImage}
                    onShowOriginal={() => setShowOriginalImage(true)}
                  />
                  <img
                    src={mainImageUrl}
                    alt={detail.title}
                    className={previewImageClassName}
                  />
                </div>

                <ImageDetailInfoPanel
                  detail={detail}
                  embedded
                  isDesigner={false}
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
          className={`surface-card relative ${previewBackgroundClassName} ${previewFrameModeClassName}`}
          style={useScrollableTallPreview ? { height: 'clamp(560px, calc(100vh - 148px), 820px)' } : { aspectRatio: detail.width && detail.height ? `${detail.width} / ${detail.height}` : '4 / 3' }}
        >
          <LongImageLoadControl
            active={useScrollableTallPreview}
            showingOriginal={showOriginalImage}
            onShowOriginal={() => setShowOriginalImage(true)}
          />
          <img
            src={mainImageUrl}
            alt={detail.title}
            className={previewImageClassName}
          />
        </div>

        <div className="min-h-0">
          <ImageDetailInfoPanel
            detail={detail}
            isDesigner={isDesigner}
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
          currentImageId={detail.id}
          editable={isDesigner}
          onImageSelected={(imageId) => navigate(`/image/${imageId}`, { replace: true })}
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

interface LongImageLoadControlProps {
  active: boolean;
  showingOriginal: boolean;
  onShowOriginal: () => void;
}

function LongImageLoadControl({
  active,
  showingOriginal,
  onShowOriginal,
}: LongImageLoadControlProps) {
  if (!active) return null;

  return (
    <div className="absolute right-3 top-3 z-10 flex max-w-[calc(100%-1.5rem)] flex-wrap items-center gap-2 rounded-full border border-border/70 bg-white/95 px-3 py-2 text-xs text-muted-foreground shadow-sm backdrop-blur">
      <span>{showingOriginal ? '正在显示原图' : '预览图加载更快'}</span>
      {!showingOriginal && (
        <button
          type="button"
          onClick={onShowOriginal}
          className="rounded-full bg-foreground px-2.5 py-1 text-xs font-semibold text-background transition hover:bg-foreground/90"
        >
          查看原图
        </button>
      )}
    </div>
  );
}

export default ImageDetail;
