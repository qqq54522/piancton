// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import NewUserWelcomeDialog from './NewUserWelcomeDialog';

describe('NewUserWelcomeDialog', () => {
  it('teaches Agent, channel browsing, and a two-step search without a top search box', async () => {
    const onComplete = vi.fn().mockResolvedValue(undefined);
    render(<NewUserWelcomeDialog open onComplete={onComplete} />);

    expect(screen.getByRole('heading', { name: '欢迎来到卖点智库' })).not.toBeNull();
    expect(screen.getByText('先问，再接着聊')).not.toBeNull();
    expect(screen.getByText('找图有两种方式')).not.toBeNull();
    expect(screen.getByText('复杂需求，可以两步问')).not.toBeNull();
    expect(screen.getByText('“洋葱学园的六大体系是什么？”')).not.toBeNull();
    expect(screen.getByText('“同步课和培优课有什么区别？”')).not.toBeNull();
    expect(screen.getByText('“帮我找新疆合作的案例图。”')).not.toBeNull();
    expect(screen.getByText('“帮我找这两个卖点下的图片。”')).not.toBeNull();
    expect(screen.queryByText(/顶部搜索/)).toBeNull();

    expect(screen.queryByRole('button', { name: 'Close' })).toBeNull();
    fireEvent.keyDown(document, { key: 'Escape' });
    fireEvent.pointerDown(document.body);
    expect(onComplete).not.toHaveBeenCalled();
    expect(screen.getByRole('heading', { name: '欢迎来到卖点智库' })).not.toBeNull();

    fireEvent.click(screen.getByRole('button', { name: '我已看完，开始使用' }));
    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));
  });

  it('keeps the guide open and shows a helpful error when completion fails', async () => {
    const onComplete = vi.fn().mockRejectedValue(new Error('offline'));
    render(<NewUserWelcomeDialog open onComplete={onComplete} />);

    fireEvent.click(screen.getByRole('button', { name: '我已看完，开始使用' }));
    expect((await screen.findByRole('alert')).textContent).toBe('暂时无法保存引导状态，请稍后再试。');
  });
});
