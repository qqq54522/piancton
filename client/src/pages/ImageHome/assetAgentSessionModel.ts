import type {
  AssetAgentChatResponse,
  AssetAgentContextCard,
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
  reasoningContent?: string;
  streaming?: boolean;
  contextCards?: AssetAgentContextCard[];
}

export interface AgentSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  contextImages: AssetAgentImagePayload[];
  suggestedQuestions: string[];
  createdAt: number;
  updatedAt: number;
  memoryUsedChars: number;
  memoryLimitChars: number;
  memoryUsageRatio: number;
}

export interface AgentState {
  sessions: AgentSession[];
  activeSessionId: string;
}

export const DEFAULT_QUESTIONS = [
  '洋葱的六大体系是什么？',
  '帮我把这段介绍写得更清楚',
  '帮我找几张适合做 PPT 的素材',
  '我发一张图，你帮我看看它讲了什么',
] as const;

export const MAX_SESSIONS = 20;
export const DEFAULT_MEMORY_LIMIT_CHARS = 12_000;
export const MEMORY_MESSAGE_LIMIT = 24;
export const MEMORY_MESSAGE_CHAR_LIMIT = 1_200;
export const LOCAL_SESSION_PREFIX = 'local-';
export const DEFAULT_GREETING =
  'Hi，我是洋葱 Agent。你可以像和普通助手聊天一样直接提问。聊到洋葱的产品、业务体系或素材时，我会结合洋葱知识与素材库回答；其他问题也可以直接问我。';

const LEGACY_DEFAULT_GREETING =
  '我是素材库 Agent。你可以把图片发给我，我会按已确认的卖点和素材信息帮你解释。';
const LEGACY_PIANCTON_DEFAULT_GREETING =
  '我是 Piancton Agent。你可以问我图片、卖点、六大体系、素材使用和销售话术；如果把图片发给我，我会结合已确认的素材信息一起回答。';
const LEGACY_BUSINESS_DEFAULT_GREETING =
  'Hi，我是洋葱业务知识助手。你可以问我业务体系、核心卖点、证明点、家长沟通和素材方向；把图片发给我，我会结合图片和知识库判断它适合表达什么卖点。';
const LEGACY_DEFAULT_QUESTIONS = [
  '这张图适合讲哪个卖点？',
  '帮我用家长能听懂的话解释',
  '它和相近卖点的区别是什么？',
] as const;
const LEGACY_DEFAULT_QUESTIONS_WITHOUT_CONTEXT = [
  '什么是同步校内？',
  '什么是 AI 拍题精学？',
  '哪些图适合讲考前突击？',
] as const;

export function responseMessage(response: AssetAgentChatResponse): ChatMessage {
  return {
    id: safeId(),
    role: 'assistant',
    content: normalizeAgentText(response.answer),
    usedModel: response.usedModel,
    contextCards: response.contextCards,
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
    memoryUsedChars: 0,
    memoryLimitChars: DEFAULT_MEMORY_LIMIT_CHARS,
    memoryUsageRatio: 0,
  };
}

export function sessionFromApi(session: ApiAssetAgentSession): AgentSession {
  const messages = session.messages.map((message) => ({
    id: message.id,
    role: message.role,
    content: normalizeLegacyDefaultMessage(normalizeAgentText(message.content)),
    usedModel: message.usedModel,
    contextCards: message.contextCards ?? [],
  }));
  const memoryLimitChars = positiveNumber(
    session.memoryLimitChars,
    DEFAULT_MEMORY_LIMIT_CHARS,
  );
  const localMemory = conversationMemoryUsage(messages, memoryLimitChars);
  return {
    id: session.id,
    title: session.title || '历史对话',
    messages,
    contextImages: session.contextImages.map(contextApiToPayload),
    suggestedQuestions: normalizedSuggestedQuestions(session.suggestedQuestions).length > 0
      ? normalizedSuggestedQuestions(session.suggestedQuestions)
      : [...DEFAULT_QUESTIONS],
    createdAt: dateToMillis(session.createdAt),
    updatedAt: dateToMillis(session.updatedAt),
    memoryUsedChars: nonNegativeNumber(session.memoryUsedChars, localMemory.usedChars),
    memoryLimitChars,
    memoryUsageRatio: boundedRatio(session.memoryUsageRatio, localMemory.ratio),
  };
}

export function conversationMemoryUsage(
  messages: ChatMessage[],
  limitChars = DEFAULT_MEMORY_LIMIT_CHARS,
): { usedChars: number; ratio: number } {
  const eligible = messages.filter((message) => (
    (message.role === 'user' || message.role === 'assistant') && message.content.trim()
  ));
  const firstUserIndex = eligible.findIndex((message) => message.role === 'user');
  if (firstUserIndex < 0) return { usedChars: 0, ratio: 0 };

  const lines = eligible.slice(firstUserIndex).map((message) => {
    const clipped = message.content.length > MEMORY_MESSAGE_CHAR_LIMIT
      ? `${message.content.slice(0, MEMORY_MESSAGE_CHAR_LIMIT - 1)}…`
      : message.content;
    return `${message.role === 'user' ? '用户' : '助手'}：${clipped}`;
  });
  const normalizedLimit = positiveNumber(limitChars, DEFAULT_MEMORY_LIMIT_CHARS);
  const rawChars = lines.length > MEMORY_MESSAGE_LIMIT
    ? normalizedLimit
    : lines.reduce((total, line) => total + line.length, Math.max(0, lines.length - 1));
  const usedChars = Math.min(rawChars, normalizedLimit);
  return {
    usedChars,
    ratio: usedChars / normalizedLimit,
  };
}

function normalizeLegacyDefaultMessage(content: string): string {
  return (
    content === LEGACY_DEFAULT_GREETING
    || content === LEGACY_PIANCTON_DEFAULT_GREETING
    || content === LEGACY_BUSINESS_DEFAULT_GREETING
    || content.startsWith('Hi，我是洋葱业务知识助手。\n\n我可以帮你理解洋葱学园')
  )
    ? DEFAULT_GREETING
    : content;
}

export function normalizeAgentText(content: string): string {
  return content
    .replace(/\\r\\n/g, '\n')
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '  ');
}

export function shouldSendAgentMessage(event: {
  key: string;
  metaKey: boolean;
  ctrlKey: boolean;
}): boolean {
  return event.key === 'Enter' && (event.metaKey || event.ctrlKey);
}

function normalizedSuggestedQuestions(questions: string[]): string[] {
  if (
    questions.length === LEGACY_DEFAULT_QUESTIONS.length
    && questions.every((question, index) => question === LEGACY_DEFAULT_QUESTIONS[index])
  ) {
    return [...DEFAULT_QUESTIONS];
  }
  if (
    questions.length === LEGACY_DEFAULT_QUESTIONS_WITHOUT_CONTEXT.length
    && questions.every((question, index) => (
      question === LEGACY_DEFAULT_QUESTIONS_WITHOUT_CONTEXT[index]
    ))
  ) {
    return [...DEFAULT_QUESTIONS];
  }
  return questions;
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
    imageUrl: payload.imageUrl ?? null,
  };
}

export function contextApiToPayload(
  value: AssetAgentImageContext,
): AssetAgentImagePayload {
  return {
    imageId: value.imageId,
    assetGroupId: value.assetGroupId ?? null,
    title: value.title,
    imageUrl: value.imageUrl ?? null,
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

function positiveNumber(value: number | undefined, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : fallback;
}

function nonNegativeNumber(value: number | undefined, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : fallback;
}

function boundedRatio(value: number | undefined, fallback: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return fallback;
  return Math.max(0, Math.min(1, value));
}
