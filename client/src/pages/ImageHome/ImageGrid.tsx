import { AnimatePresence, motion } from 'framer-motion';
import { ImageOff } from 'lucide-react';

import type { ImageItem } from '@client/src/types/api';
import ImageCard from './ImageCard';

const staggerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

interface ImageGridProps {
  images: ImageItem[];
  emptyText: string;
  withPresence?: boolean;
}

const ImageGrid = ({ images, emptyText, withPresence = false }: ImageGridProps) => {
  if (images.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <ImageOff className="size-12 text-muted-foreground/50" />
        <p className="mt-3 text-sm text-muted-foreground">{emptyText}</p>
      </div>
    );
  }

  const items = images.map((image) => (
    <motion.div
      key={image.id}
      variants={itemVariants}
      layout={withPresence}
    >
      <ImageCard image={image} />
    </motion.div>
  ));

  return (
    <motion.div
      className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4"
      initial="hidden"
      animate="visible"
      variants={staggerVariants}
    >
      {withPresence ? <AnimatePresence>{items}</AnimatePresence> : items}
    </motion.div>
  );
};

export { itemVariants, staggerVariants };
export default ImageGrid;
