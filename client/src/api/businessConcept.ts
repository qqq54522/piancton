import { api } from './client';

import type {
  BusinessConcept,
  ConceptPhraseType,
  ConceptSearchPhrase,
} from '@client/src/types/api';

export interface CreateConceptPhraseInput {
  phrase: string;
  phraseType?: ConceptPhraseType;
  origin?: ConceptSearchPhrase['origin'];
  reviewStatus?: ConceptSearchPhrase['reviewStatus'];
  weight?: number;
  sourceRef?: string;
}

export interface UpdateConceptPhraseInput {
  phrase?: string;
  phraseType?: ConceptPhraseType;
  reviewStatus?: ConceptSearchPhrase['reviewStatus'];
  weight?: number;
  sourceRef?: string | null;
}

export async function addConceptPhrase(
  conceptId: string,
  input: CreateConceptPhraseInput,
): Promise<BusinessConcept> {
  return (await api.post(`/api/business-concepts/${conceptId}/search-phrases`, input)).data;
}

export async function updateConceptPhrase(
  conceptId: string,
  phraseId: string,
  input: UpdateConceptPhraseInput,
): Promise<BusinessConcept> {
  return (await api.patch(
    `/api/business-concepts/${conceptId}/search-phrases/${phraseId}`,
    input,
  )).data;
}
