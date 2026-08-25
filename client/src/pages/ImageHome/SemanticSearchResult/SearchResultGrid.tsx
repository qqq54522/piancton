import { motion } from 'framer-motion';

import type { ProjectBasketItem } from '@client/src/features/assets/useProjectBasket';
import type { ScoredImageMatch } from '@client/src/types/api';
import ScoredImageCard from './ScoredImageCard';
import { staggerVariants } from './constants';

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
  return (
    <motion.div
      className="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4"
      initial="hidden"
      animate="visible"
      variants={staggerVariants}
    >
      {items.map((scored) => (
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
  );
}

export default SearchResultGrid;
