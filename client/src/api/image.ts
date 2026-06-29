import { api } from './client';

import type {
  CreateTagRequest,
  ImageDetail,
  ImageItem,
  ImageListParams,
  ImageListResponse,
  ProviderStatus,
  SearchFeedbackRequest,
  SemanticSearchRequest,
  SemanticSearchResponse,
  Tag,
  TagDeleteImpact,
  TagWithCount,
  UpdateImageTagsRequest,
  UpdateImageTitleRequest,
} from '@client/src/types/api';


export async function fetchImages(params: ImageListParams): Promise<ImageListResponse> {
  return (await api.get('/api/images', {
    params: { ...params, tagIds: params.tagIds?.join(',') },
  })).data;
}

export async function fetchImageDetail(id: string): Promise<ImageDetail> {
  return (await api.get(`/api/images/${id}`)).data;
}

export async function uploadImage(
  file: File,
  title: string,
  tagIds: string[],
  primaryTagId: string | null,
  categories: string[],
  expectedSearchWords: string[] = [],
  autoAnalyze = true,
): Promise<ImageItem> {
  const form = new FormData();
  form.append('file', file);
  form.append('title', title);
  form.append('tagIds', tagIds.join(','));
  if (primaryTagId) form.append('primaryTagId', primaryTagId);
  form.append('categories', categories.join(','));
  form.append('expectedSearchWords', expectedSearchWords.join('\n'));
  form.append('autoAnalyze', String(autoAnalyze));
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

export async function updateImageTags(
  id: string,
  data: UpdateImageTagsRequest,
): Promise<ImageItem> {
  return (await api.patch(`/api/images/${id}/tags`, data)).data;
}

export async function reviewBusinessLabel(
  imageId: string,
  labelId: string,
  reviewStatus: 'accepted' | 'pending' | 'rejected',
): Promise<ImageDetail> {
  return (await api.patch(`/api/images/${imageId}/business-labels/${labelId}`, {
    reviewStatus,
  })).data;
}

export async function fetchTags(): Promise<TagWithCount[]> {
  return (await api.get('/api/tags')).data;
}

export async function createTag(data: CreateTagRequest): Promise<Tag> {
  return (await api.post('/api/tags', data)).data;
}

export async function updateTag(
  id: string,
  data: { name?: string; color?: string; parentId?: string | null },
): Promise<Tag> {
  return (await api.patch(`/api/tags/${id}`, data)).data;
}

export async function deleteTag(id: string): Promise<void> {
  await api.delete(`/api/tags/${id}`);
}

export async function fetchTagDeleteImpact(id: string): Promise<TagDeleteImpact> {
  return (await api.get(`/api/tags/${id}/delete-impact`)).data;
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
