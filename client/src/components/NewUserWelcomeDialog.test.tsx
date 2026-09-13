// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import NewUserWelcomeDialog from './NewUserWelcomeDialog';

describe('NewUserWelcomeDialog', () => {
  it('explains the three primary workflows and completes once', async () => {
    const onComplete = vi.fn().mockResolvedValue(undefined);
    render(<NewUserWelcomeDialog open onComplete={onComplete} />);

    expect(screen.getByRole('heading', { name: '欢迎来到卖点智库' })).not.toBeNull();
    expect(screen.getByText('把业务需求变成可用的卖点图')).not.toBeNull();
    expect(screen.getByText('顶部直接找图，右侧深入理解')).not.toBeNull();
    expect(screen.getByText('喜欢随手留，收藏按画板整理')).not.toBeNull();
    expect(screen.getByText(/不熟悉这些体系和卖点也没关系/)).not.toBeNull();
    expect(screen.getByText('目标明确：顶部搜索')).not.toBeNull();
    expect(screen.getByText('需要理解或追问：Agent')).not.toBeNull();
    expect(screen.getByText(/点击头像里的“提交反馈”/)).not.toBeNull();

    fireEvent.click(screen.getByRole('button', { name: '知道了，开始使用' }));
    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));
  });

  it('keeps the guide open and shows a helpful error when completion fails', async () => {
    const onComplete = vi.fn().mockRejectedValue(new Error('offline'));
    render(<NewUserWelcomeDialog open onComplete={onComplete} />);

    fireEvent.click(screen.getByRole('button', { name: '知道了，开始使用' }));
    expect((await screen.findByRole('alert')).textContent).toBe('暂时无法保存引导状态，请稍后再试。');
  });
});
