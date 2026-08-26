import { api } from './client';
import type {
  ApiCenterSummary,
  ApiCredential,
  ApiCredentialCreate,
  ApiCredentialUpdate,
  ApiHealthCheck,
  ApiHealthCheckRunRequest,
  ApiHealthCheckRunResult,
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

export async function testApiCredential(
  id: string,
  task: ModelTaskName = 'search_system_routing',
): Promise<ApiHealthCheck> {
  return (await api.post(`/api/admin/api-center/credentials/${id}/test`, { task })).data;
}

export async function runApiHealthChecks(
  payload: ApiHealthCheckRunRequest = {},
): Promise<ApiHealthCheckRunResult> {
  return (await api.post('/api/admin/api-center/health-checks/run-all', payload)).data;
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
