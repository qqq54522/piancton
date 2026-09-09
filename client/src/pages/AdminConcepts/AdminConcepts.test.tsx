// @vitest-environment jsdom

import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import AdminConcepts from './AdminConcepts';

vi.mock('@client/src/features/assets/useBusinessConcepts', () => ({
  useBusinessConcepts: () => ({
    isLoading: false,
    data: [
      {
        id: 'school-point',
        code: 'school_sync',
        name: '同步校内',
        definition: '同步教材与课程目录。',
        status: 'active',
        systemLinks: [{ systemTagId: 'school', role: 'core' }],
      },
      {
        id: 'exam-point',
        code: 'focused_excellence',
        name: '专项培优',
        definition: '围绕重难点专项突破。',
        status: 'active',
        systemLinks: [{ systemTagId: 'exam', role: 'core' }],
      },
    ],
  }),
}));

vi.mock('@client/src/features/tags/useTags', () => ({
  useTags: () => ({
    isLoading: false,
    data: [
      { id: 'school', name: '同步校内体系', nodeType: 'system', status: 'active', sortOrder: 0 },
      { id: 'exam', name: '同步考点体系', nodeType: 'system', status: 'active', sortOrder: 1 },
    ],
  }),
}));

describe('AdminConcepts', () => {
  it('uses systems on the left and shows selling points for the selected system', () => {
    render(<MemoryRouter><AdminConcepts /></MemoryRouter>);

    expect(screen.getByText('业务体系')).toBeTruthy();
    expect(screen.getByText('同步校内')).toBeTruthy();
    expect(screen.queryByText('专项培优')).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: /同步考点体系/ }));
    expect(screen.getByText('专项培优')).toBeTruthy();
    expect(screen.queryByText('同步校内')).toBeNull();
  });
});
