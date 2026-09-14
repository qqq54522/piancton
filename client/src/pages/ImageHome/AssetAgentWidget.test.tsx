// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { sendImageToAssetAgent } from '@client/src/features/assets/assetAgentEvents';
import type { AssetAgentSession } from '@client/src/types/api';
import AssetAgentWidget from './AssetAgentWidget';

const mocks = vi.hoisted(() => ({
  createSession: vi.fn(),
  deleteTemporaryImage: vi.fn(),
  listSessions: vi.fn(),
  sendMessage: vi.fn(),
  streamMessage: vi.fn(),
  updateContext: vi.fn(),
  uploadTemporaryImage: vi.fn(),
}));

vi.mock('@client/src/api/assetAgent', () => ({
  createAssetAgentSession: mocks.createSession,
  deleteAssetAgentTemporaryImage: mocks.deleteTemporaryImage,
  listAssetAgentSessions: mocks.listSessions,
  sendAssetAgentMessage: mocks.sendMessage,
  streamAssetAgentMessage: mocks.streamMessage,
  updateAssetAgentSessionContext: mocks.updateContext,
  uploadAssetAgentTemporaryImage: mocks.uploadTemporaryImage,
}));
vi.mock('@client/src/api/image', () => ({ recordSearchInteraction: vi.fn() }));
vi.mock('@client/src/lib/auth', () => ({
  useAuth: () => ({ user: { id: 'user-1', username: 'business', role: 'business' } }),
}));

const SESSION: AssetAgentSession = {
  id: 'session-1',
  title: '新对话',
  messages: [
    {
      id: 'opening-1',
      role: 'assistant',
      content: '你好，可以把图片发给我后再输入问题。',
      createdAt: '2026-09-14T00:00:00Z',
    },
  ],
  contextImages: [],
  suggestedQuestions: [],
  expiresAt: '2026-09-15T00:00:00Z',
  memoryUsedChars: 0,
  memoryLimitChars: 12_000,
  memoryUsageRatio: 0,
  createdAt: '2026-09-14T00:00:00Z',
  updatedAt: '2026-09-14T00:00:00Z',
};

describe('AssetAgentWidget image context', () => {
  beforeEach(() => {
    Object.defineProperty(Element.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(),
    });
    mocks.listSessions.mockResolvedValue({ sessions: [SESSION] });
    mocks.updateContext.mockImplementation(async (_sessionId, payload) => ({
      ...SESSION,
      title: payload.contextImages[0]?.title ?? SESSION.title,
      contextImages: payload.contextImages,
      messages: [
        ...SESSION.messages,
        {
          id: 'context-1',
          role: 'system',
          content: `已加入图片上下文：${payload.contextImages[0]?.title}`,
          createdAt: '2026-09-14T00:01:00Z',
        },
      ],
      updatedAt: '2026-09-14T00:01:00Z',
    }));
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('only attaches a library image and waits for the user to ask a question', async () => {
    render(
      <MemoryRouter>
        <AssetAgentWidget open />
      </MemoryRouter>,
    );
    await screen.findByText('你好，可以把图片发给我后再输入问题。');

    sendImageToAssetAgent({
      imageId: 'trophy-image',
      assetGroupId: 'trophy-group',
      title: '奖杯照片',
      imageUrl: '/api/images/trophy-image/thumbnail',
    });

    await waitFor(() => expect(mocks.updateContext).toHaveBeenCalledWith(
      'session-1',
      {
        contextImages: [
          {
            imageId: 'trophy-image',
            assetGroupId: 'trophy-group',
            title: '奖杯照片',
            imageUrl: '/api/images/trophy-image/thumbnail',
          },
        ],
      },
    ));
    expect(await screen.findByText('已加入图片上下文：奖杯照片')).not.toBeNull();
    expect(screen.getByPlaceholderText('输入你想问的问题…')).not.toBeNull();
    expect(mocks.streamMessage).not.toHaveBeenCalled();
    expect(mocks.sendMessage).not.toHaveBeenCalled();
    expect(screen.queryByText(/请讲解这张图片，判断它适合表达什么业务体系/)).toBeNull();
  });
});
