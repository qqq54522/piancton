// @vitest-environment jsdom

import type { UseMutationResult } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { SearchFeedbackType } from '@client/src/types/api';
import SearchFeedbackPanel from './SearchFeedbackPanel';

describe('SearchFeedbackPanel', () => {
  it('requires a satisfaction choice and has no dismiss action', () => {
    const mutate = vi.fn();
    const mutation = {
      mutate,
      isPending: false,
      isError: false,
    } as unknown as UseMutationResult<void, Error, SearchFeedbackType>;

    render(
      <SearchFeedbackPanel
        feedbackNote=""
        feedbackMutation={mutation}
        submittedFeedback={null}
        onFeedbackNoteChange={vi.fn()}
      />,
    );

    const submit = screen.getByRole('button', { name: '提交反馈' });
    expect((submit as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryByRole('button', { name: 'Close' })).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: '满意' }));
    expect((submit as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(submit);

    expect(mutate).toHaveBeenCalledWith('relevant');
  });
});
