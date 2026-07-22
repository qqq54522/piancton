import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, Download, MessageSquareWarning } from 'lucide-react';
import { motion } from 'framer-motion';
import { useMutation } from '@tanstack/react-query';

import { submitSearchFeedback } from '@client/src/api/image';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { Select } from '@client/src/components/ui/select';
import { variantLabel } from '@client/src/features/assets/assetPresentation';
import { rememberImageHomeScroll } from '@client/src/features/images/searchNavigationState';
import type { AssetImage, ScoredImageMatch, SearchFeedbackType } from '@client/src/types/api';
import { itemVariants } from './constants';
import { resultMatchExplanation } from './searchConceptPresentation';

interface ScoredImageCardProps {
  scored: ScoredImageMatch;
  keyword: string;
  searchLogId?: string | null;
}

function ScoredImageCard({ scored, keyword, searchLogId }: ScoredImageCardProps) {
  const variants = scored.availableVariants.length > 0
    ? scored.availableVariants
    : [fallbackVariant(scored)];
  const [selectedId, setSelectedId] = useState(variants[0].id);
  const [submittedFeedback, setSubmittedFeedback] = useState<SearchFeedbackType | null>(null);
  const selected = variants.find((item) => item.id === selectedId) ?? variants[0];
  const matchedConcepts = scored.matchedQueryConcepts ?? [];
  const primaryConcept = matchedConcepts[0] ?? (
    scored.expressedConcepts[0]
      ? { conceptName: scored.expressedConcepts[0], relationRole: 'expresses' as const }
      : scored.supportedConcepts[0]
        ? { conceptName: scored.supportedConcepts[0], relationRole: 'supports' as const }
        : null
  );
  const feedback = useMutation({
    mutationFn: (feedbackType: 'relevant' | 'not_relevant') => submitSearchFeedback({
      searchLogId,
      keyword,
      feedbackType,
      note: feedbackType === 'relevant'
        ? '单结果反馈：就是这张'
        : '单结果反馈：不相关 / 不是这个意思',
      resultImageId: selected.id,
      assetGroupId: scored.assetGroupId,
    }),
    onSuccess: (_data, feedbackType) => setSubmittedFeedback(feedbackType),
  });

  return (
    <motion.article
      variants={itemVariants}
      className="flex h-full flex-col overflow-hidden rounded-xl border border-border bg-card shadow-sm"
    >
      <Link
        to={`/image/${selected.id}`}
        state={{ from: '/' }}
        onClick={rememberImageHomeScroll}
        className="group relative aspect-[4/3] overflow-hidden bg-muted"
      >
        <img
          src={selected.thumbnailUrl}
          alt={selected.title}
          className="size-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
        />
        {variants.length > 1 && (
          <Badge className="absolute left-2 top-2 bg-black/65 text-white">
            {variants.length} 个尺寸
          </Badge>
        )}
        {primaryConcept && (
          <div
            className="absolute bottom-2 right-2 flex max-w-[calc(100%-1rem)] items-center justify-end gap-1"
            title={matchedConcepts.length > 0
              ? matchedConcepts.map((item) => `${item.conceptName} · ${relationLabel(item.relationRole)}`).join('、')
              : `${primaryConcept.conceptName} · ${relationLabel(primaryConcept.relationRole)}`}
          >
            <Badge className="max-w-[12rem] truncate bg-slate-950/80 text-[10px] text-white backdrop-blur-sm">
              {matchedConcepts.length > 0 ? '匹配' : '主要'}：{primaryConcept.conceptName}
            </Badge>
            {matchedConcepts.length > 1 && (
              <Badge className="bg-primary text-[10px] text-primary-foreground">
                +{matchedConcepts.length - 1}
              </Badge>
            )}
          </div>
        )}
      </Link>

      <div className="flex flex-1 flex-col p-4">
        <h3 className="line-clamp-2 text-sm font-semibold text-foreground">
          {scored.assetTitle || scored.image.title}
        </h3>

        <div className="mt-3 rounded-lg bg-muted/50 px-3 py-2">
          <p className="text-[11px] font-medium text-muted-foreground">为什么匹配</p>
          <p className="mt-1 line-clamp-2 text-xs text-foreground/80">
            {resultMatchExplanation(scored)}
          </p>
        </div>

        <div className="mt-3">
          <label className="text-[11px] font-medium text-muted-foreground" htmlFor={`variant-${scored.assetGroupId || scored.image.id}`}>
            选择尺寸或渠道
          </label>
          <div className="mt-1">
            <Select
              id={`variant-${scored.assetGroupId || scored.image.id}`}
              value={selected.id}
              onChange={(event) => setSelectedId(event.target.value)}
              className="h-9 rounded-md bg-background text-xs"
            >
              {variants.map((variant) => (
                <option key={variant.id} value={variant.id}>{variantLabel(variant)}</option>
              ))}
            </Select>
          </div>
        </div>

        <div className="mt-3">
          <Button asChild size="sm" className="w-full">
            <a href={selected.downloadUrl}>
              <Download className="mr-1.5 size-3.5" />
              下载所选尺寸
            </a>
          </Button>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={feedback.isPending || submittedFeedback !== null}
              onClick={() => feedback.mutate('relevant')}
              title="确认这张素材符合当前搜索需求"
            >
              <CheckCircle2 className="size-3.5" />
              {submittedFeedback === 'relevant' ? '已标记正确' : '就是这张'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={feedback.isPending || submittedFeedback !== null}
              onClick={() => feedback.mutate('not_relevant')}
              title="此反馈只用于优化搜索，不影响素材审批"
            >
              <MessageSquareWarning className="size-3.5" />
              {submittedFeedback === 'not_relevant' ? '已反馈' : '不相关'}
            </Button>
          </div>
        </div>
      </div>
    </motion.article>
  );
}

function relationLabel(role: 'expresses' | 'supports' | 'visual_related'): string {
  return {
    expresses: '主要表达',
    supports: '可以支持',
    visual_related: '画面相关',
  }[role];
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

export default ScoredImageCard;
