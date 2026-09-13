import { api } from './client';

import type {
  AssetCollectionBoard,
  AssetCollectionMembership,
  AssetCollectionSummary,
  AssetSaveContext,
  SavedAssetListResponse,
} from '@client/src/types/api';

const ROOT = '/api/me/asset-collections';

export async function fetchAssetCollectionSummary(): Promise<AssetCollectionSummary> {
  return (await api.get(`${ROOT}/summary`)).data;
}

export async function fetchAssetMembership(
  assetGroupId: string,
): Promise<AssetCollectionMembership> {
  return (await api.get(`${ROOT}/assets/${assetGroupId}/membership`)).data;
}

export async function fetchLikedAssets(cursor?: string): Promise<SavedAssetListResponse> {
  return (await api.get(`${ROOT}/likes`, { params: { cursor, limit: 100 } })).data;
}

export async function likeAsset(
  assetGroupId: string,
  context: AssetSaveContext,
): Promise<AssetCollectionMembership> {
  return (await api.put(`${ROOT}/likes/${assetGroupId}`, context)).data;
}

export async function unlikeAsset(
  assetGroupId: string,
  context: AssetSaveContext,
): Promise<AssetCollectionMembership> {
  return (await api.delete(`${ROOT}/likes/${assetGroupId}`, { data: context })).data;
}

export async function fetchCollectionBoards(): Promise<AssetCollectionBoard[]> {
  return (await api.get(`${ROOT}/boards`)).data.items;
}

export async function createCollectionBoard(name: string): Promise<AssetCollectionBoard> {
  return (await api.post(`${ROOT}/boards`, { name })).data;
}

export async function renameCollectionBoard(
  boardId: string,
  name: string,
): Promise<AssetCollectionBoard> {
  return (await api.patch(`${ROOT}/boards/${boardId}`, { name })).data;
}

export async function deleteCollectionBoard(boardId: string): Promise<void> {
  await api.delete(`${ROOT}/boards/${boardId}`);
}

export async function fetchCollectionBoardItems(
  boardId: string,
  cursor?: string,
): Promise<SavedAssetListResponse> {
  return (await api.get(`${ROOT}/boards/${boardId}/items`, {
    params: { cursor, limit: 100 },
  })).data;
}

export async function addAssetToBoard(
  boardId: string,
  assetGroupId: string,
  context: AssetSaveContext,
): Promise<AssetCollectionMembership> {
  return (await api.put(`${ROOT}/boards/${boardId}/items/${assetGroupId}`, context)).data;
}

export async function removeAssetFromBoard(
  boardId: string,
  assetGroupId: string,
  context: AssetSaveContext,
): Promise<AssetCollectionMembership> {
  return (
    await api.delete(`${ROOT}/boards/${boardId}/items/${assetGroupId}`, { data: context })
  ).data;
}
