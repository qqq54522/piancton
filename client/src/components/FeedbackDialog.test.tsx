// @vitest-environment jsdom

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import FeedbackDialog, { PROJECT_FEEDBACK_FORM_URL } from './FeedbackDialog';

describe('FeedbackDialog', () => {
  it('keeps the Feishu feedback form inside the current page', () => {
    render(<FeedbackDialog open onOpenChange={vi.fn()} />);

    expect(screen.getByRole('heading', { name: '提交反馈' })).not.toBeNull();
    const frame = screen.getByTitle('项目反馈表');
    expect(frame.getAttribute('src')).toBe(PROJECT_FEEDBACK_FORM_URL);
    expect(screen.queryByRole('link')).toBeNull();
  });
});
