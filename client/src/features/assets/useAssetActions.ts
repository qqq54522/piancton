import { useMutation, useQueryClient } from '@tanstack/react-query';

import * as assetApi from '@client/src/api/asset';
import type { AssetGroup } from '@client/src/types/api';
import { assetGroupKey } from './useAssetGroup';

export function useAssetActions(groupId: string) {
  const queryClient = useQueryClient();
  const update = async (group: AssetGroup) => {
    queryClient.setQueryData(assetGroupKey(groupId), group);
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['images'] }),
      queryClient.invalidateQueries({ queryKey: ['image-detail'] }),
    ]);
  };

  const addVariant = useMutation({
    mutationFn: (input: Parameters<typeof assetApi.addAssetVariant>[1]) => (
      assetApi.addAssetVariant(groupId, input)
    ),
    onSuccess: update,
  });
  const replacePrimary = useMutation({
    mutationFn: (input: Parameters<typeof assetApi.replaceAssetPrimary>[1]) => (
      assetApi.replaceAssetPrimary(groupId, input)
    ),
    onSuccess: update,
  });
  const deleteVariant = useMutation({
    mutationFn: (imageId: string) => assetApi.deleteAssetVariant(groupId, imageId),
    onSuccess: update,
  });
  const confirmConcept = useMutation({
    mutationFn: (input: {
      conceptId: string;
      relationRole: assetApi.AssetRelationRole;
    }) => assetApi.confirmAssetConcept(groupId, input.conceptId, input.relationRole),
    onSuccess: update,
  });
  const reviewConcept = useMutation({
    mutationFn: (input: {
      linkId: string;
      reviewStatus: 'accepted' | 'rejected';
      relationRole?: assetApi.AssetRelationRole;
    }) => assetApi.reviewAssetConcept(
      groupId,
      input.linkId,
      input.reviewStatus,
      input.relationRole,
    ),
    onSuccess: update,
  });
  const reviewConcepts = useMutation({
    mutationFn: (input: {
      linkIds: string[];
      reviewStatus: 'accepted' | 'rejected';
    }) => assetApi.reviewAssetConcepts(groupId, input.linkIds, input.reviewStatus),
    onSuccess: update,
  });
  const addPhrase = useMutation({
    mutationFn: (phrase: string) => assetApi.addAssetSearchPhrase(groupId, phrase),
    onSuccess: update,
  });
  const reviewPhrase = useMutation({
    mutationFn: (input: {
      phraseId: string;
      reviewStatus: 'accepted' | 'rejected';
    }) => assetApi.reviewAssetSearchPhrase(groupId, input.phraseId, input.reviewStatus),
    onSuccess: update,
  });
  const removePhrase = useMutation({
    mutationFn: (phraseId: string) => assetApi.removeAssetSearchPhrase(groupId, phraseId),
    onSuccess: update,
  });

  return {
    addPhrase,
    addVariant,
    confirmConcept,
    deleteVariant,
    replacePrimary,
    removePhrase,
    reviewConcept,
    reviewConcepts,
    reviewPhrase,
  };
}
