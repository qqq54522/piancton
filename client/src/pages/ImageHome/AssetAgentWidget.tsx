import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  Image as ImageIcon,
  Loader2,
  MessageSquare,
  Plus,
  Send,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react';

import {
  createAssetAgentSession,
  deleteAssetAgentSession,
  listAssetAgentSessions,
  sendAssetAgentMessage,
  updateAssetAgentSessionContext,
} from '@client/src/api/assetAgent';
import { getApiError } from '@client/src/api/client';
import { PianctonAgentMark } from '@client/src/components/PianctonAgentMark';
import { Button } from '@client/src/components/ui/button';
import {
  listenForAssetAgentImages,
  type AssetAgentImagePayload,
} from '@client/src/features/assets/assetAgentEvents';
import { clearLegacyAssetAgentStorage } from '@client/src/features/assets/assetAgentStorage';
import { useAuth } from '@client/src/lib/auth';
import type { AssetAgentSession as ApiAssetAgentSession } from '@client/src/types/api';
import {
  contextPayloadToApi,
  createLocalSession,
  DEFAULT_QUESTIONS,
  formatExpiry,
  formatSessionTime,
  isLocalSession,
  responseMessage,
  safeId,
  sessionFromApi,
  stateFromSessions,
  titleFromMessage,
  updateSession,
  upsertSession,
  type AgentSession,
  type AgentState,
} from './assetAgentSessionModel';

const GREETING_LINES = [
  ['Hello，我在这里', '哪张图拿不准，可以来问我。'],
  ['你来了，我也醒着', '想知道图片卖点，就丢给我。'],
  ['有图不确定？', '我帮你把卖点和家长话术讲清楚。'],
  ['今天想找哪张图？', '我可以先帮你读一遍素材。'],
] as const;

const AssetAgentWidget = () => {
  const { user } = useAuth();
  if (!user) return null;

  return <AssetAgentWidgetInner key={user.id} />;
};

