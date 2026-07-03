import { Badge } from '@client/src/components/ui/badge';
import { motion } from 'framer-motion';
import type { ScoredImageMatch } from '@client/src/types/api';
import ImageCard from '../ImageCard';
import { itemVariants, MATCH_LEVEL_CONFIG } from './constants';

function ScoredImageCard({ scored }: { scored: ScoredImageMatch }) {
  const config = MATCH_LEVEL_CONFIG[scored.matchLevel];
  const LevelIcon = config.icon;

  const overlay = (
    <div className="absolute left-2 top-2 flex items-center gap-1">
      <Badge className={`${config.color} text-[10px] font-medium shadow-sm`}>
        <LevelIcon className="mr-0.5 size-3" />
        {scored.matchLevel} {config.label}
      </Badge>
    </div>
  );

  return (
    <motion.div variants={itemVariants} className="h-full">
      <ImageCard image={scored.image} overlay={overlay} />
    </motion.div>
  );
}

export default ScoredImageCard;
