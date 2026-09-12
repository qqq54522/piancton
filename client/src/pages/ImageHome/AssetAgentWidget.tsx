import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ChevronUp,
  Copy,
  Download,
  Image as ImageIcon,
  Loader2,
  Plus,
  Search,
  Send,
  Sparkles,
  X,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';

import {
  createAssetAgentSession,
  deleteAssetAgentTemporaryImage,
  listAssetAgentSessions,
  sendAssetAgentMessage,
  streamAssetAgentMessage,
  updateAssetAgentSessionContext,
  uploadAssetAgentTemporaryImage,
} from '@client/src/api/assetAgent';
import { getApiError } from '@client/src/api/client';
import { recordSearchInteraction } from '@client/src/api/image';
import { PianctonAgentMark } from '@client/src/components/PianctonAgentMark';
import { Button } from '@client/src/components/ui/button';
import {
  listenForAssetAgentImages,
  type AssetAgentImagePayload,
} from '@client/src/features/assets/assetAgentEvents';
import { clearLegacyAssetAgentStorage } from '@client/src/features/assets/assetAgentStorage';
import { useAuth } from '@client/src/lib/auth';
import { copyTextToClipboard } from '@client/src/lib/clipboard';
import type { AssetAgentContextCard } from '@client/src/types/api';
import {
  contextPayloadToApi,
  createLocalSession,
  DEFAULT_GREETING,
  DEFAULT_QUESTIONS,
  isLocalSession,
  normalizeAgentText,
  responseMessage,
  safeId,
  sessionFromApi,
  shouldSendAgentMessage,
  stateFromSessions,
  titleFromMessage,
  updateSession,
  upsertSession,
  type AgentSession,
  type AgentState,
} from './assetAgentSessionModel';

const AUTO_IMAGE_PROMPT = '请讲解这张图片，判断它适合表达什么业务体系和核心卖点，并给出可以怎么使用。';
const TEMPORARY_IMAGE_PROMPT = '请分析这张图片，说明它表达的内容、可能对应的业务体系和核心卖点；无法确认的部分请明确说明。';
const TEMPORARY_IMAGE_MAX_BYTES = 10 * 1024 * 1024;

type AgentResponseMode = 'balanced' | 'fast';

interface PendingTemporaryImage {
  file: File;
  previewUrl: string;
}

interface AssetAgentWidgetProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  topOffset?: number;
}

const AssetAgentWidget = ({ open, onOpenChange, topOffset = 0 }: AssetAgentWidgetProps = {}) => {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <AssetAgentWidgetInner
      key={user.id}
      open={open}
      onOpenChange={onOpenChange}
      topOffset={topOffset}
    />
  );
};

