import { api } from './client';

import type {
  AssetAgentChatRequest,
  AssetAgentChatResponse,
  AssetAgentSession,
  AssetAgentSessionContextUpdateRequest,
  AssetAgentSessionCreateRequest,
  AssetAgentSessionListResponse,
} from '@client/src/types/api';

export async function listAssetAgentSessions(): Promise<AssetAgentSessionListResponse> {
  return (await api.get('/api/asset-agent/sessions')).data;
}

export async function createAssetAgentSession(
  payload: AssetAgentSessionCreateRequest = {},
): Promise<AssetAgentSession> {
  return (await api.post('/api/asset-agent/sessions', payload)).data;
}

export async function updateAssetAgentSessionContext(
  sessionId: string,
  payload: AssetAgentSessionContextUpdateRequest,
): Promise<AssetAgentSession> {
  return (await api.patch(`/api/asset-agent/sessions/${sessionId}/context`, payload)).data;
}

export async function deleteAssetAgentSession(sessionId: string): Promise<void> {
  await api.delete(`/api/asset-agent/sessions/${sessionId}`);
}

export async function sendAssetAgentMessage(
  sessionId: string,
  payload: AssetAgentChatRequest,
): Promise<AssetAgentChatResponse> {
  return (
    await api.post(`/api/asset-agent/sessions/${sessionId}/messages`, payload, {
      timeout: 60_000,
    })
  ).data;
}

export async function chatWithAssetAgent(
  payload: AssetAgentChatRequest,
): Promise<AssetAgentChatResponse> {
  return (
    await api.post('/api/asset-agent/chat', payload, { timeout: 60_000 })
  ).data;
}
