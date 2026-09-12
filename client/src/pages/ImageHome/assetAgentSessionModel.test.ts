import { describe, expect, it } from 'vitest';

import {
  contextPayloadToApi,
  createLocalSession,
  sessionFromApi,
  stateFromSessions,
  titleFromMessage,
  updateSession,
} from './assetAgentSessionModel';

describe('assetAgentSessionModel', () => {
  it('creates a temporary session with the default questions', () => {
    const session = createLocalSession();

    expect(session.id.startsWith('local-')).toBe(true);
    expect(session.title).toBe('新对话');
    expect(session.messages).toHaveLength(1);
    expect(session.suggestedQuestions).toHaveLength(4);
    expect(session.expiresAt).toBeGreaterThan(session.updatedAt);
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
      createdAt: '2026-08-26T00:00:00Z',
      updatedAt: '2026-08-26T00:01:00Z',
      expiresAt: '2026-08-27T00:01:00Z',
    });

    expect(session.title).toBe('历史对话');
    expect(session.contextImages[0].imageId).toBe('image-1');
    expect(session.suggestedQuestions).toHaveLength(4);
    expect(contextPayloadToApi(session.contextImages[0])).toEqual({
      imageId: 'image-1',
      assetGroupId: null,
      title: '课程同步',
      imageUrl: null,
    });
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
