import { api } from './client';

import type {
  ImageDetail,
  ImageChannelOptions,
  ImageItem,
  ImageListParams,
  ImageListResponse,
  ForYouImageListResponse,
  ImageTitleResolution,
  ProviderStatus,
  SearchFeedbackRequest,
  SearchInteractionAction,
  SearchInteractionSource,
  SearchQueryRecommendations,
  SemanticSearchRequest,
  SemanticSearchResponse,
  TagWithCount,
  UpdateImageTitleRequest,
} from '@client/src/types/api';


export async function fetchImages(params: ImageListParams): Promise<ImageListResponse> {
  return (await api.get('/api/images', { params })).data;
}

export async function fetchForYouImages(limit = 48): Promise<ForYouImageListResponse> {
  return (await api.get('/api/images/for-you', { params: { limit } })).data;
}

export async function fetchImageChannels(): Promise<ImageChannelOptions> {
  return (await api.get('/api/images/channels')).data;
}

export async function fetchSearchQueryRecommendations(
  limit = 8,
): Promise<SearchQueryRecommendations> {
  return (await api.get('/api/images/query-recommendations', { params: { limit } })).data;
}

export async function fetchImageDetail(id: string): Promise<ImageDetail> {
  return (await api.get(`/api/images/${id}`)).data;
}

export async function uploadImage(input: {
  file: File;
  title: string;
  channel?: string;
  styleLabel?: string;
  isSceneImage?: boolean;
  autoAnalyze?: boolean;
}): Promise<ImageItem> {
  const form = new FormData();
  form.append('file', input.file);
  form.append('title', input.title);
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

export async function updateImageFilterMetadata(
  id: string,
  data: {
    channel: string;
    styleLabel?: string | null;
    isSceneImage: boolean;
  },
): Promise<ImageItem> {
  return (await api.patch(`/api/images/${id}/filter-metadata`, data)).data;
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
    await api.post('/api/images/search', params, { timeout: 210_000 })
  ).data;
}

export async function submitSearchFeedback(data: SearchFeedbackRequest): Promise<void> {
  await api.post('/api/search-feedback', data);
}

export async function recordSearchInteraction(data: {
  searchLogId?: string | null;
  keyword: string;
  action: SearchInteractionAction;
  resultImageId?: string | null;
  assetGroupId?: string | null;
  position?: number;
  source?: SearchInteractionSource;
  conversationId?: string | null;
}): Promise<void> {
  await api.post('/api/usage/search-interaction', data);
}

export async function fetchProviderStatus(): Promise<ProviderStatus> {
  return (await api.get('/api/ai/provider')).data;
}
