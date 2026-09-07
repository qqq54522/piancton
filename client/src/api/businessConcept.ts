import { api } from './client';

import type { BusinessConcept } from '@client/src/types/api';

export interface UpdateBusinessConceptInput {
  name?: string;
  conceptType?: string;
  definition?: string | null;
  recommendationText?: string | null;
  status?: 'draft' | 'active' | 'deprecated' | 'merged';
  replacedByConceptId?: string | null;
}

export async function updateBusinessConcept(
  conceptId: string,
  input: UpdateBusinessConceptInput,
): Promise<BusinessConcept> {
  return (await api.patch(`/api/business-concepts/${conceptId}`, input)).data;
}
