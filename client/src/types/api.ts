export type {
  ApiErrorBody,
  AnalysisRun,
  AuditLog,
  ContentTag,
  ImageSemanticProfile,
  ImageDetail,
  ImageItem,
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
  cursor?: string;
  limit?: number;
  sortBy?: 'createdAt' | 'downloadCount';
}

export interface ImageListResponse {
  items: ImageItem[];
  nextCursor?: string;
  hasMore: boolean;
}

export interface UpdateImageTitleRequest {
  title: string;
}

export interface ExpandedSearchTerm {
  term: string;
  relation: 'exact' | 'strong' | 'medium' | 'weak';
  reason: string;
  weight: number;
}

export interface SearchConceptMatch {
  concept: string;
  relation: 'direct' | 'related' | 'fallback';
  reason: string;
  weight: number;
}

export interface SearchUnderstanding {
  originalQuery: string;
  normalizedQuery: string;
  searchIntent: string;
  queryType: string;
  expandedTerms: ExpandedSearchTerm[];
  matchedBusinessConcepts: SearchConceptMatch[];
  excludedConcepts: string[];
  searchStrategy: string;
}

export interface SemanticSearchRequest {
  keyword: string;
  limit?: number;
  systemCode?: string | null;
}

export interface AssetImage {
  id: string;
  title: string;
  fileName: string;
  thumbnailUrl: string;
  contentUrl: string;
  downloadUrl: string;
  assetRole: 'primary' | 'derivative' | 'alternative' | 'revision' | string;
  width?: number | null;
  height?: number | null;
  aspectRatio?: number | null;
  channel?: string | null;
  versionNo: number;
  isCurrent: boolean;
}

export interface AssetConceptLink {
  id: string;
  conceptId: string;
  conceptCode: string;
  conceptName: string;
  relationRole: 'expresses' | 'supports' | 'visual_related' | 'excludes';
  origin: 'manual' | 'ai' | 'migrated' | string;
  reviewStatus: 'pending' | 'accepted' | 'rejected';
  confidence?: number | null;
  evidenceReason?: string | null;
  sourceRef?: string | null;
}

export interface AssetSearchPhrase {
  id: string;
  phrase: string;
  origin: string;
  reviewStatus: 'pending' | 'accepted' | 'rejected';
  weight: number;
}

export interface AssetGroup {
  id: string;
  title: string;
  primaryImageId?: string | null;
  approvalStatus: string;
  publishStatus: string;
  createdBy: string;
  images: AssetImage[];
  conceptLinks: AssetConceptLink[];
  searchPhrases: AssetSearchPhrase[];
  createdAt: string;
  updatedAt: string;
}

export interface ConceptSystemLink {
  systemTagId: string;
  systemName: string;
  role: string;
  weight: number;
  reason?: string | null;
  status: string;
}

export interface BusinessConcept {
  id: string;
  code: string;
  name: string;
  conceptType: string;
  definition?: string | null;
  status: string;
  version: number;
  systemLinks: ConceptSystemLink[];
}

export interface ScoredImageMatch {
  image: ImageItem;
  matchLevel: 'S' | 'A' | 'B' | 'C';
  finalScore: number;
  matchReasons: string[];
  matchedContentTerms: string[];
  matchedBusinessConcepts: string[];
  assetGroupId?: string | null;
  assetTitle?: string | null;
  availableVariants: AssetImage[];
  expressedConcepts: string[];
  supportedConcepts: string[];
}

export interface SearchBranchStatus {
  source: string;
  status: 'ok' | 'skipped' | 'timed_out' | 'failed';
  durationMs: number;
  resultCount: number;
  cacheHit: boolean;
  detail?: string | null;
}

export interface SearchDiagnostics {
  totalDurationMs: number;
  timedOut: boolean;
  rerankerUsed: boolean;
  cacheHit: boolean;
  degradedSources: string[];
  branches: SearchBranchStatus[];
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
  searchDiagnostics?: SearchDiagnostics | null;
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
  servedMode: string;
  fallback: boolean;
  fallbackReason?: string | null;
  resultCount: number;
  normalizedQuery?: string | null;
  queryType?: string | null;
  matchedConcept?: string | null;
  topImageIds: string[];
  topAssetGroupIds: string[];
  matchReasons: string[];
  durationMs?: number | null;
  timedOut: boolean;
  cacheHit: boolean;
  rerankerUsed: boolean;
  degradedSources: string[];
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
  resultImageId?: string | null;
  assetGroupId?: string | null;
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

export interface AiConceptReviewQueueItem {
  id: string;
  assetGroupId: string;
  imageId: string;
  imageTitle: string;
  thumbnailUrl: string;
  conceptCode: string;
  conceptName: string;
  systemNames: string[];
  relationRole: string;
  confidence?: number | null;
  reason?: string | null;
  createdAt: string;
}

export interface ConceptHealthItem {
  conceptId: string;
  conceptCode: string;
  conceptName: string;
  systemNames: string[];
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
  suggestedConcept?: string | null;
  reason: string;
  source: string;
}

export interface SearchFeedbackRequest {
  searchLogId?: string | null;
  keyword: string;
  feedbackType: SearchFeedbackType;
  note?: string | null;
  resultImageId?: string | null;
  assetGroupId?: string | null;
}

export interface SearchOpsSummary {
  totalSearches: number;
  zeroResultCount: number;
  fallbackCount: number;
  timedOutCount: number;
  cacheHitCount: number;
  rerankerUsedCount: number;
  averageDurationMs: number;
  p95DurationMs: number;
  aiUnderstoodCount: number;
  topQueries: SearchMetricItem[];
  zeroResultQueries: SearchMetricItem[];
  topNormalizedQueries: SearchMetricItem[];
  topMatchedConcepts: SearchMetricItem[];
  feedbackCount: number;
  feedbackByType: SearchMetricItem[];
  feedbackQueries: SearchMetricItem[];
  recentFeedback: SearchFeedbackItem[];
  recentLogs: SearchLogItem[];
  searchIssues: SearchOpsIssue[];
  aiReviewQueue: AiConceptReviewQueueItem[];
  conceptHealth: ConceptHealthItem[];
  assetGaps: AssetGapItem[];
}
