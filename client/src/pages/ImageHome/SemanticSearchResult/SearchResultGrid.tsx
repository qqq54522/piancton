import { motion } from 'framer-motion';
import { useEffect, useMemo, useRef, useState } from 'react';

import type { ProjectBasketItem } from '@client/src/features/assets/useProjectBasket';
import type { ScoredImageMatch } from '@client/src/types/api';
import ScoredImageCard from './ScoredImageCard';
import { staggerVariants } from './constants';

const RESULT_RENDER_BATCH_SIZE = 24;

interface SearchResultGridProps {
  items: ScoredImageMatch[];
  keyword: string;
  searchLogId?: string | null;
  showSearchContext: boolean;
  animateGifPreview?: boolean;
  isInProjectBasket?: (assetGroupId?: string | null) => boolean;
  onToggleProjectBasket?: (item: ProjectBasketItem) => void;
}

function SearchResultGrid({
  items,
  keyword,
  searchLogId,
  showSearchContext,
  animateGifPreview = true,
  isInProjectBasket,
  onToggleProjectBasket,
}: SearchResultGridProps) {
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const itemSignature = useMemo(
    () => items.map((item) => item.assetGroupId || item.image.id).join('|'),
    [items],
  );
  const [renderState, setRenderState] = useState({
    signature: itemSignature,
    count: RESULT_RENDER_BATCH_SIZE,
  });
  const visibleCount = renderState.signature === itemSignature
    ? renderState.count
    : RESULT_RENDER_BATCH_SIZE;

  useEffect(() => {
    setRenderState((current) => (
      current.signature === itemSignature
        ? current
        : { signature: itemSignature, count: RESULT_RENDER_BATCH_SIZE }
    ));
  }, [itemSignature]);

  useEffect(() => {
    const sentinel = loadMoreRef.current;
    if (!sentinel || visibleCount >= items.length) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setRenderState((current) => {
            const currentCount = current.signature === itemSignature
              ? current.count
              : RESULT_RENDER_BATCH_SIZE;
            return {
              signature: itemSignature,
              count: Math.min(currentCount + RESULT_RENDER_BATCH_SIZE, items.length),
            };
          });
        }
      },
      { rootMargin: '320px' },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [itemSignature, items.length, visibleCount]);

  const visibleItems = items.slice(0, visibleCount);

  return (
    <>
      <motion.div
        className="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4"
        initial="hidden"
        animate="visible"
        variants={staggerVariants}
      >
        {visibleItems.map((scored) => (
          <ScoredImageCard
            key={scored.assetGroupId || scored.image.id}
            scored={scored}
            keyword={keyword}
            searchLogId={searchLogId}
            showSearchContext={showSearchContext}
            animateGifPreview={animateGifPreview}
            inProjectBasket={isInProjectBasket?.(scored.assetGroupId)}
            onToggleProjectBasket={onToggleProjectBasket}
          />
        ))}
      </motion.div>
      {visibleCount < items.length && (
        <div
          ref={loadMoreRef}
          className="flex min-h-16 items-center justify-center text-xs text-muted-foreground"
          aria-label="继续加载搜索结果"
        >
          向下滚动继续查看
        </div>
      )}
    </>
  );
}

export default SearchResultGrid;
