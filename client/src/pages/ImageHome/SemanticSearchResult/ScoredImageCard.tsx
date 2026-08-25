import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { toast } from 'sonner';

import { Select } from '@client/src/components/ui/select';
import { variantLabel } from '@client/src/features/assets/assetPresentation';
import { sendImageToAssetAgent } from '@client/src/features/assets/assetAgentEvents';
import type { ProjectBasketItem } from '@client/src/features/assets/useProjectBasket';
import { previewUrlFor } from '@client/src/features/images/imagePreview';
import { rememberImageHomeScroll } from '@client/src/features/images/searchNavigationState';
import type { AssetImage, ScoredImageMatch } from '@client/src/types/api';
import { itemVariants } from './constants';
import RadialActionMenu from '../RadialActionMenu';
import { resultRecommendationCopy, resultRecommendedPoint } from './searchConceptPresentation';

interface ScoredImageCardProps {
  scored: ScoredImageMatch;
  keyword: string;
  searchLogId?: string | null;
  showSearchContext: boolean;
  inProjectBasket?: boolean;
  animateGifPreview?: boolean;
  onToggleProjectBasket?: (item: ProjectBasketItem) => void;
}

function ScoredImageCard({
  scored,
  keyword: _keyword,
  searchLogId: _searchLogId,
  showSearchContext,
  inProjectBasket = false,
  animateGifPreview = true,
  onToggleProjectBasket,
}: ScoredImageCardProps) {
  const variants = scored.availableVariants.length > 0
    ? scored.availableVariants
    : [fallbackVariant(scored)];
  const [selectedId, setSelectedId] = useState(variants[0].id);
  const selected = variants.find((item) => item.id === selectedId) ?? variants[0];
  const recommendation = resultRecommendationCopy(scored);
  const canSaveToProjectBasket = Boolean(scored.assetGroupId && onToggleProjectBasket);
  const identityCode = selected.versionCode || selected.assetCode || scored.image.versionCode || scored.image.assetCode;
  const copyIdentity = async () => {
    if (!identityCode) return;
    await navigator.clipboard.writeText(identityCode);
    toast.success('身份码已复制');
  };

  return (
    <motion.article
      variants={itemVariants}
      className="group relative mb-4 break-inside-avoid rounded-xl border border-border bg-white shadow-sm transition-[transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:shadow-lg"
    >
      <Link
        to={`/image/${selected.id}`}
        state={{ from: '/' }}
        onClick={rememberImageHomeScroll}
        aria-label={`就是这张：${selected.title}`}
        className="block overflow-hidden bg-muted"
        style={{ aspectRatio: imageAspectRatio(selected) }}
      >
        <img
          src={previewUrlFor(selected, { animateGif: animateGifPreview })}
          alt={selected.title}
          className="size-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
        />
      </Link>

      <RadialActionMenu
        identityCode={identityCode}
        inProjectBasket={inProjectBasket}
        onCopyIdentity={identityCode ? copyIdentity : undefined}
        onSendToAgent={() => {
          sendImageToAssetAgent({
            imageId: selected.id,
            assetGroupId: scored.assetGroupId,
            title: scored.assetTitle || selected.title,
          });
        }}
        onToggleProjectBasket={canSaveToProjectBasket
          ? () => {
            if (!scored.assetGroupId || !onToggleProjectBasket) return;
            onToggleProjectBasket({
              assetGroupId: scored.assetGroupId,
              title: scored.assetTitle || scored.image.title,
              imageId: scored.image.id,
            });
          }
          : undefined}
        downloadHref={selected.downloadUrl}
        downloadLabel={variantLabel(selected)}
        variantSelector={variants.length > 1 ? (
          <Select
            aria-label="选择下载尺寸"
            value={selected.id}
            onChange={(event) => setSelectedId(event.target.value)}
            className="h-8 w-28 rounded-full border-white/70 bg-white/90 px-2 text-[11px] shadow-sm backdrop-blur-md"
          >
            {variants.map((variant) => (
              <option key={variant.id} value={variant.id}>{variantLabel(variant)}</option>
            ))}
          </Select>
        ) : undefined}
      />

      {showSearchContext && (
        <div className="border-t border-border/70 bg-white px-3.5 py-3">
          <p className="break-words text-[11px] font-semibold leading-5 text-muted-foreground">
            推荐点：{resultRecommendedPoint(scored)}
          </p>
          <p className="mt-1 break-words text-xs font-medium leading-5 text-foreground/86">
            {recommendation.primary}
          </p>
          {recommendation.secondary.length > 0 && (
            <div className="mt-2 border-l-2 border-border pl-2">
              <p className="break-words whitespace-pre-wrap text-xs leading-5 text-muted-foreground">
                {recommendation.secondary.join(' ')}
              </p>
            </div>
          )}
        </div>
      )}

      {!showSearchContext && (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/55 to-transparent p-3 opacity-0 transition-opacity group-hover:opacity-100">
          <p className="line-clamp-1 text-sm font-semibold text-white">
            {scored.assetTitle || scored.image.title}
          </p>
        </div>
      )}

    </motion.article>
  );
}

function fallbackVariant(scored: ScoredImageMatch): AssetImage {
  return {
    id: scored.image.id,
    assetCode: scored.image.assetCode,
    versionCode: scored.image.versionCode,
    sharePath: scored.image.sharePath,
    title: scored.image.title,
    fileName: scored.image.fileName,
    thumbnailUrl: scored.image.thumbnailUrl,
    contentUrl: scored.image.contentUrl,
    downloadUrl: scored.image.downloadUrl,
    mediaType: scored.image.mediaType,
    assetRole: scored.image.assetRole,
    width: scored.image.width,
    height: scored.image.height,
    aspectRatio: scored.image.aspectRatio,
    channel: scored.image.channel,
    versionNo: scored.image.versionNo,
    isCurrent: scored.image.isCurrent,
  };
}

function imageAspectRatio(image: AssetImage): string {
  if (image.aspectRatio && image.aspectRatio > 0) return String(image.aspectRatio);
  if (image.width && image.height) return `${image.width} / ${image.height}`;
  return '4 / 3';
}

export default ScoredImageCard;
