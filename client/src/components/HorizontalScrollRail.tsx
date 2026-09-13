import {
  type ComponentPropsWithoutRef,
  type PointerEvent as ReactPointerEvent,
  useEffect,
  useRef,
  useState,
} from 'react';

import { cn } from '@client/src/lib/utils';

type HorizontalScrollRailProps = Omit<
  ComponentPropsWithoutRef<'div'>,
  'onClickCapture' | 'onPointerCancel' | 'onPointerDown' | 'onPointerMove' | 'onPointerUp'
>;

interface DragState {
  active: boolean;
  moved: boolean;
  pointerId: number;
  startScrollLeft: number;
  startX: number;
}

const EMPTY_DRAG: DragState = {
  active: false,
  moved: false,
  pointerId: -1,
  startScrollLeft: 0,
  startX: 0,
};

export default function HorizontalScrollRail({
  children,
  className,
  tabIndex = 0,
  ...props
}: HorizontalScrollRailProps) {
  const railRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<DragState>({ ...EMPTY_DRAG });
  const suppressClickRef = useRef(false);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const rail = railRef.current;
    if (!rail) return undefined;

    const handleWheel = (event: WheelEvent) => {
      if (event.ctrlKey || rail.scrollWidth <= rail.clientWidth) return;

      const rawDelta = Math.abs(event.deltaY) >= Math.abs(event.deltaX)
        ? event.deltaY
        : event.deltaX;
      if (!rawDelta) return;

      const unit = event.deltaMode === WheelEvent.DOM_DELTA_LINE
        ? 16
        : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
          ? rail.clientWidth
          : 1;
      const maxScrollLeft = Math.max(0, rail.scrollWidth - rail.clientWidth);
      const nextScrollLeft = Math.min(
        maxScrollLeft,
        Math.max(0, rail.scrollLeft + rawDelta * unit),
      );

      // 到达横向边界后继续保留页面的正常纵向滚动。
      if (nextScrollLeft === rail.scrollLeft) return;
      event.preventDefault();
      rail.scrollLeft = nextScrollLeft;
    };

    rail.addEventListener('wheel', handleWheel, { passive: false });
    return () => rail.removeEventListener('wheel', handleWheel);
  }, []);

  const finishDrag = (event: ReactPointerEvent<HTMLDivElement>, cancelled = false) => {
    const drag = dragRef.current;
    if (!drag.active || drag.pointerId !== event.pointerId) return;

    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    dragRef.current = { ...EMPTY_DRAG };
    setDragging(false);

    if (!cancelled && drag.moved) {
      suppressClickRef.current = true;
      window.setTimeout(() => {
        suppressClickRef.current = false;
      }, 0);
    }
  };

  return (
    <div
      {...props}
      ref={railRef}
      tabIndex={tabIndex}
      data-dragging={dragging ? 'true' : 'false'}
      className={cn(
        'horizontal-scroll-rail overflow-x-auto overflow-y-hidden overscroll-x-contain',
        dragging ? 'cursor-grabbing select-none' : 'cursor-grab',
        className,
      )}
      onPointerDown={(event) => {
        if (
          event.pointerType !== 'mouse'
          || event.button !== 0
          || event.currentTarget.scrollWidth <= event.currentTarget.clientWidth
        ) return;

        dragRef.current = {
          active: true,
          moved: false,
          pointerId: event.pointerId,
          startScrollLeft: event.currentTarget.scrollLeft,
          startX: event.clientX,
        };
        event.currentTarget.setPointerCapture?.(event.pointerId);
      }}
      onPointerMove={(event) => {
        const drag = dragRef.current;
        if (!drag.active || drag.pointerId !== event.pointerId) return;

        const distance = event.clientX - drag.startX;
        if (!drag.moved && Math.abs(distance) < 4) return;
        if (!drag.moved) {
          drag.moved = true;
          setDragging(true);
        }
        event.preventDefault();
        event.currentTarget.scrollLeft = drag.startScrollLeft - distance;
      }}
      onPointerUp={(event) => finishDrag(event)}
      onPointerCancel={(event) => finishDrag(event, true)}
      onClickCapture={(event) => {
        if (!suppressClickRef.current) return;
        suppressClickRef.current = false;
        event.preventDefault();
        event.stopPropagation();
      }}
    >
      {children}
    </div>
  );
}
