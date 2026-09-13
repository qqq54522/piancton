// @vitest-environment jsdom

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import UnreadAnnouncementBadge from './UnreadAnnouncementBadge';

describe('UnreadAnnouncementBadge', () => {
  it('hides zero and renders unread counts including the upper cap', () => {
    const view = render(<UnreadAnnouncementBadge count={0} />);
    expect(screen.queryByLabelText('0 条未读消息')).toBeNull();

    view.rerender(<UnreadAnnouncementBadge count={2} />);
    expect(screen.getByLabelText('2 条未读消息').textContent).toBe('2');

    view.rerender(<UnreadAnnouncementBadge count={120} />);
    expect(screen.getByLabelText('120 条未读消息').textContent).toBe('99+');
  });
});
