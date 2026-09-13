// @vitest-environment jsdom

import { fireEvent, render, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import HorizontalScrollRail from './HorizontalScrollRail';

function renderRail() {
  const view = render(
    <HorizontalScrollRail aria-label="渠道选择">
      <button type="button">渠道一</button>
      <button type="button">渠道二</button>
    </HorizontalScrollRail>,
  );
  const rail = within(view.container).getByLabelText('渠道选择');
  Object.defineProperties(rail, {
    clientWidth: { configurable: true, value: 200 },
    scrollWidth: { configurable: true, value: 600 },
  });
  const setPointerCapture = vi.fn();
  const releasePointerCapture = vi.fn();
  Object.defineProperties(rail, {
    hasPointerCapture: { configurable: true, value: vi.fn(() => true) },
    releasePointerCapture: { configurable: true, value: releasePointerCapture },
    setPointerCapture: { configurable: true, value: setPointerCapture },
  });
  return { rail, releasePointerCapture, setPointerCapture, view };
}

describe('HorizontalScrollRail', () => {
  it('turns the mouse wheel into horizontal scrolling while movement is available', () => {
    const { rail } = renderRail();

    const movingWheel = new WheelEvent('wheel', { cancelable: true, deltaY: 80 });
    expect(rail.dispatchEvent(movingWheel)).toBe(false);

    expect(rail.scrollLeft).toBe(80);

    rail.scrollLeft = 400;
    const boundaryWheel = new WheelEvent('wheel', { cancelable: true, deltaY: 80 });
    expect(rail.dispatchEvent(boundaryWheel)).toBe(true);
    expect(rail.scrollLeft).toBe(400);
  });

  it('supports mouse drag without activating a channel button', () => {
    vi.useFakeTimers();
    const { rail, releasePointerCapture, setPointerCapture } = renderRail();
    const firstChannel = within(rail).getByRole('button', { name: '渠道一' });
    const onClick = vi.fn();
    firstChannel.addEventListener('click', onClick);

    fireEvent.pointerDown(rail, {
      button: 0,
      clientX: 180,
      pointerId: 1,
      pointerType: 'mouse',
    });
    fireEvent.pointerMove(rail, {
      clientX: 100,
      pointerId: 1,
      pointerType: 'mouse',
    });
    expect(setPointerCapture).toHaveBeenCalledWith(1);
    fireEvent.pointerUp(rail, { pointerId: 1, pointerType: 'mouse' });
    fireEvent.click(firstChannel);

    expect(rail.scrollLeft).toBe(80);
    expect(onClick).not.toHaveBeenCalled();
    expect(releasePointerCapture).toHaveBeenCalledWith(1);
    vi.runAllTimers();
    vi.useRealTimers();
  });

  it('keeps a normal channel click available when the user does not drag', () => {
    const { rail, setPointerCapture } = renderRail();
    const firstChannel = within(rail).getByRole('button', { name: '渠道一' });
    const onClick = vi.fn();
    firstChannel.addEventListener('click', onClick);

    fireEvent.pointerDown(firstChannel, {
      button: 0,
      clientX: 100,
      pointerId: 1,
      pointerType: 'mouse',
    });
    fireEvent.pointerUp(firstChannel, { pointerId: 1, pointerType: 'mouse' });
    fireEvent.click(firstChannel);

    expect(setPointerCapture).not.toHaveBeenCalled();
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
