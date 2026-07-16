import { describe, expect, it } from 'vitest';

import type { AssetConceptLink, BusinessConcept } from '@client/src/types/api';
import { selectInheritedConcepts } from './conceptPhrasePresentation';

describe('concept phrase presentation', () => {
  it('shows one inherited phrase group when manual and accepted AI links share a concept', () => {
    const concepts = [
      { id: 'sync-school', name: '同步校内' },
    ] as BusinessConcept[];
    const links = [
      {
        id: 'manual-link',
        conceptId: 'sync-school',
        origin: 'manual',
        reviewStatus: 'accepted',
        relationRole: 'expresses',
      },
      {
        id: 'ai-link',
        conceptId: 'sync-school',
        origin: 'ai',
        reviewStatus: 'accepted',
        relationRole: 'expresses',
      },
    ] as AssetConceptLink[];

    expect(selectInheritedConcepts(links, concepts).map((item) => item.id)).toEqual([
      'sync-school',
    ]);
  });
});
