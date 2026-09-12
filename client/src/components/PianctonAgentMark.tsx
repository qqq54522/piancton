import { useEffect, useRef, useState } from 'react';

import { cn } from '@client/src/lib/utils';

type AgentMarkSize = 'sm' | 'md' | 'lg';
type AgentMarkState = 'idle' | 'thinking' | 'happy' | 'wake';
type AgentMarkVariant = 'orb' | 'flat';

const sizeClass: Record<AgentMarkSize, string> = {
  sm: 'size-10',
  md: 'size-12',
  lg: 'size-14',
};

export function PianctonAgentMark({
  size = 'md',
  state = 'idle',
  variant = 'orb',
  interactive = true,
  className,
}: {
  size?: AgentMarkSize;
  state?: AgentMarkState;
  variant?: AgentMarkVariant;
  interactive?: boolean;
  className?: string;
}) {
  const markRef = useRef<HTMLSpanElement | null>(null);
  const [gaze, setGaze] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (!interactive) {
      setGaze({ x: 0, y: 0 });
      return undefined;
    }
    const mark = markRef.current;
    if (!mark || typeof window === 'undefined') return undefined;

    let frame = 0;
    let nextGaze = { x: 0, y: 0 };
    let currentGaze = { x: 0, y: 0 };

    const updateTarget = (event: PointerEvent) => {
      const rect = mark.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const radiusX = Math.max(rect.width * 1.8, 1);
      const radiusY = Math.max(rect.height * 1.8, 1);
      nextGaze = {
        x: Math.max(-1, Math.min(1, (event.clientX - centerX) / radiusX)),
        y: Math.max(-1, Math.min(1, (event.clientY - centerY) / radiusY)),
      };
    };

    const resetTarget = () => {
      nextGaze = { x: 0, y: 0 };
    };

    const animate = () => {
      currentGaze = {
        x: currentGaze.x + (nextGaze.x - currentGaze.x) * 0.14,
        y: currentGaze.y + (nextGaze.y - currentGaze.y) * 0.14,
      };
      setGaze(currentGaze);
      frame = window.requestAnimationFrame(animate);
    };

    window.addEventListener('pointermove', updateTarget, { passive: true });
    window.addEventListener('blur', resetTarget);
    frame = window.requestAnimationFrame(animate);
    return () => {
      window.removeEventListener('pointermove', updateTarget);
      window.removeEventListener('blur', resetTarget);
      window.cancelAnimationFrame(frame);
    };
  }, [interactive]);

  return (
    <span
      ref={markRef}
      className={cn(
        variant === 'flat' ? 'agent-flat-mark' : 'agent-orb',
        sizeClass[size],
        className,
      )}
      data-state={state}
      style={{
        '--agent-gaze-x': `${gaze.x * 3.5}px`,
        '--agent-gaze-y': `${gaze.y * 2.5}px`,
        '--agent-face-rotate': `${gaze.x * 3.5}deg`,
        '--agent-orb-shift-x': `${gaze.x * 1.5}px`,
        '--agent-orb-shift-y': `${gaze.y * 1}px`,
        '--agent-orb-rotate': `${gaze.x * 2.5}deg`,
        '--agent-orb-scale-x': `${1 + Math.abs(gaze.x) * 0.035}`,
        '--agent-orb-scale-y': `${1 - Math.abs(gaze.x) * 0.02}`,
      } as React.CSSProperties}
      aria-hidden="true"
    >
      <span className="agent-orb-rainbow" />
      <span className="agent-orb-face">
        <span className="agent-orb-eye">
          <span className="agent-orb-pupil" />
        </span>
        <span className="agent-orb-eye">
          <span className="agent-orb-pupil" />
        </span>
        <span className="agent-orb-mouth" />
      </span>
    </span>
  );
}
