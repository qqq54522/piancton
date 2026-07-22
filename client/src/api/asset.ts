import { api } from './client';

import type {
  AssetConceptLink,
  AssetGroup,
  BusinessFacetCatalog,
  BusinessConcept,
} from '@client/src/types/api';

export type AssetRelationRole = AssetConceptLink['relationRole'];

export async function fetchAssetGroup(id: string): Promise<AssetGroup> {
  return (await api.get(`/api/asset-groups/${id}`)).data;
}

export async function fetchBusinessConcepts(): Promise<BusinessConcept[]> {
  return (await api.get('/api/business-concepts')).data;
}

export async function fetchBusinessFacets(): Promise<BusinessFacetCatalog> {
  return (await api.get('/api/business-facets')).data;
}

export async function updateAssetBusinessClassification(
  groupId: string,
  input: {
    conceptId?: string | null;
    proofPointCode?: string | null;
    evidencePointCode?: string | null;
  },
): Promise<AssetGroup> {
  return (await api.patch(`/api/asset-groups/${groupId}/business-classification`, input)).data;
}

export async function addAssetVariant(
  groupId: string,
  input: {
    file: File;
    title?: string;
    role: 'derivative' | 'alternative' | 'revision';
    channel?: string;
  },
): Promise<AssetGroup> {
  const form = new FormData();
  form.append('file', input.file);
  form.append('assetRole', input.role);
  if (input.title?.trim()) form.append('title', input.title.trim());
  if (input.channel?.trim()) form.append('channel', input.channel.trim());
  form.append('autoAnalyze', String(input.role !== 'derivative'));
  return (await api.post(`/api/asset-groups/${groupId}/images`, form)).data;
}

export async function replaceAssetPrimary(
  groupId: string,
  input: { file: File; title?: string; channel?: string },
): Promise<AssetGroup> {
  const form = new FormData();
  form.append('file', input.file);
  if (input.title?.trim()) form.append('title', input.title.trim());
  if (input.channel?.trim()) form.append('channel', input.channel.trim());
  form.append('autoAnalyze', 'true');
  return (await api.post(`/api/asset-groups/${groupId}/primary-image`, form)).data;
}

export async function deleteAssetVariant(
  groupId: string,
  imageId: string,
): Promise<AssetGroup> {
  return (await api.delete(`/api/asset-groups/${groupId}/images/${imageId}`)).data;
}

export async function confirmAssetConcept(
  groupId: string,
  conceptId: string,
  relationRole: AssetRelationRole,
): Promise<AssetGroup> {
  return (await api.post(`/api/asset-groups/${groupId}/concept-links`, {
    conceptId,
    relationRole,
  })).data;
}

export async function reviewAssetConcept(
  groupId: string,
  linkId: string,
  reviewStatus: 'accepted' | 'rejected',
  relationRole?: AssetRelationRole,
): Promise<AssetGroup> {
  return (await api.patch(`/api/asset-groups/${groupId}/concept-links/${linkId}`, {
    reviewStatus,
    relationRole,
  })).data;
}

export async function reviewAssetConcepts(
  groupId: string,
  linkIds: string[],
  reviewStatus: 'accepted' | 'rejected',
): Promise<AssetGroup> {
  return (await api.post(`/api/asset-groups/${groupId}/concept-links/review-batch`, {
    linkIds,
    reviewStatus,
  })).data;
}

export async function addAssetSearchPhrase(
  groupId: string,
  phrase: string,
): Promise<AssetGroup> {
  return (await api.post(`/api/asset-groups/${groupId}/search-phrases`, {
    phrase,
    weight: 1,
  })).data;
}

export async function reviewAssetSearchPhrase(
  groupId: string,
  phraseId: string,
  reviewStatus: 'accepted' | 'rejected',
): Promise<AssetGroup> {
  return (await api.patch(`/api/asset-groups/${groupId}/search-phrases/${phraseId}`, {
    reviewStatus,
  })).data;
}

export async function removeAssetSearchPhrase(
  groupId: string,
  phraseId: string,
): Promise<AssetGroup> {
  return (await api.delete(`/api/asset-groups/${groupId}/search-phrases/${phraseId}`)).data;
}
