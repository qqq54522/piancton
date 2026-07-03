import { motion } from 'framer-motion';
import type { ScoredImageMatch } from '@client/src/types/api';
import ScoredImageCard from './ScoredImageCard';
import { staggerVariants } from './constants';

function SearchResultGrid({ items }: { items: ScoredImageMatch[] }) {
  return (
    <motion.div
      className="grid grid-cols-2 items-stretch gap-4 sm:grid-cols-3 lg:grid-cols-4"
      initial="hidden"
      animate="visible"
      variants={staggerVariants}
    >
      {items.map((scored) => (
        <ScoredImageCard key={scored.image.id} scored={scored} />
      ))}
    </motion.div>
  );
}

export default SearchResultGrid;
