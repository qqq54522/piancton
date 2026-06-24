export type {
  ApiErrorBody,
  AnalysisRun,
  BusinessLabel,
  AuditLog,
  ContentTag,
  ImageDetail,
  ImageItem,
  Level2Category,
  LoginResponse,
  Tag,
  User,
  UserRole,
} from './api.generated';

import type { ImageItem, Tag } from './api.generated';

export interface TagWithCount extends Tag {
  children?: TagWithCount[];
}

export interface ImageListParams {
  keyword?: string;
  tagIds?: string[];
  cursor?: string;
  limit?: number;
  sortBy?: 'createdAt' | 'downloadCount';
  category?: string;
}

export interface ImageListResponse {
  items: ImageItem[];
  nextCursor?: string;
  hasMore: boolean;
}

export interface UpdateImageTagsRequest {
  tagIds: string[];
  primaryTagId?: string | null;
}

export interface UpdateImageTitleRequest {
  title: string;
}

export interface CreateTagRequest {
  name: string;
  color: string;
  parentId?: string | null;
  isSecondary?: boolean;
}

export interface TagDeleteImpact {
  tagId: string;
  tagName: string;
  subtreeTagCount: number;
  directChildCount: number;
  affectedImageCount: number;
}

export interface ExpandedSearchTag {
  tag: string;
  relation: 'exact' | 'strong' | 'medium' | 'weak';
  reason: string;
  weight: number;
}

export interface SearchCategoryMatch {
  category: string;
  relation: 'direct' | 'related' | 'fallback';
  reason: string;
  weight: number;
}

export interface SearchUnderstanding {
  originalQuery: string;
  normalizedQuery: string;
  searchIntent: string;
  queryType: string;
  expandedLevel1Tags: ExpandedSearchTag[];
  matchedLevel2Categories: SearchCategoryMatch[];
  excludeTags: string[];
  searchStrategy: string;
}

export type SearchMode = 'precise' | 'smart';

export interface SemanticSearchRequest {
  keyword: string;
  limit?: number;
  searchMode?: SearchMode;
}

export interface ScoredImageMatch {
  image: ImageItem;
  matchLevel: 'S' | 'A' | 'B' | 'C';
  finalScore: number;
  matchReasons: string[];
  matchedLevel1Tags: string[];
  matchedLevel2Categories: string[];
}

export interface SellingPointHit {
  pointKey: string;
  pointName: string;
  weight: number;
}

export interface SellingPointMatch {
  systemKey: string;
  systemName: string;
  points: SellingPointHit[];
}

export interface SemanticSearchResponse {
  results: ScoredImageMatch[];
  hasMore: boolean;
  searchUnderstanding?: SearchUnderstanding;
  matchSummary?: string;
  searchMode?: 'selling_point' | 'fuzzy' | 'meilisearch';
  fallback?: boolean;
  fallbackReason?: string;
  sellingPointMatches?: SellingPointMatch[];
}

export interface ProviderStatus {
  provider: string;
  configured: boolean;
  modelName: string;
}