function AssetAgentWidgetInner() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [initialLoading, setInitialLoading] = useState(true);
  const [loadingSessionId, setLoadingSessionId] = useState<string | null>(null);
  const [sessionMenuOpen, setSessionMenuOpen] = useState(false);
  const [state, setState] = useState<AgentState>(() => stateFromSessions([createLocalSession()]));
  const sessionMenuRef = useRef<HTMLDivElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const [markState, setMarkState] = useState<'idle' | 'thinking' | 'happy' | 'wake'>('idle');
  const activeSession = useMemo(
    () => state.sessions.find((session) => session.id === state.activeSessionId)
      ?? state.sessions[0],
    [state.activeSessionId, state.sessions],
  );
  const activeSessionRef = useRef<AgentSession | null>(activeSession);
  const loading = Boolean(activeSession && loadingSessionId === activeSession.id);
  const orbState = loading ? 'thinking' : markState;
  const persistedSessionCount = state.sessions.filter((session) => !isLocalSession(session.id)).length;
  const sessionCount = persistedSessionCount || state.sessions.length;
  const isTemporarySession = isLocalSession(activeSession.id);
  const activeSessionId = activeSession.id;
  const activeMessageCount = activeSession.messages.length;

  const pushAssistantError = useCallback((message: string, sessionId?: string) => {
    const targetId = sessionId ?? activeSessionRef.current?.id;
    if (!targetId) return;
    setState((current) => updateSession(current, targetId, (session) => ({
      ...session,
      messages: [
        ...session.messages,
        {
          id: safeId(),
          role: 'assistant',
          content: `这次没处理成功：${message}`,
          usedModel: false,
        },
      ],
      updatedAt: Date.now(),
    })));
  }, []);

  const ensureServerSession = useCallback(async (
    contextImages?: AssetAgentImagePayload[],
  ): Promise<AgentSession> => {
    const current = activeSessionRef.current;
    const nextContext = contextImages ?? current?.contextImages ?? [];
    if (current && !isLocalSession(current.id)) return current;

    const created = await createAssetAgentSession({
      contextImages: nextContext.map(contextPayloadToApi),
    });
    const normalized = sessionFromApi(created);
    setState((existing) => upsertSession(existing, normalized, normalized.id));
    return normalized;
  }, []);

  const addImageToSession = useCallback(async (image: AssetAgentImagePayload) => {
    setOpen(true);
    const current = activeSessionRef.current;
    const contextImages = current?.contextImages ?? [];
    if (contextImages.some((item) => item.imageId === image.imageId)) return;

    const nextContext = [...contextImages, image].slice(-8);
    if (!current || isLocalSession(current.id)) {
      try {
        const created = await createAssetAgentSession({
          contextImages: nextContext.map(contextPayloadToApi),
        });
        setState((existing) => upsertSession(existing, sessionFromApi(created), created.id));
      } catch (error) {
        pushAssistantError(getApiError(error).message);
      }
      return;
    }

    setState((existing) => updateSession(existing, current.id, (session) => ({
      ...session,
      title: session.title === '新对话' ? image.title : session.title,
      contextImages: nextContext,
      messages: [
        ...session.messages,
        {
          id: safeId(),
          role: 'system',
          content: `已加入图片上下文：${image.title}`,
        },
      ],
      updatedAt: Date.now(),
    })));
    try {
      const updated = await updateAssetAgentSessionContext(current.id, {
        contextImages: nextContext.map(contextPayloadToApi),
      });
      setState((existing) => upsertSession(existing, sessionFromApi(updated), updated.id));
    } catch (error) {
      pushAssistantError(getApiError(error).message, current.id);
    }
  }, [pushAssistantError]);

  useEffect(() => {
    activeSessionRef.current = activeSession;
  }, [activeSession]);

  useEffect(() => {
    if (loading) {
      setMarkState('thinking');
      return undefined;
    }
    if (markState !== 'happy' && markState !== 'wake') {
      setMarkState('idle');
    }
    return undefined;
  }, [loading, markState]);

  useEffect(() => {
    clearLegacyAssetAgentStorage();
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadPersonalSessions = async () => {
      setInitialLoading(true);
      try {
        const response = await listAssetAgentSessions();
        const apiSessions = response.sessions.length > 0
          ? response.sessions
          : [await createAssetAgentSession()];
        if (!cancelled) {
          const sessions = apiSessions.map(sessionFromApi);
          setState(stateFromSessions(sessions, sessions[0]?.id));
        }
      } catch (error) {
        const apiError = getApiError(error);
        if (!cancelled) {
          setState(stateFromSessions([
            createLocalSession(`暂时没加载到个人记录：${apiError.message}`),
          ]));
        }
      } finally {
        if (!cancelled) setInitialLoading(false);
      }
    };

    void loadPersonalSessions();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    messagesEndRef.current?.scrollIntoView({ block: 'end' });
  }, [activeSessionId, activeMessageCount, loading, open]);

  useEffect(() => {
    if (!sessionMenuOpen) return undefined;
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target;
      if (
        target instanceof Node
        && sessionMenuRef.current
        && !sessionMenuRef.current.contains(target)
      ) {
        setSessionMenuOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSessionMenuOpen(false);
      }
    };
    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [sessionMenuOpen]);

  useEffect(() => {
    return listenForAssetAgentImages((image) => {
      void addImageToSession(image);
    });
  }, [addImageToSession]);

  const createNewSession = async () => {
    setSessionMenuOpen(false);
    setInput('');
    setMarkState('wake');
    window.setTimeout(() => setMarkState('idle'), 900);
    try {
      const created = await createAssetAgentSession();
      setState((current) => upsertSession(current, sessionFromApi(created), created.id));
    } catch (error) {
      pushAssistantError(getApiError(error).message);
    }
  };

  const removeActiveSession = async () => {
    if (!activeSession) return;
    const target = activeSession;
    setSessionMenuOpen(false);
    setInput('');
    if (isLocalSession(target.id)) {
      setState(stateFromSessions([createLocalSession()]));
      return;
    }

    try {
      await deleteAssetAgentSession(target.id);
      const remaining = state.sessions.filter((session) => session.id !== target.id);
      if (remaining.length > 0) {
        setState(stateFromSessions(remaining, remaining[0].id));
        return;
      }
      const created = await createAssetAgentSession();
      setState(stateFromSessions([sessionFromApi(created)], created.id));
    } catch (error) {
      pushAssistantError(getApiError(error).message, target.id);
    }
  };

  const clearActiveContext = async () => {
    if (!activeSession) return;
    const target = activeSession;
    setState((current) => updateSession(current, target.id, (session) => ({
      ...session,
      contextImages: [],
      updatedAt: Date.now(),
    })));
    if (isLocalSession(target.id)) return;
    try {
      const updated = await updateAssetAgentSessionContext(target.id, { contextImages: [] });
      setState((current) => upsertSession(current, sessionFromApi(updated), updated.id));
    } catch (error) {
      pushAssistantError(getApiError(error).message, target.id);
    }
  };

  const ask = async (question?: string) => {
    const message = (question ?? input).trim();
    if (!message || loadingSessionId || initialLoading || !activeSession) return;
    let targetSession = activeSession;

    setInput('');
    setMarkState('thinking');
    try {
      if (isLocalSession(targetSession.id)) {
        targetSession = await ensureServerSession(targetSession.contextImages);
      }
    } catch (error) {
      pushAssistantError(getApiError(error).message, targetSession.id);
      return;
    }

    setLoadingSessionId(targetSession.id);
    setState((current) => updateSession(current, targetSession.id, (session) => ({
      ...session,
      title: session.title === '新对话' ? titleFromMessage(message) : session.title,
      messages: [
        ...session.messages,
        { id: safeId(), role: 'user', content: message },
      ],
      updatedAt: Date.now(),
    })));
    try {
      const response = await sendAssetAgentMessage(targetSession.id, {
        message,
        imageIds: targetSession.contextImages.map((image) => image.imageId),
        assetGroupIds: targetSession.contextImages
          .map((image) => image.assetGroupId)
          .filter((value): value is string => Boolean(value)),
        conversationId: targetSession.id,
      });
      if (response.session) {
        setState((current) => upsertSession(
          current,
          sessionFromApi(response.session as ApiAssetAgentSession),
          response.session?.id,
        ));
      } else {
        setState((current) => updateSession(current, targetSession.id, (session) => ({
          ...session,
          messages: [
            ...session.messages,
            responseMessage(response),
          ],
          suggestedQuestions: response.suggestedQuestions.length > 0
            ? response.suggestedQuestions
            : [...DEFAULT_QUESTIONS],
          updatedAt: Date.now(),
        })));
      }
      setMarkState('happy');
      window.setTimeout(() => setMarkState('idle'), 1400);
    } catch (error) {
      pushAssistantError(getApiError(error).message, targetSession.id);
      setMarkState('wake');
      window.setTimeout(() => setMarkState('idle'), 900);
    } finally {
      setLoadingSessionId(null);
    }
  };

  if (!open) {
    return (
      <div className="fixed bottom-24 right-6 z-50">
        <button
          type="button"
          className="agent-greeting-bubble hidden w-[256px] rounded-2xl border border-border/80 bg-card/95 px-4 py-3 text-left text-xs leading-5 text-foreground shadow-xl shadow-foreground/10 backdrop-blur transition hover:-translate-y-0.5 sm:block"
          onClick={() => setOpen(true)}
        >
          <span className="sr-only">Hello，我在这里。哪张图拿不准，可以来问我。</span>
          <span className="agent-greeting-viewport" aria-hidden="true">
            <span className="agent-greeting-track">
              {[...GREETING_LINES, GREETING_LINES[0]].map(([title, subtitle], index) => (
                <span
                  key={`${title}-${index}`}
                  className="agent-greeting-line"
                >
                  <span className="block font-semibold">{title}</span>
                  <span className="mt-0.5 block text-muted-foreground">{subtitle}</span>
                </span>
              ))}
            </span>
          </span>
        </button>
        <button
          type="button"
          className="agent-launcher-glow inline-flex size-16 items-center justify-center rounded-full border border-white/70 bg-card/80 shadow-2xl shadow-foreground/20 backdrop-blur transition-transform hover:-translate-y-1"
          onClick={() => {
            setMarkState('wake');
            setOpen(true);
            window.setTimeout(() => setMarkState('idle'), 900);
          }}
          aria-label="打开素材库 Agent"
        >
          <PianctonAgentMark size="lg" state={markState} />
        </button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-5 right-5 z-50 flex h-[660px] max-h-[calc(100vh-40px)] w-[420px] max-w-[calc(100vw-32px)] flex-col overflow-hidden rounded-[28px] border border-border/80 bg-card/95 shadow-2xl shadow-foreground/15 backdrop-blur-xl">
      <div className="border-b border-border/70 bg-gradient-to-br from-secondary/70 via-card to-card px-4 py-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <PianctonAgentMark size="md" state={orbState} />
            <div>
              <p className="text-sm font-semibold tracking-tight">素材库 Agent</p>
              <p className="text-[11px] leading-4 text-muted-foreground">
                {loading
                  ? '正在理解素材上下文'
                  : isTemporarySession
                    ? '当前页面临时记录，未写入账号'
                    : `${sessionCount} 条今日记录 · ${formatExpiry(activeSession.expiresAt)} 清空`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-8 rounded-full"
              onClick={() => void createNewSession()}
              title="新建聊天记录"
            >
              <Plus className="size-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-8 rounded-full"
              onClick={() => setOpen(false)}
              title="收起"
            >
              <X className="size-4" />
            </Button>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-2">
          <div ref={sessionMenuRef} className="relative min-w-0 flex-1">
            <button
              type="button"
              className="agent-session-select flex w-full items-center gap-2 px-3.5 text-left"
              aria-haspopup="listbox"
              aria-expanded={sessionMenuOpen}
              onClick={() => setSessionMenuOpen((current) => !current)}
            >
              <MessageSquare className="size-3.5 shrink-0 text-muted-foreground" />
              <span className="min-w-0 flex-1 truncate text-xs font-medium text-foreground">
                {activeSession.title} · {formatSessionTime(activeSession.updatedAt)}
              </span>
              {sessionMenuOpen ? (
                <ChevronUp className="size-4 shrink-0 text-foreground" />
              ) : (
                <ChevronDown className="size-4 shrink-0 text-foreground" />
              )}
            </button>
            {sessionMenuOpen && (
              <div
                className="agent-session-menu compact-scrollbar absolute left-0 right-0 top-[calc(100%+8px)] z-30 max-h-56 overflow-y-auto rounded-2xl border border-border/80 bg-card p-1.5 shadow-xl shadow-foreground/12"
                role="listbox"
              >
                {state.sessions.map((session) => (
                  <button
                    key={session.id}
                    type="button"
                    role="option"
                    aria-selected={session.id === activeSession.id}
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left transition hover:bg-secondary/70 data-[active=true]:bg-secondary"
                    data-active={session.id === activeSession.id}
                    onClick={() => {
                      setState((current) => ({
                        ...current,
                        activeSessionId: session.id,
                      }));
                      setInput('');
                      setSessionMenuOpen(false);
                    }}
                  >
                    <MessageSquare className="size-3.5 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-xs font-medium text-foreground">
                        {session.title}
                      </span>
                      <span className="mt-0.5 block text-[10px] text-muted-foreground">
                        {formatSessionTime(session.updatedAt)}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-9 rounded-full"
            onClick={() => void removeActiveSession()}
            title="删除当前聊天记录"
          >
            <Trash2 className="size-4" />
          </Button>
        </div>
      </div>

      {activeSession.contextImages.length > 0 && (
        <div className="border-b border-border/60 bg-secondary/45 px-4 py-2">
          <div className="mb-1 flex items-center justify-between">
            <p className="text-[11px] font-medium text-muted-foreground">
              当前聊天已带入 {activeSession.contextImages.length} 张图片
            </p>
            <button
              type="button"
              className="text-[11px] text-muted-foreground hover:text-foreground"
              onClick={() => void clearActiveContext()}
            >
              清空
            </button>
          </div>
          <div className="flex gap-1.5 overflow-x-auto pb-1">
            {activeSession.contextImages.map((image) => (
              <span
                key={image.imageId}
                className="inline-flex max-w-[180px] shrink-0 items-center gap-1 rounded-full border border-border/60 bg-white px-2 py-1 text-[11px] text-foreground shadow-sm"
              >
                <ImageIcon className="size-3" />
                <span className="truncate">{image.title}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="compact-scrollbar flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {activeSession.messages.map((message) => (
          <div
            key={message.id}
            className={message.role === 'user' ? 'flex justify-end' : 'flex justify-start'}
          >
            <div
              className={[
                'max-w-[86%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-xs leading-5 shadow-sm',
                message.role === 'user'
                  ? 'bg-foreground text-background shadow-foreground/10'
                  : message.role === 'system'
                    ? 'bg-secondary text-muted-foreground'
                    : 'border border-border/70 bg-[#f8f7f4] text-foreground',
              ].join(' ')}
            >
              {message.content}
              {message.role === 'assistant' && message.usedModel === false && (
                <p className="mt-1 text-[10px] text-muted-foreground">
                  未调用到模型，已走本地兜底
                </p>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="agent-thinking-card w-[92%] rounded-[22px] border border-border/80 bg-white px-4 py-3.5 text-xs shadow-md shadow-foreground/8">
              <div className="flex items-start gap-3">
                <PianctonAgentMark size="sm" state="thinking" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-foreground">Agent 正在思考</p>
                    <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
                  </div>
                  <p className="mt-1 leading-5 text-muted-foreground">
                    我会先看图片上下文，再把它翻译成业务方能直接使用的卖点解释。
                  </p>
                  <div className="mt-3 space-y-1.5">
                    {[
                      '读取当前图片与已确认卖点',
                      '对照素材话术、证明点和使用场景',
                      '组织成家长/业务都能听懂的回答',
                    ].map((step, index) => (
                      <div
                        key={step}
                        className="agent-thinking-step flex items-center gap-2 rounded-full bg-secondary/70 px-2.5 py-1.5 text-[11px] text-muted-foreground"
                        style={{ animationDelay: `${index * 180}ms` }}
                      >
                        <span className="size-1.5 rounded-full bg-foreground/40" />
                        <span>{step}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-border/70 bg-card/95 px-4 py-3">
        <div className="mb-2 flex flex-wrap gap-1.5">
          {activeSession.suggestedQuestions.map((question) => (
            <button
              key={question}
              type="button"
              className="inline-flex items-center gap-1 rounded-full border border-border bg-white px-2.5 py-1 text-[11px] text-muted-foreground transition hover:-translate-y-0.5 hover:border-foreground/30 hover:text-foreground hover:shadow-sm"
              disabled={Boolean(loadingSessionId)}
              onClick={() => void ask(question)}
            >
              <Sparkles className="size-3" />
              {question}
            </button>
          ))}
        </div>
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            rows={2}
            placeholder="问我：这张图怎么跟家长解释？"
            className="min-h-[44px] flex-1 resize-none rounded-2xl border border-border bg-white px-3 py-2 text-xs outline-none transition focus:border-foreground/30 focus:shadow-sm"
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                void ask();
              }
            }}
          />
          <Button
            type="button"
            size="icon"
            className="size-10 rounded-full"
            disabled={Boolean(loadingSessionId) || !input.trim()}
            onClick={() => void ask()}
          >
            <Send className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

export default AssetAgentWidget;
