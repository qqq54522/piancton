import { useMutation, useQueryClient } from '@tanstack/react-query';

import * as conceptApi from '@client/src/api/businessConcept';
import type { BusinessConcept } from '@client/src/types/api';
import { businessConceptsKey } from './useBusinessConcepts';

export function useBusinessConceptActions() {
  const queryClient = useQueryClient();
  const update = (updated: BusinessConcept) => {
    queryClient.setQueryData<BusinessConcept[]>(businessConceptsKey, (current = []) => (
      current.map((concept) => concept.id === updated.id ? updated : concept)
    ));
  };

  const addPhrase = useMutation({
    mutationFn: ({
      conceptId,
      input,
    }: {
      conceptId: string;
      input: conceptApi.CreateConceptPhraseInput;
    }) => conceptApi.addConceptPhrase(conceptId, input),
    onSuccess: update,
  });

  const updatePhrase = useMutation({
    mutationFn: ({
      conceptId,
      phraseId,
      input,
    }: {
      conceptId: string;
      phraseId: string;
      input: conceptApi.UpdateConceptPhraseInput;
    }) => conceptApi.updateConceptPhrase(conceptId, phraseId, input),
    onSuccess: update,
  });

  return { addPhrase, updatePhrase };
}
