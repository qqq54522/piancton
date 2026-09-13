// @vitest-environment jsdom

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import RadialActionMenu from './RadialActionMenu';

describe('RadialActionMenu', () => {
  it('separates likes, boards and multi-select export', () => {
    const toggleLike = vi.fn();
    const addToBoard = vi.fn();
    const toggleExport = vi.fn();

    render(
      <RadialActionMenu
        identityCode="PC-TEST"
        onCopyIdentity={vi.fn()}
        onSendToAgent={vi.fn()}
        onToggleLike={toggleLike}
        onAddToBoard={addToBoard}
        onToggleProjectBasket={toggleExport}
      />,
    );

    expect(
      screen.getByLabelText('图片快捷操作').classList.contains('pointer-events-none'),
    ).toBe(true);
    expect(
      screen.getByRole('button', { name: '加入我的喜欢' }).classList.contains('pointer-events-auto'),
    ).toBe(true);
    expect(
      screen.getByRole('button', { name: '收藏到画板' }).classList.contains('pointer-events-auto'),
    ).toBe(true);
    expect(
      screen.getByRole('button', { name: '加入多选导出' }).classList.contains('pointer-events-auto'),
    ).toBe(true);

    fireEvent.click(screen.getByRole('button', { name: '加入我的喜欢' }));
    fireEvent.click(screen.getByRole('button', { name: '收藏到画板' }));
    fireEvent.click(screen.getByRole('button', { name: '加入多选导出' }));

    expect(toggleLike).toHaveBeenCalledOnce();
    expect(addToBoard).toHaveBeenCalledOnce();
    expect(toggleExport).toHaveBeenCalledOnce();
    expect(screen.queryByText('加入项目夹')).toBeNull();
  });
});
