import { AnimatePresence, motion } from 'framer-motion';
import { ImageOff } from 'lucide-react';
import type { ReactNode } from 'react';

import EmptyState from '@client/src/components/EmptyState';
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
  emptyDescription?: string;
  emptyAction?: ReactNode;
  withPresence?: boolean;
}

const ImageGrid = ({ images, emptyText, emptyDescription, emptyAction, withPresence = false }: ImageGridProps) => {
  if (images.length === 0) {
    return (
      <EmptyState
        icon={<ImageOff className="size-5" />}
        title={emptyText}
        description={emptyDescription}
        action={emptyAction}
      />
    );
  }

  const items = images.map((image) => (
    <motion.div
      key={image.id}
      variants={itemVariants}
      layout={withPresence}
      className="h-full"
    >
      <ImageCard image={image} />
    </motion.div>
  ));

  return (
    <motion.div
      className="grid grid-cols-1 items-stretch gap-5 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4"
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