function AssetAgentWidgetInner({
  open: controlledOpen,
  onOpenChange,
  topOffset = 0,
}: AssetAgentWidgetProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const [input, setInput] = useState('');
  const [pendingImage, setPendingImage] = useState<PendingTemporaryImage | null>(null);
  const [responseMode, setResponseMode] = useState<AgentResponseMode>('balanced');
  const [uploadingImage, setUploadingImage] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [loadingSessionId, setLoadingSessionId] = useState<string | null>(null);
  const [state, setState] = useState<AgentState>(() => stateFromSessions([createLocalSession()]));
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const messagesViewportRef = useRef<HTMLDivElement | null>(null);
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const pendingImageRef = useRef<PendingTemporaryImage | null>(null);
  const followStreamRef = useRef(true);
  const askRef = useRef<((question?: string, sessionOverride?: AgentSession) => Promise<void>) | null>(null);
  const [markState, setMarkState] = useState<'idle' | 'thinking' | 'happy' | 'wake'>('idle');
  const activeSession = useMemo(
    () => state.sessions.find((session) => session.id === state.activeSessionId)
      ?? state.sessions[0],
    [state.activeSessionId, state.sessions],
  );
  const activeSessionRef = useRef<AgentSession | null>(activeSession);
  const loading = Boolean(activeSession && loadingSessionId === activeSession.id);
  const hasStreamingAssistant = Boolean(
    activeSession?.messages.some((message) => (
      message.role === 'assistant' && message.streaming
    )),
  );
  const activeSessionId = activeSession.id;
  const activeMessageCount = activeSession.messages.length;
  const activeMessageContentLength = activeSession.messages.reduce(
    (total, message) => total + message.content.length + (message.reasoningContent?.length ?? 0),
    0,
  );
  const isIntroOnly = !activeSession.messages.some((message) => message.role === 'user');
  const open = controlledOpen ?? internalOpen;

  const clearPendingImage = useCallback(() => {
    const current = pendingImageRef.current;
    if (current) URL.revokeObjectURL(current.previewUrl);
    pendingImageRef.current = null;
    setPendingImage(null);
    if (imageInputRef.current) imageInputRef.current.value = '';
  }, []);

  const setOpenState = useCallback((nextOpen: boolean) => {
    if (controlledOpen === undefined) {
      setInternalOpen(nextOpen);
    }
    onOpenChange?.(nextOpen);
  }, [controlledOpen, onOpenChange]);

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

  const addImageToSession = useCallback(async (
    image: AssetAgentImagePayload,
  ): Promise<AgentSession | null> => {
    setOpenState(true);
    const current = activeSessionRef.current;
    const contextImages = current?.contextImages ?? [];
    if (contextImages.some((item) => item.imageId === image.imageId)) return current ?? null;

    const nextContext = [...contextImages, image].slice(-8);
    if (!current || isLocalSession(current.id)) {
      try {
        const created = await createAssetAgentSession({
          contextImages: nextContext.map(contextPayloadToApi),
        });
        const normalized = sessionFromApi(created);
        setState((existing) => upsertSession(existing, normalized, created.id));
        return normalized;
      } catch (error) {
        pushAssistantError(getApiError(error).message);
        return null;
      }
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
      const normalized = sessionFromApi(updated);
      setState((existing) => upsertSession(existing, normalized, updated.id));
      return normalized;
    } catch (error) {
      pushAssistantError(getApiError(error).message, current.id);
      return null;
    }
  }, [pushAssistantError, setOpenState]);

  useEffect(() => {
    activeSessionRef.current = activeSession;
  }, [activeSession]);

  useEffect(() => {
    pendingImageRef.current = pendingImage;
  }, [pendingImage]);

  useEffect(() => () => {
    const current = pendingImageRef.current;
    if (current) URL.revokeObjectURL(current.previewUrl);
  }, []);

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
    followStreamRef.current = true;
    messagesEndRef.current?.scrollIntoView({ block: 'end' });
  }, [activeSessionId, open]);

  useEffect(() => {
    if (!open || !followStreamRef.current) return undefined;
    const frame = window.requestAnimationFrame(() => {
      const viewport = messagesViewportRef.current;
      if (viewport) viewport.scrollTop = viewport.scrollHeight;
    });
    return () => window.cancelAnimationFrame(frame);
  }, [activeMessageContentLength, activeMessageCount, loading, open]);

  useEffect(() => {
    return listenForAssetAgentImages((image) => {
      void (async () => {
        const session = await addImageToSession(image);
        if (session) void askRef.current?.(AUTO_IMAGE_PROMPT, session);
      })();
    });
  }, [addImageToSession]);

  const createNewSession = async () => {
    setInput('');
    clearPendingImage();
    setMarkState('wake');
    window.setTimeout(() => setMarkState('idle'), 900);
    const localSession = createLocalSession();
    setState((current) => upsertSession(current, localSession, localSession.id));
    try {
      const created = await createAssetAgentSession();
      setState((current) => upsertSession(current, sessionFromApi(created), created.id));
    } catch (error) {
      pushAssistantError(getApiError(error).message, localSession.id);
    }
  };

  const selectTemporaryImage = (file: File | undefined) => {
    if (!file) return;
    if (file.size > TEMPORARY_IMAGE_MAX_BYTES) {
      toast.error('临时问图不能超过 10MB');
      if (imageInputRef.current) imageInputRef.current.value = '';
      return;
    }
    const previous = pendingImageRef.current;
    if (previous) URL.revokeObjectURL(previous.previewUrl);
    const next = { file, previewUrl: URL.createObjectURL(file) };
    pendingImageRef.current = next;
    setPendingImage(next);
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

  const removeContextImage = async (imageId: string) => {
    if (!activeSession) return;
    const target = activeSession;
    const nextContext = target.contextImages.filter((image) => image.imageId !== imageId);
    if (nextContext.length === target.contextImages.length) return;
    setState((current) => updateSession(current, target.id, (session) => ({
      ...session,
      contextImages: nextContext,
      updatedAt: Date.now(),
    })));
    if (isLocalSession(target.id)) return;
    try {
      const updated = await updateAssetAgentSessionContext(target.id, {
        contextImages: nextContext.map(contextPayloadToApi),
      });
      setState((current) => upsertSession(current, sessionFromApi(updated), updated.id));
    } catch (error) {
      pushAssistantError(getApiError(error).message, target.id);
    }
  };

  const ask = async (question?: string, sessionOverride?: AgentSession) => {
    const imageForRequest = pendingImageRef.current;
    const message = (question ?? input).trim() || (imageForRequest ? TEMPORARY_IMAGE_PROMPT : '');
    const sourceSession = sessionOverride ?? activeSession;
    if (
      !message
      || loadingSessionId
      || uploadingImage
      || initialLoading
      || !sourceSession
    ) return;
    let targetSession = sourceSession;

    if (!question) setInput('');
    setMarkState('thinking');
    if (imageForRequest) setUploadingImage(true);
    try {
      if (isLocalSession(targetSession.id)) {
        targetSession = await ensureServerSession(targetSession.contextImages);
      }
    } catch (error) {
      pushAssistantError(getApiError(error).message, targetSession.id);
      setUploadingImage(false);
      return;
    }

    setLoadingSessionId(targetSession.id);
    followStreamRef.current = true;
    const assistantMessageId = safeId();
    setState((current) => updateSession(current, targetSession.id, (session) => ({
      ...session,
      title: session.title === '新对话' ? titleFromMessage(message) : session.title,
      messages: [
        ...session.messages,
        { id: safeId(), role: 'user', content: message },
        {
          id: assistantMessageId,
          role: 'assistant',
          content: '',
          reasoningContent: '',
          streaming: true,
        },
      ],
      updatedAt: Date.now(),
    })));
    let uploadedToken = '';
    try {
      const temporaryImage = imageForRequest
        ? await uploadAssetAgentTemporaryImage(imageForRequest.file)
        : null;
      uploadedToken = temporaryImage?.token ?? '';
      const payload = {
        message,
        imageIds: targetSession.contextImages.map((image) => image.imageId),
        assetGroupIds: targetSession.contextImages
          .map((image) => image.assetGroupId)
          .filter((value): value is string => Boolean(value)),
        conversationId: targetSession.id,
        temporaryImageToken: temporaryImage?.token ?? null,
        responseMode,
      };
      await streamAssetAgentMessage(targetSession.id, payload, (event) => {
        if (event.type === 'error') {
          throw new Error(event.message);
        }
        if (event.type === 'reasoning_delta' || event.type === 'answer_delta') {
          setState((current) => updateSession(current, targetSession.id, (session) => ({
            ...session,
            messages: session.messages.map((item) => {
              if (item.id !== assistantMessageId) return item;
              return {
                ...item,
                reasoningContent: event.type === 'reasoning_delta'
                  ? `${item.reasoningContent ?? ''}${event.text}`
                  : item.reasoningContent,
                content: event.type === 'answer_delta'
                  ? normalizeAgentText(`${item.content}${event.text}`)
                  : item.content,
              };
            }),
            updatedAt: Date.now(),
          })));
          return;
        }
        if (event.type === 'context_cards') {
          setState((current) => updateSession(current, targetSession.id, (session) => ({
            ...session,
            messages: session.messages.map((item) => (
              item.id === assistantMessageId
                ? { ...item, contextCards: event.cards }
                : item
            )),
            updatedAt: Date.now(),
          })));
          return;
        }
        setState((current) => updateSession(current, targetSession.id, (session) => ({
          ...session,
          messages: session.messages.map((item) => (
            item.id === assistantMessageId
              ? {
                ...item,
                content: item.content || normalizeAgentText(event.response.answer),
                usedModel: event.response.usedModel,
                contextCards: event.response.contextCards,
                streaming: false,
              }
              : item
          )),
          suggestedQuestions: event.response.suggestedQuestions.length > 0
            ? event.response.suggestedQuestions
            : [...DEFAULT_QUESTIONS],
          updatedAt: Date.now(),
        })));
      });
      setMarkState('happy');
      window.setTimeout(() => setMarkState('idle'), 1400);
      if (imageForRequest) clearPendingImage();
    } catch (error) {
      if (uploadedToken) {
        try {
          await deleteAssetAgentTemporaryImage(uploadedToken);
        } catch {
          // The backend normally consumes it; expiry cleanup covers interrupted requests.
        }
      }
      setState((current) => updateSession(current, targetSession.id, (session) => ({
        ...session,
        messages: session.messages.filter((item) => item.id !== assistantMessageId),
      })));
      try {
        const fallbackTemporaryImage = imageForRequest
          ? await uploadAssetAgentTemporaryImage(imageForRequest.file)
          : null;
        uploadedToken = fallbackTemporaryImage?.token ?? '';
        const response = await sendAssetAgentMessage(targetSession.id, {
          message,
          imageIds: targetSession.contextImages.map((image) => image.imageId),
          assetGroupIds: targetSession.contextImages
            .map((image) => image.assetGroupId)
            .filter((value): value is string => Boolean(value)),
          conversationId: targetSession.id,
          temporaryImageToken: fallbackTemporaryImage?.token ?? null,
          responseMode,
        });
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
        if (imageForRequest) clearPendingImage();
      } catch (fallbackError) {
        const messageText = fallbackError instanceof Error
          ? fallbackError.message
          : getApiError(error).message;
        pushAssistantError(messageText, targetSession.id);
      } finally {
        if (uploadedToken) {
          try {
            await deleteAssetAgentTemporaryImage(uploadedToken);
          } catch {
            // The backend normally consumes it; expiry cleanup covers interrupted requests.
          }
        }
      }
      setMarkState('wake');
      window.setTimeout(() => setMarkState('idle'), 900);
    } finally {
      setUploadingImage(false);
      setLoadingSessionId(null);
    }
  };

  useEffect(() => {
    askRef.current = ask;
  });

  if (!open) {
    return null;
  }

  return (
    <aside
      className="fixed bottom-0 right-0 z-50 flex w-full flex-col overflow-hidden border-l border-border/80 bg-card/95 shadow-2xl shadow-foreground/18 backdrop-blur-xl sm:w-[420px] lg:w-[440px]"
      style={{
        top: topOffset,
        height: `calc(100dvh - ${topOffset}px)`,
      }}
      aria-label="Piancton Agent 对话侧栏"
    >
      <div className="flex h-12 items-center justify-end gap-2 border-b border-border/60 bg-white px-4">
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[13px] font-medium text-muted-foreground transition hover:bg-secondary/70 hover:text-foreground"
          onClick={() => void createNewSession()}
        >
          <Plus className="size-3.5" />
          新对话
        </button>
        <button
          type="button"
          className="inline-flex size-8 items-center justify-center rounded-full text-muted-foreground transition hover:bg-secondary/70 hover:text-foreground"
          onClick={() => setOpenState(false)}
          aria-label="收起 Piancton Agent"
          title="收起"
        >
          <X className="size-4" />
        </button>
      </div>

      {activeSession.contextImages.length > 0 && (
        <div className="border-b border-border/60 bg-secondary/45 px-4 py-2">
          <div className="mb-1 flex items-center justify-between">
            <p className="text-[11px] font-medium text-muted-foreground">
              当前聊天已带入 {activeSession.contextImages.length} 张图片
            </p>
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-full border border-border/60 bg-white px-2 py-1 text-[11px] text-muted-foreground shadow-xs transition hover:text-foreground"
              onClick={() => void clearActiveContext()}
            >
              <X className="size-3" />
              清空全部
            </button>
          </div>
          <div className="flex gap-1.5 overflow-x-auto pb-1">
            {activeSession.contextImages.map((image) => (
              <span
                key={image.imageId}
                className="inline-flex max-w-[210px] shrink-0 items-center gap-1.5 rounded-full border border-border/60 bg-white px-2 py-1 text-[11px] text-foreground shadow-sm"
              >
                {image.imageUrl ? (
                  <img
                    src={image.imageUrl}
                    alt=""
                    className="size-5 rounded-full object-cover"
                    loading="lazy"
                    decoding="async"
                  />
                ) : (
                  <ImageIcon className="size-3" />
                )}
                <span className="truncate">{image.title}</span>
                <button
                  type="button"
                  aria-label={`移除上下文图片：${image.title}`}
                  title="从当前对话移除"
                  onClick={() => void removeContextImage(image.imageId)}
                  className="inline-flex size-5 shrink-0 items-center justify-center rounded-full text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                >
                  <X className="size-3" />
                </button>
              </span>
            ))}
          </div>
        </div>
      )}

      <div
        ref={messagesViewportRef}
        className="compact-scrollbar flex-1 space-y-5 overflow-y-auto px-5 py-5"
        onScroll={(event) => {
          const viewport = event.currentTarget;
          followStreamRef.current = (
            viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < 80
          );
        }}
      >
        {activeSession.messages.map((message, index) => {
          const previousUserMessage = activeSession.messages
            .slice(0, index)
            .reverse()
            .find((item) => item.role === 'user')?.content;
          const isIntroMessage = message.role === 'assistant' && index === 0;
          return (
          <div
            key={message.id}
            className={message.role === 'user' ? 'flex justify-end' : 'flex justify-start'}
          >
            <div
              className={[
                'whitespace-pre-wrap',
                message.role === 'user'
                  ? 'max-w-[82%] rounded-2xl bg-foreground px-4 py-2.5 text-[13px] leading-5 text-background shadow-sm shadow-foreground/10'
                  : message.role === 'system'
                    ? 'max-w-[92%] rounded-2xl bg-secondary px-3 py-2 text-[13px] leading-6 text-muted-foreground'
                    : isIntroMessage
                      ? 'w-full text-foreground/78'
                      : 'w-full text-foreground/78',
              ].join(' ')}
            >
              {isIntroMessage ? (
                <AgentIntroCard
                  content={normalizeAgentText(message.content || DEFAULT_GREETING)}
                  questions={activeSession.suggestedQuestions}
                  onAsk={(question) => void ask(question)}
                />
              ) : null}
              {message.role === 'assistant' && message.reasoningContent && (
                <AgentAnalysisCard
                  query={previousUserMessage}
                  streaming={Boolean(message.streaming)}
                />
              )}
              {!isIntroMessage && (
                <AgentMessageContent
                  content={normalizeAgentText(message.content || (message.streaming ? '正在生成回答内容…' : ''))}
                />
              )}
              {message.role === 'assistant' && message.contextCards && (
                <AgentImageCards
                  cards={message.contextCards}
                  conversationId={activeSession.id}
                />
              )}
            </div>
          </div>
          );
        })}
        {loading && !hasStreamingAssistant && (
          <div className="flex justify-start">
            <div className="w-full">
              <AgentAnalysisCard query={input} streaming />
            </div>
          </div>
        )}
        {!loading && !isIntroOnly && activeSession.suggestedQuestions.length > 0 && (
          <div className="ml-auto w-[92%] space-y-2">
            {activeSession.suggestedQuestions.slice(0, 4).map((question) => (
              <button
                key={question}
                type="button"
                className="w-full rounded-full border border-border/70 bg-white px-4 py-2.5 text-left text-[13px] leading-5 text-foreground transition hover:border-foreground/20 hover:bg-secondary/60"
                onClick={() => void ask(question)}
              >
                {question}
              </button>
            ))}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-border/60 bg-white px-5 py-3">
        <div className="mb-2 flex items-center justify-between gap-3">
          <div
            className="inline-flex rounded-full bg-secondary/70 p-0.5 text-[11px]"
            aria-label="回答模式"
          >
            {(['balanced', 'fast'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                className={[
                  'rounded-full px-2.5 py-1 font-medium transition',
                  responseMode === mode
                    ? 'bg-white text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground',
                ].join(' ')}
                onClick={() => setResponseMode(mode)}
                title={mode === 'balanced' ? '结论、依据和建议更完整' : '更快给出简洁结论'}
              >
                {mode === 'balanced' ? '均衡' : '快速'}
              </button>
            ))}
          </div>
          <span className="text-[10px] text-muted-foreground">Enter 换行 · ⌘/Ctrl+Enter 发送</span>
        </div>
        {pendingImage && (
          <div className="mb-2 flex items-center gap-2 rounded-xl border border-border/70 bg-secondary/35 p-2">
            <img
              src={pendingImage.previewUrl}
              alt="待提问图片预览"
              className="size-12 rounded-lg object-cover"
            />
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-foreground">{pendingImage.file.name}</p>
              <p className="text-[10px] text-muted-foreground">仅用于本次问答，不进入素材库</p>
            </div>
            <button
              type="button"
              className="inline-flex size-7 items-center justify-center rounded-full text-muted-foreground transition hover:bg-white hover:text-foreground"
              onClick={clearPendingImage}
              disabled={uploadingImage}
              aria-label="移除待提问图片"
              title="移除图片"
            >
              <X className="size-3.5" />
            </button>
          </div>
        )}
        <div className="flex items-end gap-2 rounded-[18px] border border-border bg-white px-2.5 py-2 shadow-sm transition focus-within:border-foreground/20 focus-within:ring-2 focus-within:ring-foreground/5">
          <input
            ref={imageInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            className="hidden"
            onChange={(event) => selectTemporaryImage(event.target.files?.[0])}
          />
          <button
            type="button"
            className="inline-flex size-9 shrink-0 items-center justify-center rounded-full text-muted-foreground transition hover:bg-secondary hover:text-foreground"
            onClick={() => imageInputRef.current?.click()}
            disabled={Boolean(loadingSessionId) || uploadingImage}
            aria-label="上传图片提问"
            title="上传一张临时图片提问"
          >
            <ImageIcon className="size-4" />
          </button>
          <textarea
            value={input}
            rows={1}
            placeholder="问我：这张图怎么用、卖点怎么讲、销售怎么回复？"
            className="min-h-9 max-h-28 flex-1 resize-none border-0 bg-transparent px-0 py-1.5 text-[15px] leading-6 outline-none placeholder:text-muted-foreground/90 focus:ring-0"
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (shouldSendAgentMessage(event)) {
                event.preventDefault();
                void ask();
              }
            }}
          />
          <Button
            type="button"
            size="icon"
            className="size-9 shrink-0 rounded-full"
            disabled={
              Boolean(loadingSessionId)
              || uploadingImage
              || (!input.trim() && !pendingImage)
            }
            onClick={() => void ask()}
          >
            {uploadingImage ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Send className="size-4" />
            )}
          </Button>
        </div>
      </div>
    </aside>
  );
}

