import { describe, expect, it } from 'vitest';

import {
  contextPayloadToApi,
  conversationMemoryUsage,
  createLocalSession,
  sessionFromApi,
  stateFromSessions,
  titleFromMessage,
  updateSession,
  normalizeAgentText,
  shouldSendAgentMessage,
} from './assetAgentSessionModel';

describe('assetAgentSessionModel', () => {
  it('creates a temporary session with the default questions', () => {
    const session = createLocalSession();

    expect(session.id.startsWith('local-')).toBe(true);
    expect(session.title).toBe('新对话');
    expect(session.messages).toHaveLength(1);
    expect(session.suggestedQuestions).toHaveLength(4);
    expect(session.memoryUsageRatio).toBe(0);
  });

  it('normalizes API sessions and context payloads', () => {
    const session = sessionFromApi({
      id: 'session-1',
      title: '',
      messages: [
        {
          id: 'message-1',
          role: 'assistant',
          content: '回答',
          usedModel: true,
          createdAt: '2026-08-26T00:00:00Z',
        },
      ],
      contextImages: [
        {
          imageId: 'image-1',
          assetGroupId: null,
          title: '课程同步',
        },
      ],
      suggestedQuestions: [],
      memoryUsedChars: 120,
      memoryLimitChars: 12000,
      memoryUsageRatio: 0.01,
      createdAt: '2026-08-26T00:00:00Z',
      updatedAt: '2026-08-26T00:01:00Z',
      expiresAt: '2026-08-27T00:00:00Z',
    });

    expect(session.title).toBe('历史对话');
    expect(session.contextImages[0].imageId).toBe('image-1');
    expect(session.suggestedQuestions).toHaveLength(4);
    expect(session.memoryUsageRatio).toBe(0.01);
    expect(contextPayloadToApi(session.contextImages[0])).toEqual({
      imageId: 'image-1',
      assetGroupId: null,
      title: '课程同步',
      imageUrl: null,
    });
  });

  it('measures only the active conversation after the first user message', () => {
    const usage = conversationMemoryUsage([
      { id: 'greeting', role: 'assistant', content: '很长的开场白'.repeat(100) },
      { id: 'user', role: 'user', content: '先介绍拍题精学' },
      { id: 'assistant', role: 'assistant', content: '它属于拍题精学卖点' },
    ], 100);

    expect(usage.usedChars).toBeGreaterThan(0);
    expect(usage.usedChars).toBeLessThan(100);
    expect(usage.ratio).toBe(usage.usedChars / 100);
  });

  it('reports a full window after the controlled message limit is reached', () => {
    const messages = Array.from({ length: 25 }, (_, index) => ({
      id: `message-${index}`,
      role: index % 2 === 0 ? 'user' as const : 'assistant' as const,
      content: `第 ${index + 1} 条消息`,
    }));

    expect(conversationMemoryUsage(messages, 12000)).toEqual({
      usedChars: 12000,
      ratio: 1,
    });
  });

  it('renders escaped line breaks from configured AI Search openings', () => {
    expect(normalizeAgentText('Hi\\n\\n我可以帮你')).toBe('Hi\n\n我可以帮你');
  });

  it('keeps Enter for new lines and sends only with the command shortcut', () => {
    expect(shouldSendAgentMessage({ key: 'Enter', metaKey: false, ctrlKey: false }))
      .toBe(false);
    expect(shouldSendAgentMessage({ key: 'Enter', metaKey: true, ctrlKey: false }))
      .toBe(true);
    expect(shouldSendAgentMessage({ key: 'Enter', metaKey: false, ctrlKey: true }))
      .toBe(true);
  });

  it('keeps the selected session stable while sorting by activity', () => {
    const older = createLocalSession();
    const newer = createLocalSession();
    const state = stateFromSessions(
      [
        { ...older, id: 'session-old', updatedAt: 100 },
        { ...newer, id: 'session-new', updatedAt: 200 },
      ],
      'session-old',
    );

    expect(state.sessions[0].id).toBe('session-new');
    expect(state.activeSessionId).toBe('session-old');

    const updated = updateSession(state, 'session-old', (session) => ({
      ...session,
      title: titleFromMessage('  家长如何理解这张图  '),
    }));
    expect(updated.sessions.find((session) => session.id === 'session-old')?.title)
      .toBe('家长如何理解这张图');
  });
});
