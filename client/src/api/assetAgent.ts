import { api } from './client';

import type {
  AssetAgentChatRequest,
  AssetAgentChatResponse,
  AssetAgentSession,
  AssetAgentSessionContextUpdateRequest,
  AssetAgentSessionCreateRequest,
  AssetAgentSessionListResponse,
} from '@client/src/types/api';

type AssetAgentStreamEvent =
  | { type: 'reasoning_delta'; text: string }
  | { type: 'answer_delta'; text: string }
  | { type: 'final'; response: AssetAgentChatResponse }
  | { type: 'error'; message: string };

function readCookie(name: string): string | undefined {
  const prefix = `${name}=`;
  return document.cookie
    .split(';')
    .map((value) => value.trim())
    .find((value) => value.startsWith(prefix))
    ?.slice(prefix.length);
}

function apiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || '';
}

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

export async function streamAssetAgentMessage(
  sessionId: string,
  payload: AssetAgentChatRequest,
  onEvent: (event: AssetAgentStreamEvent) => void,
): Promise<void> {
  const csrf = readCookie('piancton_csrf');
  const response = await fetch(
    `${apiBaseUrl()}/api/asset-agent/sessions/${sessionId}/messages/stream`,
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrf ? { 'X-CSRF-Token': decodeURIComponent(csrf) } : {}),
      },
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) {
    let message = 'Piancton Agent 流式请求失败';
    try {
      const body = await response.json();
      if (body && typeof body.message === 'string') message = body.message;
    } catch {
      // keep stable fallback message
    }
    throw new Error(message);
  }
  const reader = response.body?.getReader();
  if (!reader) throw new Error('浏览器暂不支持流式读取');
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split('\n\n');
    buffer = frames.pop() ?? '';
    for (const frame of frames) {
      const event = parseSseFrame(frame);
      if (event) onEvent(event);
    }
  }
  const trailing = parseSseFrame(buffer);
  if (trailing) onEvent(trailing);
}

export async function chatWithAssetAgent(
  payload: AssetAgentChatRequest,
): Promise<AssetAgentChatResponse> {
  return (
    await api.post('/api/asset-agent/chat', payload, { timeout: 60_000 })
  ).data;
}

function parseSseFrame(frame: string): AssetAgentStreamEvent | null {
  const eventLine = frame.split('\n').find((line) => line.startsWith('event:'));
  const dataLine = frame.split('\n').find((line) => line.startsWith('data:'));
  const eventName = eventLine?.slice('event:'.length).trim();
  const rawData = dataLine?.slice('data:'.length).trim();
  if (!eventName || !rawData) return null;
  let payload: unknown;
  try {
    payload = JSON.parse(rawData);
  } catch {
    return null;
  }
  if (!payload || typeof payload !== 'object') return null;
  const data = payload as Record<string, unknown>;
  if (eventName === 'reasoning_delta' && typeof data.text === 'string') {
    return { type: 'reasoning_delta', text: data.text };
  }
  if (eventName === 'answer_delta' && typeof data.text === 'string') {
    return { type: 'answer_delta', text: data.text };
  }
  if (eventName === 'final') {
    return { type: 'final', response: data as unknown as AssetAgentChatResponse };
  }
  if (eventName === 'error' && typeof data.message === 'string') {
    return { type: 'error', message: data.message };
  }
  return null;
}
