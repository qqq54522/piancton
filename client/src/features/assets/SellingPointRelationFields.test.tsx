import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { BusinessConcept } from '@client/src/types/api';
import { SellingPointRelationFields } from './SellingPointRelationFields';

const concepts = [
  { id: 'one', code: 'one', name: '动画精讲' },
  { id: 'two', code: 'two', name: '举一反三' },
  { id: 'three', code: 'three', name: '督学伴学' },
] as BusinessConcept[];

describe('SellingPointRelationFields', () => {
  it('supports one primary concept and several supporting concepts', () => {
    const onPrimaryConceptChange = vi.fn();
    const onSupportConceptIdsChange = vi.fn();
    render(
      <SellingPointRelationFields
        concepts={concepts}
        primaryConceptId="one"
        supportConceptIds={['two']}
        onPrimaryConceptChange={onPrimaryConceptChange}
        onSupportConceptIdsChange={onSupportConceptIdsChange}
      />,
    );

    expect(screen.queryByRole('button', { name: '动画精讲' })).toBeNull();
    expect(screen.getByRole('button', { name: '举一反三' }).getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(screen.getByRole('button', { name: '督学伴学' }));
    expect(onSupportConceptIdsChange).toHaveBeenCalledWith(['two', 'three']);

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'two' } });
    expect(onPrimaryConceptChange).toHaveBeenCalledWith('two');
    expect(onSupportConceptIdsChange).toHaveBeenCalledWith([]);
  });
});
// @vitest-environment jsdom
