// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import NewUserWelcomeDialog from './NewUserWelcomeDialog';

describe('NewUserWelcomeDialog', () => {
  it('explains the three primary workflows and completes once', async () => {
    const onComplete = vi.fn().mockResolvedValue(undefined);
    render(<NewUserWelcomeDialog open onComplete={onComplete} />);

    expect(screen.getByRole('heading', { name: '欢迎来到卖点智库' })).not.toBeNull();
    expect(screen.getByText('把业务需求变成可用素材')).not.toBeNull();
    expect(screen.getByText('顶部找图，右侧继续问')).not.toBeNull();
    expect(screen.getByText('喜欢随手留，收藏按画板整理')).not.toBeNull();
    expect(screen.getByText(/点击头像中的“提交反馈”/)).not.toBeNull();

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
