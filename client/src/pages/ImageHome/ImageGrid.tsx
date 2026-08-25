import { AnimatePresence, motion } from 'framer-motion';
import { ImageOff } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';

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
  emptyVariant?: 'card' | 'plain';
  layout?: 'grid' | 'masonry';
  withPresence?: boolean;
  animateGifPreview?: boolean;
}

const ImageGrid = ({
  images,
  emptyText,
  emptyDescription,
  emptyAction,
  emptyVariant = 'card',
  layout = 'grid',
  withPresence = false,
  animateGifPreview = true,
}: ImageGridProps) => {
  const [layoutRevision, setLayoutRevision] = useState(0);
  const imageSignature = useMemo(
    () => images.map((image) => image.id).join('|'),
    [images],
  );
  const refreshLayout = useCallback(() => {
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        void document.documentElement.offsetHeight;
        window.dispatchEvent(new Event('resize'));
      });
    });
  }, []);

  useEffect(() => {
    if (layout !== 'masonry') return;
    refreshLayout();
  }, [imageSignature, layout, refreshLayout]);

  useEffect(() => {
    if (layout !== 'masonry') return;
    const refreshAfterNavigationRestore = (event?: PageTransitionEvent) => {
      if (event && !event.persisted) return;
      setLayoutRevision((current) => current + 1);
      refreshLayout();
    };
    const refreshAfterVisibilityRestore = () => {
      if (document.visibilityState === 'visible') refreshLayout();
    };
    window.addEventListener('pageshow', refreshAfterNavigationRestore);
    document.addEventListener('visibilitychange', refreshAfterVisibilityRestore);
    return () => {
      window.removeEventListener('pageshow', refreshAfterNavigationRestore);
      document.removeEventListener('visibilitychange', refreshAfterVisibilityRestore);
    };
  }, [layout, refreshLayout]);

  if (images.length === 0) {
    if (emptyVariant === 'plain') {
      return (
        <div className="flex min-h-[320px] items-center justify-center">
          <p className="text-sm font-medium text-muted-foreground">{emptyText}</p>
        </div>
      );
    }
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
      className={layout === 'masonry' ? 'mb-5 break-inside-avoid' : 'h-full'}
    >
      <ImageCard
        image={image}
        variant={layout}
        animateGifPreview={animateGifPreview}
        onImageLoad={layout === 'masonry' ? refreshLayout : undefined}
      />
    </motion.div>
  ));

  if (layout === 'masonry') {
    return (
      <motion.div
        key={`masonry-${layoutRevision}`}
        className="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4 2xl:columns-5 min-[1800px]:columns-6"
        initial="hidden"
        animate="visible"
        variants={staggerVariants}
      >
        {withPresence ? <AnimatePresence>{items}</AnimatePresence> : items}
      </motion.div>
    );
  }

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
