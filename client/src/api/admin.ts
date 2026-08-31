import { api } from './client';
import {
  apiCenterRequestWaitMs,
  HEALTH_CHECK_PARALLELISM,
  HEALTH_PROBE_ATTEMPTS,
  HEALTH_PROBE_LIMIT_SECONDS,
  NEW_API_PROBE_LIMIT_SECONDS,
} from './apiCenterWaitPolicy';
import type {
  ApiCallTraceListParams,
  ApiCallTraceListResponse,
  ApiCenterMaintenanceRunResult,
  ApiCenterSummary,
  ApiCredential,
  ApiCredentialCreate,
  ApiCredentialUpdate,
  ApiHealthCheck,
  ApiHealthCheckRunRequest,
  ApiHealthCheckRunResult,
  ApiTemperatureProbeRequest,
  ApiTemperatureTuneRequest,
  ApiTemperatureTuneResult,
  ApiProviderGroup,
  AssetIdentityCodeListResponse,
  ModelTaskName,
  RoutingSlot,
  RoutingSlotUpdate,
  AuditLog,
  SearchOpsSummary,
  UsageAnalyticsSummary,
  User,
  UserRole,
} from '@client/src/types/api';


export async function fetchUsers(): Promise<User[]> {
  return (await api.get('/api/admin/users')).data;
}

export async function createUser(data: {
  username: string;
  password: string;
  role: UserRole;
}): Promise<User> {
  return (await api.post('/api/admin/users', data)).data;
}

export async function updateUser(
  id: string,
  data: { role?: UserRole; isActive?: boolean },
): Promise<User> {
  return (await api.patch(`/api/admin/users/${id}`, data)).data;
}

export async function resetPassword(id: string, password: string): Promise<void> {
  await api.post(`/api/admin/users/${id}/reset-password`, { password });
}

export async function fetchAuditLogs(): Promise<AuditLog[]> {
  return (await api.get('/api/admin/users/audit-logs')).data;
}

export async function fetchSearchOpsSummary(days = 7): Promise<SearchOpsSummary> {
  return (await api.get('/api/admin/search-ops/summary', { params: { days } })).data;
}

export async function fetchUsageAnalyticsSummary(
  days = 7,
): Promise<UsageAnalyticsSummary> {
  return (await api.get('/api/admin/usage/summary', { params: { days } })).data;
}

export async function fetchApiCenterSummary(): Promise<ApiCenterSummary> {
  return (await api.get('/api/admin/api-center/summary')).data;
}

export async function fetchApiCallTraces(
  params: ApiCallTraceListParams = {},
): Promise<ApiCallTraceListResponse> {
  return (
    await api.get('/api/admin/api-center/call-traces', {
      params: {
        limit: params.limit,
        offset: params.offset,
        task: params.task || undefined,
        status: params.status || undefined,
        provider: params.provider || undefined,
        credential_id: params.credentialId || undefined,
        request_id: params.requestId || undefined,
        keyword: params.keyword || undefined,
      },
    })
  ).data;
}

export async function createApiCredential(payload: ApiCredentialCreate): Promise<ApiCredential> {
  return (await api.post('/api/admin/api-center/credentials', payload)).data;
}

export async function updateApiCredential(
  id: string,
  payload: ApiCredentialUpdate,
): Promise<ApiCredential> {
  return (await api.patch(`/api/admin/api-center/credentials/${id}`, payload)).data;
}

export async function deleteApiCredential(id: string): Promise<void> {
  await api.delete(`/api/admin/api-center/credentials/${id}`);
}

export async function disableApiProviderGroup(providerGroup: string): Promise<ApiProviderGroup> {
  return (
    await api.post(
      `/api/admin/api-center/provider-groups/${encodeURIComponent(providerGroup)}/disable`,
    )
  ).data;
}

export async function probeApiCredentialTemperature(
  payload: ApiTemperatureProbeRequest,
): Promise<ApiTemperatureTuneResult> {
  const perProbeTimeoutSeconds = Math.min(
    Math.max(payload.timeoutSeconds ?? 20, 0.5),
    NEW_API_PROBE_LIMIT_SECONDS,
  );
  const candidateCount = Math.min(
    Math.max((payload.candidateTemperatures?.length ?? 5) + 1, 1),
    6,
  );
  return (
    await api.post('/api/admin/api-center/credentials/temperature-probe', payload, {
      timeout: apiCenterRequestWaitMs(perProbeTimeoutSeconds, candidateCount),
    })
  ).data;
}

export async function testApiCredential(
  id: string,
  task: ModelTaskName = 'search_system_routing',
): Promise<ApiHealthCheck> {
  return (
    await api.post(`/api/admin/api-center/credentials/${id}/test`, { task }, {
      timeout: apiCenterRequestWaitMs(
        HEALTH_PROBE_LIMIT_SECONDS,
        HEALTH_PROBE_ATTEMPTS,
      ),
    })
  ).data;
}

export async function tuneApiCredentialTemperature(
  id: string,
  payload: ApiTemperatureTuneRequest = {},
): Promise<ApiTemperatureTuneResult> {
  return (await api.post(
    `/api/admin/api-center/credentials/${id}/temperature-tune`,
    payload,
  )).data;
}

export async function runApiHealthChecks(
  payload: ApiHealthCheckRunRequest = {},
  expectedCredentialCount = 1,
): Promise<ApiHealthCheckRunResult> {
  return (
    await api.post('/api/admin/api-center/health-checks/run-all', payload, {
      timeout: apiCenterRequestWaitMs(
        HEALTH_PROBE_LIMIT_SECONDS,
        expectedCredentialCount * HEALTH_PROBE_ATTEMPTS,
        HEALTH_CHECK_PARALLELISM,
      ),
    })
  ).data;
}

export async function runApiCenterMaintenance(
  expectedCredentialCount = 1,
): Promise<ApiCenterMaintenanceRunResult> {
  return (
    await api.post('/api/admin/api-center/maintenance/run', {}, {
      timeout: apiCenterRequestWaitMs(
        HEALTH_PROBE_LIMIT_SECONDS,
        expectedCredentialCount * HEALTH_PROBE_ATTEMPTS,
        HEALTH_CHECK_PARALLELISM,
      ),
    })
  ).data;
}

export async function updateRoutingSlot(
  task: string,
  payload: RoutingSlotUpdate,
): Promise<RoutingSlot> {
  return (await api.patch(`/api/admin/api-center/routing-slots/${task}`, payload)).data;
}

export async function fetchIdentityCodes(params: {
  q?: string;
  codeType?: 'all' | 'asset' | 'version';
  status?: 'all' | 'active' | 'deleted' | 'retired';
  page?: number;
  pageSize?: number;
} = {}): Promise<AssetIdentityCodeListResponse> {
  return (await api.get('/api/admin/identity-codes', { params })).data;
}
