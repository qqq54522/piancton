export type {
  ApiErrorBody,
  AnalysisRun,
  AuditLog,
  ImageSemanticProfile,
  ImageDetail,
  ImageItem,
  ImageTitleResolution,
  LoginResponse,
  Tag,
  User,
  UserRole,
} from './api.generated';

import type {
  ImageItem,
  Tag,
} from './api.generated';
import type { components } from './openapi';

export type ImageIdentityCodeRead = components['schemas']['ImageIdentityCodeRead'];
export type ImageIdentityCodeSummary = components['schemas']['ImageIdentityCodeSummary'];
export type ImageIdentityCodeListResponse = components['schemas']['ImageIdentityCodeListResponse'];

export interface TagWithCount extends Tag {
  children?: TagWithCount[];
}

export interface ImageListParams {
  keyword?: string;
  channel?: string;
  cursor?: string;
  limit?: number;
  sortBy?: 'createdAt' | 'downloadCount';
}

export interface ImageListResponse {
  items: ImageItem[];
  nextCursor?: string;
  hasMore: boolean;
}

export interface ImageChannelOptions {
  channels: string[];
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

export interface SearchProofPointMatch {
  code: string;
  conceptCode: string;
  name: string;
  reason: string;
  weight: number;
  evidenceTerms: string[];
}

export interface SearchEvidencePointMatch {
  code: string;
  proofPointCode: string;
  conceptCode: string;
  name: string;
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
  matchedProofPoints: SearchProofPointMatch[];
  matchedEvidencePoints: SearchEvidencePointMatch[];
  excludedConcepts: string[];
  searchStrategy: string;
}

export interface SemanticSearchRequest {
  keyword: string;
  limit?: number;
  systemCode?: string | null;
  conceptCode?: string | null;
  proofPointCode?: string | null;
  evidencePointCode?: string | null;
}

export interface AssetImage {
    id: string;
  identityCode?: string | null;
  title: string;
  fileName: string;
  thumbnailUrl: string;
  contentUrl: string;
  downloadUrl: string;
  mediaType?: string;
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

export type AssetSourceLinkType =
  | 'figma'
  | 'design_file'
  | 'cloud_drive'
  | 'reference_doc'
  | 'asset_package'
  | 'other';

export interface AssetSourceLink {
  id: string;
  label: string;
  url: string;
  linkType: AssetSourceLinkType;
  note?: string | null;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
}

export interface AssetGroup {
  id: string;
  title: string;
  primaryImageId?: string | null;
  approvalStatus: string;
  publishStatus: string;
  styleLabel?: string | null;
  isSceneImage?: boolean | null;
  createdBy: string;
  images: AssetImage[];
  conceptLinks: AssetConceptLink[];
  searchPhrases: AssetSearchPhrase[];
  sourceLinks: AssetSourceLink[];
  primaryProofPointCode?: string | null;
  primaryEvidencePointCode?: string | null;
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

export type ConceptPhraseType =
  | 'official'
  | 'alias'
  | 'pain'
  | 'outcome'
  | 'scenario'
  | 'colloquial'
  | 'typo';

export interface ConceptSearchPhrase {
  id: string;
  phrase: string;
  phraseType: ConceptPhraseType;
  origin: 'source_document' | 'manual' | 'ai' | 'search_feedback' | 'migrated';
  reviewStatus: 'pending' | 'accepted' | 'rejected';
  weight: number;
  sourceRef?: string | null;
  createdAt: string;
}

export interface BusinessConcept {
  id: string;
  code: string;
  name: string;
  conceptType: string;
  definition?: string | null;
  recommendationText?: string | null;
  status: string;
  version: number;
  systemLinks: ConceptSystemLink[];
  searchPhrases: ConceptSearchPhrase[];
}

export interface ProofPointFacet {
  code: string;
  conceptCode: string;
  name: string;
}

export interface EvidencePointFacet {
  code: string;
  proofPointCode: string;
  conceptCode: string;
  name: string;
  sourceRef?: string;
  sourcePaths?: EvidencePointSourcePathNode[][];
  reviewNotes?: string[];
}

export interface EvidencePointSourcePathNode {
  level: 'system' | 'selling_point' | 'proof_group' | 'evidence_expression';
  label: string;
}

export interface BusinessFacetCatalog {
  proofPoints: ProofPointFacet[];
  evidencePoints: EvidencePointFacet[];
}

export interface ScoredImageMatch {
  image: ImageItem;
  matchLevel: 'S' | 'A' | 'B' | 'C';
  finalScore: number;
  matchReasons: string[];
  resultRecommendationReason?: string | null;
  matchedContentTerms: string[];
  matchedBusinessConcepts: string[];
  assetGroupId?: string | null;
  assetTitle?: string | null;
  availableVariants: AssetImage[];
  expressedConcepts: string[];
  supportedConcepts: string[];
  matchedQueryConcepts: SearchResultConceptMatch[];
  primaryProofPointCode?: string | null;
  primaryProofPointName?: string | null;
  primaryProofPointClaim?: string | null;
  primaryEvidencePointCode?: string | null;
  primaryEvidencePointName?: string | null;
}

export interface SearchResultConceptMatch {
  conceptCode: string;
  conceptName: string;
  relationRole: 'expresses' | 'supports' | 'visual_related';
  recommendationText?: string | null;
}

export interface SearchBranchStatus {
  source: string;
  status: 'ok' | 'skipped' | 'timed_out' | 'failed';
  durationMs: number;
  resultCount: number;
  cacheHit: boolean;
  detail?: string | null;
  attempts?: ModelAttempt[];
}

export interface ModelAttempt {
  task: string;
  layer: string;
  provider: string;
  model: string;
  status: string;
  durationMs: number;
  fallbackIndex?: number | null;
  error: string;
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
  routeExplanation?: string | null;
  searchMode?: 'fuzzy' | 'meilisearch';
  fallback?: boolean;
  fallbackReason?: string;
  searchDiagnostics?: SearchDiagnostics | null;
  identityCode?: string | null;
  exactMatch?: boolean;
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
  | 'relevant'
  | 'not_relevant'
  | 'too_few_results'
  | 'need_different_style'
  | 'right_business_wrong_visual'
  | 'right_visual_wrong_business'
  | 'wrong_version'
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

export interface AssetOperationsOverview {
  assetGroupCount: number;
  imageCount: number;
  currentImageCount: number;
  missingSourceLinkCount: number;
  missingSourceLinkRate: number;
  singleVersionGroupCount: number;
  missingBusinessRelationCount: number;
  missingSearchPhraseCount: number;
  missingStyleCount: number;
  unsetSceneCount: number;
  missingChannelCount: number;
  totalDownloadCount: number;
  unusedAssetGroupCount: number;
}

export interface AssetOpsIssue {
  id: string;
  assetGroupId: string;
  title: string;
  primaryImageId?: string | null;
  issueType: string;
  severity: 'high' | 'medium' | 'low';
  message: string;
  suggestedAction: string;
  updatedAt: string;
}

export interface SourceLinkRecentItem {
  id: string;
  assetGroupId: string;
  assetGroupTitle: string;
  primaryImageId?: string | null;
  label: string;
  linkType: string;
  url: string;
  reviewStatus: 'ok' | 'stale';
  updatedAt: string;
}

export interface SourceLinkHealth {
  totalLinks: number;
  groupsWithSourceLinks: number;
  groupsWithoutSourceLinks: number;
  staleLinkCount: number;
  groupsRequiringReview: number;
  linkTypeCounts: SearchMetricItem[];
  recentLinks: SourceLinkRecentItem[];
}

export interface SearchPerformanceSummary {
  sampleCount: number;
  averageDurationMs: number;
  p50DurationMs: number;
  p95DurationMs: number;
  p99DurationMs: number;
  slowSearchCount: number;
  slowSearchRate: number;
  timeoutCount: number;
  fallbackCount: number;
  cacheHitCount: number;
  cacheHitRate: number;
  rerankerUsedCount: number;
  aiUnderstoodCount: number;
  modelWorkUnitCount: number;
  modelWorkUnitRate: number;
  recentSlowLogs: SearchLogItem[];
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
  assetOperations: AssetOperationsOverview;
  assetOpsIssues: AssetOpsIssue[];
  sourceLinkHealth: SourceLinkHealth;
  searchPerformance: SearchPerformanceSummary;
}

export interface PageViewCreate {
  path: string;
  title?: string | null;
}

export interface UsageTotals {
  loginCount: number;
  pageViewCount: number;
  downloadCount: number;
  activeUserCount: number;
}

export interface DailyUsageMetric {
  date: string;
  loginCount: number;
  pageViewCount: number;
  downloadCount: number;
  activeUserCount: number;
}

export interface UserUsageMetric {
  userId: string;
  username: string;
  role: string;
  isActive: boolean;
  loginCount: number;
  pageViewCount: number;
  downloadCount: number;
  activityCount: number;
  lastActivityAt?: string | null;
}

export interface UsageEventRead {
  id: string;
  userId?: string | null;
  username?: string | null;
  eventType: string;
  targetType?: string | null;
  targetId?: string | null;
  path?: string | null;
  details: Record<string, unknown>;
  createdAt: string;
}

export interface UsageAnalyticsSummary {
  dateFrom: string;
  dateTo: string;
  totals: UsageTotals;
  daily: DailyUsageMetric[];
  users: UserUsageMetric[];
  recentEvents: UsageEventRead[];
}

export type ModelTaskName =
  | 'image_content_analysis'
  | 'search_system_routing'
  | 'search_intent_understanding'
  | 'search_proof_point_understanding'
  | 'search_candidate_review'
  | 'search_result_recommendation_reason'
  | 'copy_selling_point_matching'
  | 'asset_agent_chat';

export interface ApiCredential {
  id: string;
  label: string;
  providerType: string;
  baseUrl: string;
  modelName: string;
  apiKeyPreview: string;
  taskScope: string[];
  status: string;
  priority: number;
  timeoutSeconds: number;
  temperature: number;
  temperatureEnabled: boolean;
  maxConcurrency: number;
  autoAssignEnabled: boolean;
  capabilityProfile: ApiCredentialCapability[];
  currentConcurrency: number;
  availableConcurrency: number;
  capacityStatus: string;
  recentCallCount: number;
  recentFailureRate: number;
  recentAverageLatencyMs: number;
  lastStatus?: string | null;
  lastLatencyMs?: number | null;
  lastError?: string | null;
  lastCheckedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ApiCredentialCapability {
  capability: string;
  label: string;
  status: 'ok' | 'failed' | 'unknown';
  lastTask?: string | null;
  durationMs?: number | null;
  errorSummary?: string | null;
  checkedAt?: string | null;
}

export interface ApiProviderGroup {
  providerGroup: string;
  credentialCount: number;
  activeCredentialCount: number;
  autoAssignCredentialCount: number;
  currentConcurrency: number;
  recentCallCount: number;
  recentFailureRate: number;
  recentTimeoutCount: number;
  status: 'ok' | 'watch' | 'degraded';
  recommendation?: string | null;
}

export interface ApiCredentialCreate {
  label: string;
  providerType?: string;
  baseUrl: string;
  modelName: string;
  apiKey: string;
  taskScope?: ModelTaskName[];
  status?: 'active' | 'disabled';
  priority?: number;
  timeoutSeconds?: number;
  temperature?: number;
  temperatureEnabled?: boolean;
  maxConcurrency?: number;
  autoAssignEnabled?: boolean;
}

export interface ApiCredentialUpdate {
  label?: string;
  providerType?: string;
  baseUrl?: string;
  modelName?: string;
  apiKey?: string;
  taskScope?: ModelTaskName[];
  status?: 'active' | 'disabled';
  priority?: number;
  timeoutSeconds?: number;
  temperature?: number;
  temperatureEnabled?: boolean;
  maxConcurrency?: number;
  autoAssignEnabled?: boolean;
}

export interface AssetAgentChatRequest {
  message: string;
  imageIds?: string[];
  assetGroupIds?: string[];
  conversationId?: string | null;
}

export interface AssetAgentImageContext {
  imageId: string;
  assetGroupId?: string | null;
  title: string;
}

export interface AssetAgentMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  usedModel?: boolean | null;
  createdAt: string;
}

export interface AssetAgentSession {
  id: string;
  title: string;
  messages: AssetAgentMessage[];
  contextImages: AssetAgentImageContext[];
  suggestedQuestions: string[];
  expiresAt: string;
  createdAt: string;
  updatedAt: string;
}

export interface AssetAgentSessionListResponse {
  sessions: AssetAgentSession[];
}

export interface AssetAgentSessionCreateRequest {
  title?: string | null;
  contextImages?: AssetAgentImageContext[];
}

export interface AssetAgentSessionContextUpdateRequest {
  contextImages: AssetAgentImageContext[];
}

export interface AssetAgentContextCard {
  kind: 'image' | 'asset_group' | 'concept';
  id: string;
  title: string;
  subtitle?: string | null;
  facts: string[];
}

export interface AssetAgentChatResponse {
  answer: string;
  conversationId?: string | null;
  session?: AssetAgentSession | null;
  suggestedQuestions: string[];
  contextCards: AssetAgentContextCard[];
  usedModel: boolean;
  providerAttempts: Record<string, unknown>[];
}

export interface RoutingSlot {
  id: string;
  task: string;
  label: string;
  primaryCredentialId?: string | null;
  primaryCredentialLabel?: string | null;
  backupCredentialIds: string[];
  backupCredentialLabels: string[];
  excludedCredentialIds: string[];
  excludedCredentialLabels: string[];
  timeoutSeconds: number;
  hedgingDelayMs: number;
  maxParallel: number;
  autoSelectEnabled: boolean;
  notes?: string | null;
  updatedAt: string;
}

export interface RoutingSlotUpdate {
  label?: string;
  primaryCredentialId?: string | null;
  backupCredentialIds?: string[];
  excludedCredentialIds?: string[];
  timeoutSeconds?: number;
  hedgingDelayMs?: number;
  maxParallel?: number;
  autoSelectEnabled?: boolean;
  notes?: string | null;
}

export interface ApiExternalKnowledgeServiceConfig {
  enabled: boolean;
  baseUrl: string;
  serviceResourceId: string;
  apiKeyConfigured: boolean;
  timeoutSeconds: number;
  resultLimit: number;
  maxMatches: number;
}

export interface ApiExternalVectorDatabaseConfig {
  enabled: boolean;
  fallbackEnabled: boolean;
  baseUrl: string;
  collectionName: string;
  indexName: string;
  apiKeyConfigured: boolean;
  timeoutSeconds: number;
  searchLimit: number;
  primaryMinScore: number;
  primaryMaxMatches: number;
  fallbackMinScore: number;
  fallbackMaxMatches: number;
}

export interface ApiExternalConnections {
  knowledgeService: ApiExternalKnowledgeServiceConfig;
  vectorDatabase: ApiExternalVectorDatabaseConfig;
}

export interface ApiExternalKnowledgeServiceUpdate {
  enabled?: boolean;
  baseUrl?: string;
  serviceResourceId?: string;
  apiKey?: string;
  timeoutSeconds?: number;
  resultLimit?: number;
  maxMatches?: number;
}

export interface ApiExternalVectorDatabaseUpdate {
  enabled?: boolean;
  fallbackEnabled?: boolean;
  baseUrl?: string;
  collectionName?: string;
  indexName?: string;
  apiKey?: string;
  timeoutSeconds?: number;
  searchLimit?: number;
  primaryMinScore?: number;
  primaryMaxMatches?: number;
  fallbackMinScore?: number;
  fallbackMaxMatches?: number;
}

export interface ApiExternalConnectionTestResult {
  status: 'ok' | 'failed' | 'skipped';
  durationMs: number;
  message: string;
  preview: Record<string, unknown>;
}

export interface ApiSearchChainDiagnosticStep {
  name: string;
  status: 'ok' | 'failed' | 'skipped';
  durationMs: number;
  message: string;
  preview: Record<string, unknown>;
}

export interface ApiSearchChainDiagnosticResult {
  status: 'ok' | 'degraded' | 'failed' | 'skipped';
  query: string;
  durationMs: number;
  steps: ApiSearchChainDiagnosticStep[];
  matchedConcepts: string[];
  resultCount: number;
  fallback: boolean;
  fallbackReason?: string | null;
}

export interface ApiHealthCheck {
  id: string;
  credentialId: string;
  credentialLabel?: string | null;
  task: string;
  status: string;
  durationMs: number;
  errorCode?: string | null;
  errorCategory?: string | null;
  errorSeverity?: string | null;
  errorRetryable?: boolean | null;
  errorOperatorAction?: string | null;
  errorSystemAction?: string | null;
  errorSummary?: string | null;
  checkedAt: string;
}

export interface ApiHealthCheckRunRequest {
  task?: ModelTaskName | null;
  includeDisabled?: boolean;
  timeoutSeconds?: number | null;
}

export interface ApiHealthCheckRunResult {
  checkedCount: number;
  okCount: number;
  failedCount: number;
  checks: ApiHealthCheck[];
}

export interface ApiTemperatureProbe {
  temperature?: number | null;
  temperatureEnabled: boolean;
  status: string;
  durationMs: number;
  errorCode?: string | null;
  errorCategory?: string | null;
  errorSeverity?: string | null;
  errorRetryable?: boolean | null;
  errorOperatorAction?: string | null;
  errorSystemAction?: string | null;
  errorSummary?: string | null;
  checkedAt: string;
}

export interface ApiTemperatureTuneRequest {
  task?: ModelTaskName | null;
  candidateTemperatures?: number[] | null;
  timeoutSeconds?: number | null;
  persist?: boolean;
}

export interface ApiTemperatureProbeRequest {
  baseUrl: string;
  modelName: string;
  apiKey: string;
  task?: ModelTaskName;
  temperature?: number;
  candidateTemperatures?: number[] | null;
  timeoutSeconds?: number | null;
}

export interface ApiTemperatureTuneResult {
  credentialId: string;
  credentialLabel?: string | null;
  status: string;
  previousTemperature: number;
  previousTemperatureEnabled: boolean;
  selectedTemperature?: number | null;
  selectedTemperatureEnabled?: boolean | null;
  probes: ApiTemperatureProbe[];
}

export interface ApiCallTrace {
  id: string;
  searchLogId?: string | null;
  requestId?: string | null;
  searchKeyword?: string | null;
  searchResultCount?: number | null;
  searchTimedOut?: boolean | null;
  task: string;
  layerName: string;
  credentialId?: string | null;
  credentialLabel?: string | null;
  provider: string;
  model: string;
  status: string;
  durationMs: number;
  fallbackIndex?: number | null;
  errorCode?: string | null;
  errorCategory?: string | null;
  errorSeverity?: string | null;
  errorRetryable?: boolean | null;
  errorOperatorAction?: string | null;
  errorSystemAction?: string | null;
  errorSummary?: string | null;
  responseValid?: boolean | null;
  outputSummary: Record<string, unknown>;
  createdAt: string;
}

export interface ApiCallTraceListParams {
  limit?: number;
  offset?: number;
  task?: string;
  status?: string;
  provider?: string;
  credentialId?: string;
  requestId?: string;
  keyword?: string;
}

export interface ApiCallTraceListResponse {
  items: ApiCallTrace[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

export interface ApiCenterOverview {
  credentialCount: number;
  activeCredentialCount: number;
  healthyCredentialCount: number;
  degradedCredentialCount: number;
  configuredSlotCount: number;
  recentCallCount: number;
  recentFailureCount: number;
  p95LatencyMs: number;
}

export interface ApiCenterMaintenance {
  enabled: boolean;
  intervalMinutes: number;
  startupDelaySeconds: number;
  maxCredentialsPerCycle: number;
  callTraceRetentionDays: number;
  healthCheckRetentionDays: number;
  lastStartedAt?: string | null;
  lastFinishedAt?: string | null;
  lastStatus: string;
  lastError?: string | null;
  lastCheckedCount: number;
  lastOkCount: number;
  lastFailedCount: number;
  lastDeletedCallTraceCount: number;
  lastDeletedHealthCheckCount: number;
  nextRunAt?: string | null;
}

export interface ApiCenterMaintenanceRunResult {
  status: string;
  startedAt: string;
  finishedAt: string;
  checkedCount: number;
  okCount: number;
  failedCount: number;
  deletedCallTraceCount: number;
  deletedHealthCheckCount: number;
}

export interface ApiCenterSummary {
  overview: ApiCenterOverview;
  maintenance: ApiCenterMaintenance;
  externalConnections: ApiExternalConnections;
  credentials: ApiCredential[];
  providerGroups: ApiProviderGroup[];
  routingSlots: RoutingSlot[];
  recentCallTraces: ApiCallTrace[];
}
