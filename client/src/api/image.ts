import { api } from './client';

import type {
  AssetSearchPhraseSuggestion,
  ImageDetail,
  ImageItem,
  ImageListParams,
  ImageListResponse,
  ImageTitleResolution,
  ProviderStatus,
  SearchFeedbackRequest,
  SemanticSearchRequest,
  SemanticSearchResponse,
  TagWithCount,
  UpdateImageTitleRequest,
} from '@client/src/types/api';


export async function fetchImages(params: ImageListParams): Promise<ImageListResponse> {
  return (await api.get('/api/images', { params })).data;
}

export async function fetchImageDetail(id: string): Promise<ImageDetail> {
  return (await api.get(`/api/images/${id}`)).data;
}

export async function uploadImage(input: {
  file: File;
  title: string;
  expectedSearchWords?: string[];
  channel?: string;
  styleLabel?: string;
  isSceneImage?: boolean;
  autoAnalyze?: boolean;
}): Promise<ImageItem> {
  const form = new FormData();
  form.append('file', input.file);
  form.append('title', input.title);
  form.append('expectedSearchWords', (input.expectedSearchWords ?? []).join('\n'));
  if (input.channel?.trim()) form.append('channel', input.channel.trim());
  if (input.styleLabel?.trim()) form.append('styleLabel', input.styleLabel.trim());
  if (typeof input.isSceneImage === 'boolean') {
    form.append('isSceneImage', String(input.isSceneImage));
  }
  form.append('autoAnalyze', String(input.autoAnalyze ?? true));
  return (await api.post('/api/images/upload', form)).data;
}

export async function updateImageTitle(
  id: string,
  data: UpdateImageTitleRequest,
): Promise<ImageItem> {
  return (await api.patch(`/api/images/${id}/title`, data)).data;
}

export async function resolveImageTitle(title: string): Promise<ImageTitleResolution> {
  return (await api.get('/api/images/title-resolution', { params: { title } })).data;
}

export async function deleteImage(id: string): Promise<void> {
  await api.delete(`/api/images/${id}`);
}

export async function fetchTrash(): Promise<ImageItem[]> {
  return (await api.get('/api/images/trash')).data;
}

export async function restoreImage(id: string): Promise<ImageItem> {
  return (await api.post(`/api/images/${id}/restore`)).data;
}

export async function purgeImage(id: string): Promise<void> {
  await api.delete(`/api/images/${id}/purge`);
}

export async function fetchTags(): Promise<TagWithCount[]> {
  return (await api.get('/api/tags')).data;
}

export async function semanticSearch(
  params: SemanticSearchRequest,
): Promise<SemanticSearchResponse> {
  return (
    await api.post('/api/images/search', params, { timeout: 180_000 })
  ).data;
}

export async function submitSearchFeedback(data: SearchFeedbackRequest): Promise<void> {
  await api.post('/api/search-feedback', data);
}

export async function fetchProviderStatus(): Promise<ProviderStatus> {
  return (await api.get('/api/ai/provider')).data;
}

export async function generateAssetSearchPhrases(input: {
  file: File;
  count: number;
  title?: string;
  conceptCode?: string;
}): Promise<AssetSearchPhraseSuggestion> {
  const form = new FormData();
  form.append('file', input.file);
  form.append('count', String(input.count));
  if (input.title?.trim()) form.append('title', input.title.trim());
  if (input.conceptCode?.trim()) form.append('conceptCode', input.conceptCode.trim());
  return (
    await api.post('/api/ai/asset-search-phrases', form, { timeout: 120_000 })
  ).data;
}

export async function analyzeContentTags(id: string): Promise<void> {
  await api.post(`/api/ai/images/${id}/analyze`);
}
