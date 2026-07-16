import { describe, expect, it } from 'vitest';

import type { AssetConceptLink, BusinessConcept } from '@client/src/types/api';
import { selectInheritedConcepts } from './conceptPhrasePresentation';

describe('concept phrase presentation', () => {
  it('inherits only unique concepts from manually confirmed relationships', () => {
    const concepts = [
      { id: 'sync-school', name: '同步校内' },
      { id: 'ai-only', name: '仅 AI 接受' },
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
      {
        id: 'ai-only-link',
        conceptId: 'ai-only',
        origin: 'ai',
        reviewStatus: 'accepted',
        relationRole: 'supports',
      },
    ] as AssetConceptLink[];

    expect(selectInheritedConcepts(links, concepts).map((item) => item.id)).toEqual([
      'sync-school',
    ]);
  });
});
