// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import DailyFeedbackDialog, { DAILY_FEEDBACK_FORM_URL } from './DailyFeedbackDialog';

describe('DailyFeedbackDialog', () => {
  it('embeds the daily Feishu form and completes only from the explicit button', async () => {
    const onComplete = vi.fn().mockResolvedValue(undefined);
    render(<DailyFeedbackDialog open onComplete={onComplete} />);

    expect(screen.getByRole('heading', { name: '昨日使用反馈' })).not.toBeNull();
    expect(screen.queryByRole('button', { name: 'Close' })).toBeNull();
    expect(screen.getByTitle('昨日使用反馈表').getAttribute('src')).toBe(
      DAILY_FEEDBACK_FORM_URL,
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.getByRole('heading', { name: '昨日使用反馈' })).not.toBeNull();

    fireEvent.click(screen.getByRole('button', { name: /我已提交/ }));
    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));
  });

  it('keeps the required dialog open when saving fails', async () => {
    render(
      <DailyFeedbackDialog
        open
        onComplete={vi.fn().mockRejectedValue(new Error('offline'))}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /我已提交/ }));
    expect((await screen.findByRole('alert')).textContent).toContain('暂时无法保存完成状态');
    expect(screen.getByRole('heading', { name: '昨日使用反馈' })).not.toBeNull();
  });
});
