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

  const updateConcept = useMutation({
    mutationFn: ({
      conceptId,
      input,
    }: {
      conceptId: string;
      input: conceptApi.UpdateBusinessConceptInput;
    }) => conceptApi.updateBusinessConcept(conceptId, input),
    onSuccess: update,
  });

  return { updateConcept };
}
