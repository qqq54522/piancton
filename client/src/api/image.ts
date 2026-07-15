import { api } from './client';

import type {
  ImageDetail,
  ImageItem,
  ImageListParams,
  ImageListResponse,
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
  autoAnalyze?: boolean;
}): Promise<ImageItem> {
  const form = new FormData();
  form.append('file', input.file);
  form.append('title', input.title);
  form.append('expectedSearchWords', (input.expectedSearchWords ?? []).join('\n'));
  if (input.channel?.trim()) form.append('channel', input.channel.trim());
  form.append('autoAnalyze', String(input.autoAnalyze ?? true));
  return (await api.post('/api/images/upload', form)).data;
}

export async function updateImageTitle(
  id: string,
  data: UpdateImageTitleRequest,
): Promise<ImageItem> {
  return (await api.patch(`/api/images/${id}/title`, data)).data;
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
  return (await api.post('/api/images/search', params)).data;
}

export async function submitSearchFeedback(data: SearchFeedbackRequest): Promise<void> {
  await api.post('/api/search-feedback', data);
}

export async function fetchProviderStatus(): Promise<ProviderStatus> {
  return (await api.get('/api/ai/provider')).data;
}

export async function analyzeContentTags(id: string): Promise<void> {
  await api.post(`/api/ai/images/${id}/analyze`);
}
