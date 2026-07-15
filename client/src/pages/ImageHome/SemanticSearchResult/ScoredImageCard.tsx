import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, Download, MessageSquareWarning } from 'lucide-react';
import { motion } from 'framer-motion';
import { useMutation } from '@tanstack/react-query';

import { submitSearchFeedback } from '@client/src/api/image';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import { variantLabel } from '@client/src/features/assets/assetPresentation';
import type { AssetImage, ScoredImageMatch } from '@client/src/types/api';
import { itemVariants } from './constants';

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
  const selected = variants.find((item) => item.id === selectedId) ?? variants[0];
  const concepts = useMemo(
    () => [
      ...scored.expressedConcepts.map((name) => ({ name, role: '主要表达' })),
      ...scored.supportedConcepts.map((name) => ({ name, role: '可以支持' })),
    ].slice(0, 4),
    [scored.expressedConcepts, scored.supportedConcepts],
  );
  const feedback = useMutation({
    mutationFn: () => submitSearchFeedback({
      searchLogId,
      keyword,
      feedbackType: 'not_relevant',
      note: '单结果反馈：不相关 / 不是这个意思',
      resultImageId: selected.id,
      assetGroupId: scored.assetGroupId,
    }),
  });

  return (
    <motion.article
      variants={itemVariants}
      className="flex h-full flex-col overflow-hidden rounded-xl border border-border bg-card shadow-sm"
    >
      <Link to={`/image/${selected.id}`} className="group relative aspect-[4/3] overflow-hidden bg-muted">
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
      </Link>

      <div className="flex flex-1 flex-col p-4">
        <h3 className="line-clamp-2 text-sm font-semibold text-foreground">
          {scored.assetTitle || scored.image.title}
        </h3>

        {concepts.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {concepts.map((concept) => (
              <Badge
                key={`${concept.role}-${concept.name}`}
                variant={concept.role === '主要表达' ? 'default' : 'outline'}
                className="text-[10px]"
              >
                {concept.name} · {concept.role}
              </Badge>
            ))}
          </div>
        )}

        <div className="mt-3 rounded-lg bg-muted/50 px-3 py-2">
          <p className="text-[11px] font-medium text-muted-foreground">为什么匹配</p>
          <p className="mt-1 line-clamp-2 text-xs text-foreground/80">
            {scored.matchReasons.slice(0, 2).join('；') || '与搜索内容相关'}
          </p>
        </div>

        <div className="mt-3">
          <label className="text-[11px] font-medium text-muted-foreground" htmlFor={`variant-${scored.assetGroupId || scored.image.id}`}>
            选择尺寸或渠道
          </label>
          <select
            id={`variant-${scored.assetGroupId || scored.image.id}`}
            value={selected.id}
            onChange={(event) => setSelectedId(event.target.value)}
            className="mt-1 h-9 w-full rounded-md border border-input bg-background px-2 text-xs"
          >
            {variants.map((variant) => (
              <option key={variant.id} value={variant.id}>{variantLabel(variant)}</option>
            ))}
          </select>
        </div>

        <div className="mt-3 flex gap-2">
          <Button asChild size="sm" className="flex-1">
            <a href={selected.downloadUrl}>
              <Download className="mr-1.5 size-3.5" />
              下载所选尺寸
            </a>
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={feedback.isPending || feedback.isSuccess}
            onClick={() => feedback.mutate()}
            title="此反馈只用于优化搜索，不影响素材审批"
          >
            {feedback.isSuccess ? <Check className="size-3.5" /> : <MessageSquareWarning className="size-3.5" />}
            <span className="ml-1">{feedback.isSuccess ? '已反馈' : '不相关'}</span>
          </Button>
        </div>
      </div>
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

export default ScoredImageCard;
