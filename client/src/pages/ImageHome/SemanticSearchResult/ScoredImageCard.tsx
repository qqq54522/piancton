import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Download } from 'lucide-react';
import { motion } from 'framer-motion';

import { Select } from '@client/src/components/ui/select';
import { variantLabel } from '@client/src/features/assets/assetPresentation';
import { rememberImageHomeScroll } from '@client/src/features/images/searchNavigationState';
import type { AssetImage, ScoredImageMatch } from '@client/src/types/api';
import { itemVariants } from './constants';
import { resultRecommendationCopy, resultRecommendedPoint } from './searchConceptPresentation';

interface ScoredImageCardProps {
  scored: ScoredImageMatch;
  keyword: string;
  searchLogId?: string | null;
  showSearchContext: boolean;
}

function ScoredImageCard({
  scored,
  keyword: _keyword,
  searchLogId: _searchLogId,
  showSearchContext,
}: ScoredImageCardProps) {
  const variants = scored.availableVariants.length > 0
    ? scored.availableVariants
    : [fallbackVariant(scored)];
  const [selectedId, setSelectedId] = useState(variants[0].id);
  const selected = variants.find((item) => item.id === selectedId) ?? variants[0];
  const recommendation = resultRecommendationCopy(scored);

  return (
    <motion.article
      variants={itemVariants}
      className="group relative mb-4 break-inside-avoid overflow-hidden rounded-xl border border-border bg-white shadow-sm transition-shadow hover:shadow-lg"
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
          src={selected.thumbnailUrl}
          alt={selected.title}
          className="size-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
        />
      </Link>

      <div className="absolute right-2 top-2 z-20 flex items-center gap-1.5">
        {variants.length > 1 && (
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
        )}
        <a
          href={selected.downloadUrl}
          aria-label="下载所选尺寸"
          title={variantLabel(selected)}
          className="inline-flex size-8 items-center justify-center rounded-full bg-white/90 text-foreground shadow-sm backdrop-blur-md transition-colors hover:bg-foreground hover:text-background"
        >
          <Download className="size-4" />
        </a>
      </div>

      {showSearchContext && (
        <div className="border-t border-border/70 bg-white px-3.5 py-3">
          <p className="text-[11px] font-semibold text-muted-foreground">
            推荐点：{resultRecommendedPoint(scored)}
          </p>
          <p className="mt-1 line-clamp-2 text-xs font-medium leading-5 text-foreground/86">
            {recommendation.primary}
          </p>
          {recommendation.secondary.length > 0 && (
            <div className="mt-2 border-l-2 border-border pl-2">
              <p className="line-clamp-2 text-xs leading-5 text-muted-foreground">
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
    title: scored.image.title,
    fileName: scored.image.fileName,
    thumbnailUrl: scored.image.thumbnailUrl,
    contentUrl: scored.image.contentUrl,
    downloadUrl: scored.image.downloadUrl,
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