function AgentIntroCard({
  content,
  questions,
  onAsk,
}: {
  content: string;
  questions: string[];
  onAsk: (question: string) => void;
}) {
  const paragraphs = content.split('\n\n');
  return (
    <div className="space-y-4">
      <div className="space-y-3 text-sm leading-7 text-foreground/78">
        {paragraphs.map((paragraph, index) => (
          <p key={paragraph} className={index === 0 ? 'text-base font-semibold leading-7 text-foreground/90' : undefined}>
            {paragraph}
          </p>
        ))}
      </div>
      <div className="flex items-center gap-2 pt-1 text-[13px] font-medium text-muted-foreground">
        <Sparkles className="size-3.5" />
        <span>试试这样问我</span>
      </div>
      <div className="space-y-2">
        {questions.slice(0, 4).map((question) => (
          <button
            key={question}
            type="button"
            className="w-full rounded-full border border-border/80 bg-white px-4 py-2.5 text-left text-[13px] leading-5 text-foreground transition hover:border-foreground/20 hover:bg-secondary/60"
            onClick={() => onAsk(question)}
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

function AgentAnalysisCard({
  query,
  streaming,
}: {
  query?: string;
  streaming: boolean;
}) {
  const trimmedQuery = _clipText(query?.trim() || '当前问题', 24);
  const queryChips = [
    trimmedQuery,
    buildAnalysisFollowupChip(query || ''),
  ].filter((item, index, values) => item && values.indexOf(item) === index);
  const steps = [
    '分析您的需求',
    '查询符合需求的物品',
    '整合多源信息，筛选精选内容',
    '生成回复内容',
  ];
  return (
    <div className="agent-thinking-card mb-3 rounded-2xl bg-[#f3f4f8] px-4 py-3 text-xs leading-5 text-muted-foreground">
      <div className="mb-2 flex items-center justify-between gap-2 font-semibold text-foreground">
        <span className="inline-flex items-center gap-1.5">
          {streaming ? (
            <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
          ) : (
            <PianctonAgentMark size="sm" state="happy" interactive={false} className="!size-4" />
          )}
          问题分析{streaming ? '中…' : '完成'}
        </span>
        <ChevronUp className="size-3.5 text-muted-foreground" />
      </div>
      <div className="space-y-1.5">
        {steps.map((step, index) => (
          <div key={step} className="flex items-start gap-2">
            <span
              className={[
                'mt-1.5 size-1.5 shrink-0 rounded-full',
                index < 2 || !streaming ? 'bg-foreground/45' : 'bg-border',
              ].join(' ')}
            />
            <span>{step}</span>
          </div>
        ))}
      </div>
      <div className="mt-2 space-y-1.5">
        {queryChips.map((item) => (
          <div
            key={item}
            className="flex items-center justify-between gap-2 rounded-lg bg-white px-2.5 py-1.5 text-xs text-foreground shadow-sm"
          >
            <span className="inline-flex min-w-0 items-center gap-1.5">
              <Search className="size-3 shrink-0 text-muted-foreground" />
              <span className="truncate">{item}</span>
            </span>
            <span className="text-muted-foreground">→</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function buildAnalysisFollowupChip(query: string) {
  const normalized = query.trim();
  if (!normalized) return '梳理业务知识与表达方式';
  if (/家长|话术|沟通|听懂|转成/.test(normalized)) {
    return '整理成家长能听懂的表达';
  }
  if (/找图|图片|素材|配图/.test(normalized)) {
    return '先确认卖点，再检索已适配素材';
  }
  return `直接回答“${_clipText(normalized, 18)}”`;
}

function AgentMessageContent({ content }: { content: string }) {
  const lines = content.split('\n');
  return (
    <div className="space-y-2 text-sm leading-7 text-inherit">
      {lines.map((rawLine, index) => {
        const line = rawLine.trim();
        const key = `${index}-${rawLine}`;
        if (!line) return <div key={key} className="h-1" />;
        if (/^#{1,3}\s+/.test(line)) {
          return (
            <p key={key} className="pt-1 text-base font-semibold leading-7 text-inherit">
              {renderInlineMarkdown(line.replace(/^#{1,3}\s+/, ''))}
            </p>
          );
        }
        if (/^[-*]\s+/.test(line)) {
          return (
            <p key={key} className="pl-3 text-sm leading-7 before:mr-1 before:content-['•']">
              {renderInlineMarkdown(line.replace(/^[-*]\s+/, ''))}
            </p>
          );
        }
        if (/^\d+[.)、]\s*/.test(line)) {
          return (
            <p key={key} className="text-sm leading-7">
              {renderInlineMarkdown(line)}
            </p>
          );
        }
        return (
          <p key={key} className="text-sm leading-7">
            {renderInlineMarkdown(line)}
          </p>
        );
      })}
    </div>
  );
}

function AgentImageCards({
  cards,
  conversationId,
}: {
  cards: AssetAgentContextCard[];
  conversationId: string;
}) {
  const imageCards = cards.filter((card) => card.kind === 'image' && card.imageUrl).slice(0, 8);
  if (imageCards.length === 0) return null;
  return (
    <div className="mt-3 grid grid-cols-2 gap-2" aria-label="Agent 推荐素材">
      {imageCards.map((card, index) => (
        <AgentImageCard
          key={card.id}
          card={card}
          conversationId={conversationId}
          position={index + 1}
        />
      ))}
    </div>
  );
}

function AgentImageCard({
  card,
  conversationId,
  position,
}: {
  card: AssetAgentContextCard;
  conversationId: string;
  position: number;
}) {
  const cardRef = useRef<HTMLElement | null>(null);
  const exposureSent = useRef(false);
  const track = useCallback((action: 'exposure' | 'open_detail' | 'download' | 'copy_identity') => {
    void recordSearchInteraction({
      searchLogId: null,
      keyword: '',
      action,
      resultImageId: card.id,
      assetGroupId: card.assetGroupId,
      position,
      source: 'agent_chat',
      conversationId,
    }).catch(() => undefined);
  }, [card.assetGroupId, card.id, conversationId, position]);

  useEffect(() => {
    const element = cardRef.current;
    if (!element || exposureSent.current) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting || exposureSent.current) return;
      exposureSent.current = true;
      track('exposure');
      observer.disconnect();
    }, { threshold: 0.45 });
    observer.observe(element);
    return () => observer.disconnect();
  }, [track]);

  const copyIdentity = async () => {
    if (!card.identityCode) return;
    if (await copyTextToClipboard(card.identityCode)) {
      track('copy_identity');
      toast.success('身份码已复制');
    } else {
      toast.error('复制失败');
    }
  };

  return (
    <article ref={cardRef} className="group overflow-hidden rounded-xl border border-border/70 bg-white shadow-sm">
      <Link
        to={`/image/${card.id}`}
        className="block aspect-[4/3] overflow-hidden bg-secondary"
        onClick={() => track('open_detail')}
      >
        <img
          src={card.imageUrl || `/api/images/${card.id}/thumbnail`}
          alt={card.title}
          className="size-full object-cover transition-transform duration-200 group-hover:scale-[1.02]"
          loading="lazy"
          decoding="async"
        />
      </Link>
      <div className="space-y-1.5 p-2.5">
        <p className="line-clamp-2 text-[13px] font-medium leading-5 text-foreground">
          {card.title}
        </p>
        {card.identityCode && (
          <p className="text-[11px] text-muted-foreground">{card.identityCode}</p>
        )}
        <div className="flex items-center gap-1">
          {card.identityCode && (
            <button
              type="button"
              onClick={() => void copyIdentity()}
              className="inline-flex size-7 items-center justify-center rounded-full text-muted-foreground transition hover:bg-secondary hover:text-foreground"
              aria-label={`复制 ${card.title} 的身份码`}
              title="复制身份码"
            >
              <Copy className="size-3.5" />
            </button>
          )}
          {card.downloadUrl && (
            <a
              href={card.downloadUrl}
              download
              onClick={() => track('download')}
              className="inline-flex size-7 items-center justify-center rounded-full text-muted-foreground transition hover:bg-secondary hover:text-foreground"
              aria-label={`下载 ${card.title}`}
              title="下载"
            >
              <Download className="size-3.5" />
            </a>
          )}
        </div>
      </div>
    </article>
  );
}

function renderInlineMarkdown(value: string) {
  return value.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={`${part}-${index}`} className="font-semibold text-foreground">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

function _clipText(value: string, maxLength: number) {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;
}

export default AssetAgentWidget;
