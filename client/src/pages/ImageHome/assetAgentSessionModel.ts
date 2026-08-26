import type {
  AssetAgentChatResponse,
  AssetAgentImageContext,
  AssetAgentSession as ApiAssetAgentSession,
} from '@client/src/types/api';
import type { AssetAgentImagePayload } from '@client/src/features/assets/assetAgentEvents';

export type ChatRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  usedModel?: boolean | null;
}

export interface AgentSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  contextImages: AssetAgentImagePayload[];
  suggestedQuestions: string[];
  createdAt: number;
  updatedAt: number;
  expiresAt: number;
}

export interface AgentState {
  sessions: AgentSession[];
  activeSessionId: string;
}

export const DEFAULT_QUESTIONS = [
  '这张图适合讲哪个卖点？',
  '帮我用家长能听懂的话解释',
  '它和相近卖点的区别是什么？',
] as const;

export const MAX_SESSIONS = 20;
export const SESSION_TTL_MS = 24 * 60 * 60 * 1000;
export const LOCAL_SESSION_PREFIX = 'local-';
export const DEFAULT_GREETING =
  '我是素材库 Agent。你可以把图片发给我，我会按已确认的卖点和素材信息帮你解释。';

export function responseMessage(response: AssetAgentChatResponse): ChatMessage {
  const suffix = response.usedModel ? '' : '\n\n（本次模型不可用，已走本地兜底。）';
  return {
    id: safeId(),
    role: 'assistant',
    content: `${response.answer}${suffix}`,
    usedModel: response.usedModel,
  };
}

export function createLocalSession(message = DEFAULT_GREETING): AgentSession {
  const now = Date.now();
  return {
    id: `${LOCAL_SESSION_PREFIX}${safeId()}`,
    title: '新对话',
    messages: [
      {
        id: safeId(),
        role: 'assistant',
        content: message,
      },
    ],
    contextImages: [],
    suggestedQuestions: [...DEFAULT_QUESTIONS],
    createdAt: now,
    updatedAt: now,
    expiresAt: now + SESSION_TTL_MS,
  };
}

export function sessionFromApi(session: ApiAssetAgentSession): AgentSession {
  return {
    id: session.id,
    title: session.title || '历史对话',
    messages: session.messages.map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      usedModel: message.usedModel,
    })),
    contextImages: session.contextImages.map(contextApiToPayload),
    suggestedQuestions: session.suggestedQuestions.length > 0
      ? session.suggestedQuestions
      : [...DEFAULT_QUESTIONS],
    createdAt: dateToMillis(session.createdAt),
    updatedAt: dateToMillis(session.updatedAt),
    expiresAt: dateToMillis(session.expiresAt),
  };
}

export function stateFromSessions(
  sessions: AgentSession[],
  activeSessionId?: string,
): AgentState {
  const normalized = sessions
    .filter((session) => session.messages.length > 0)
    .sort((left, right) => right.updatedAt - left.updatedAt)
    .slice(0, MAX_SESSIONS);
  const fallback = normalized.length > 0 ? normalized : [createLocalSession()];
  return {
    sessions: fallback,
    activeSessionId: activeSessionId && fallback.some((item) => item.id === activeSessionId)
      ? activeSessionId
      : fallback[0].id,
  };
}

export function upsertSession(
  state: AgentState,
  session: AgentSession,
  activeSessionId = session.id,
): AgentState {
  const sessions = [
    session,
    ...state.sessions.filter((item) => item.id !== session.id && !isLocalSession(item.id)),
  ]
    .sort((left, right) => right.updatedAt - left.updatedAt)
    .slice(0, MAX_SESSIONS);
  return stateFromSessions(sessions, activeSessionId);
}

export function updateSession(
  state: AgentState,
  sessionId: string,
  updater: (session: AgentSession) => AgentSession,
): AgentState {
  const sessions = state.sessions
    .map((session) => (session.id === sessionId ? updater(session) : session))
    .sort((left, right) => right.updatedAt - left.updatedAt)
    .slice(0, MAX_SESSIONS);
  return { ...state, sessions };
}

export function contextPayloadToApi(
  payload: AssetAgentImagePayload,
): AssetAgentImageContext {
  return {
    imageId: payload.imageId,
    assetGroupId: payload.assetGroupId ?? null,
    title: payload.title,
  };
}

export function contextApiToPayload(
  value: AssetAgentImageContext,
): AssetAgentImagePayload {
  return {
    imageId: value.imageId,
    assetGroupId: value.assetGroupId ?? null,
    title: value.title,
  };
}

export function titleFromMessage(message: string): string {
  const cleaned = message.replace(/\s+/g, ' ').trim();
  return cleaned.length > 16 ? `${cleaned.slice(0, 16)}…` : cleaned || '新对话';
}

export function formatSessionTime(value: number): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '刚刚';
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatExpiry(value: number): string {
  const remainingMs = Math.max(0, value - Date.now());
  const hours = Math.ceil(remainingMs / (60 * 60 * 1000));
  if (hours <= 1) return '1 小时内';
  return `${hours} 小时`;
}

export function isLocalSession(sessionId: string): boolean {
  return sessionId.startsWith(LOCAL_SESSION_PREFIX);
}

export function safeId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function dateToMillis(value: string): number {
  const parsed = new Date(value).getTime();
  return Number.isFinite(parsed) ? parsed : Date.now();
}
