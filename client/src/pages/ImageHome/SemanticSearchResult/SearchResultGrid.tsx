import { motion } from 'framer-motion';

import type { ScoredImageMatch } from '@client/src/types/api';
import ScoredImageCard from './ScoredImageCard';
import { staggerVariants } from './constants';

interface SearchResultGridProps {
  items: ScoredImageMatch[];
  keyword: string;
  searchLogId?: string | null;
}

function SearchResultGrid({ items, keyword, searchLogId }: SearchResultGridProps) {
  return (
    <motion.div
      className="grid grid-cols-1 items-stretch gap-4 sm:grid-cols-2 lg:grid-cols-3"
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
        />
      ))}
    </motion.div>
  );
}

export default SearchResultGrid;
