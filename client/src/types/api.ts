export type {
  ApiErrorBody,
  AnalysisRun,
  BusinessLabel,
  AuditLog,
  ContentTag,
  ImageSemanticProfile,
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

export interface SemanticSearchResponse {
  results: ScoredImageMatch[];
  hasMore: boolean;
  searchLogId?: string | null;
  searchUnderstanding?: SearchUnderstanding;
  matchSummary?: string;
  searchMode?: 'fuzzy' | 'meilisearch';
  fallback?: boolean;
  fallbackReason?: string;
}

export interface ProviderStatus {
  provider: string;
  configured: boolean;
  modelName: string;
}

export interface SearchMetricItem {
  label: string;
  count: number;
}

export interface SearchLogItem {
  id: string;
  keyword: string;
  requestedMode: string;
  servedMode: string;
  fallback: boolean;
  fallbackReason?: string | null;
  resultCount: number;
  normalizedQuery?: string | null;
  queryType?: string | null;
  matchedCategory?: string | null;
  topImageIds: string[];
  matchReasons: string[];
  createdAt: string;
}

export type SearchFeedbackType =
  | 'not_relevant'
  | 'too_few_results'
  | 'need_different_style'
  | 'asset_request';

export interface SearchFeedbackItem {
  id: string;
  searchLogId?: string | null;
  keyword: string;
  feedbackType: SearchFeedbackType | string;
  note?: string | null;
  createdAt: string;
}

export interface SearchOpsIssue {
  id: string;
  keyword: string;
  issueType: string;
  severity: 'high' | 'medium' | 'low';
  source: string;
  count: number;
  reason: string;
  suggestedAction: string;
  latestAt: string;
}

export interface AiReviewQueueItem {
  id: string;
  imageId: string;
  imageTitle: string;
  thumbnailUrl: string;
  labelCode: string;
  labelName: string;
  systemName?: string | null;
  role: string;
  confidence?: number | null;
  evidenceLevel?: string | null;
  reason?: string | null;
  createdAt: string;
}

export interface LabelHealthItem {
  tagId: string;
  labelCode?: string | null;
  labelName: string;
  systemName?: string | null;
  imageCount: number;
  manualCount: number;
  aiPendingCount: number;
  aiAcceptedCount: number;
  aiRejectedCount: number;
  searchCount: number;
  healthLevel: 'healthy' | 'needs_assets' | 'needs_review' | 'watch';
  recommendation: string;
}

export interface AssetGapItem {
  keyword: string;
  demandCount: number;
  suggestedLabel?: string | null;
  reason: string;
  source: string;
}

export interface SearchFeedbackRequest {
  searchLogId?: string | null;
  keyword: string;
  feedbackType: SearchFeedbackType;
  note?: string | null;
}

export interface SearchOpsSummary {
  totalSearches: number;
  zeroResultCount: number;
  fallbackCount: number;
  aiUnderstoodCount: number;
  smartSearchCount: number;
  preciseSearchCount: number;
  topQueries: SearchMetricItem[];
  zeroResultQueries: SearchMetricItem[];
  topNormalizedQueries: SearchMetricItem[];
  topMatchedCategories: SearchMetricItem[];
  feedbackCount: number;
  feedbackByType: SearchMetricItem[];
  feedbackQueries: SearchMetricItem[];
  recentFeedback: SearchFeedbackItem[];
  recentLogs: SearchLogItem[];
  searchIssues: SearchOpsIssue[];
  aiReviewQueue: AiReviewQueueItem[];
  labelHealth: LabelHealthItem[];
  assetGaps: AssetGapItem[];
}
