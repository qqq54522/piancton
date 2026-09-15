// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
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
    expect(screen.queryByText('今日记忆')).toBeNull();

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

  it('consumes a library image after one answer and keeps the conversation for followups', async () => {
    mocks.streamMessage.mockImplementation(async (_sessionId, _payload, onEvent) => {
      onEvent({
        type: 'final',
        response: {
          answer: '这张图展示了一座奖杯。',
          conversationId: 'session-1',
          session: { ...SESSION, contextImages: [] },
          suggestedQuestions: [],
          contextCards: [],
          usedModel: true,
          providerAttempts: [],
        },
      });
    });
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
    await screen.findByText('下一条消息将附带 1 张图片');

    const input = screen.getByPlaceholderText('输入你想问的问题…');
    fireEvent.change(input, { target: { value: '这张图是什么？' } });
    fireEvent.keyDown(input, { key: 'Enter', metaKey: true });
    await waitFor(() => expect(mocks.streamMessage).toHaveBeenCalledTimes(1));
    expect(mocks.streamMessage.mock.calls[0][1].imageIds).toEqual(['trophy-image']);
    await waitFor(() => expect(screen.queryByText('下一条消息将附带 1 张图片')).toBeNull());
    expect(screen.getByText('奖杯照片')).not.toBeNull();

    fireEvent.change(input, { target: { value: '那它适合怎么用？' } });
    fireEvent.keyDown(input, { key: 'Enter', metaKey: true });
    await waitFor(() => expect(mocks.streamMessage).toHaveBeenCalledTimes(2));
    expect(mocks.streamMessage.mock.calls[1][1].imageIds).toEqual([]);
    expect(mocks.streamMessage.mock.calls[1][1].conversationId).toBe('session-1');
  });

  it('switches the pending library image when another image is sent', async () => {
    mocks.streamMessage.mockImplementation(async (_sessionId, _payload, onEvent) => {
      onEvent({
        type: 'final',
        response: {
          answer: '这是第二张图的回答。',
          conversationId: 'session-1',
          session: { ...SESSION, contextImages: [] },
          suggestedQuestions: [],
          contextCards: [],
          usedModel: true,
          providerAttempts: [],
        },
      });
    });
    render(
      <MemoryRouter>
        <AssetAgentWidget open />
      </MemoryRouter>,
    );
    await screen.findByText('你好，可以把图片发给我后再输入问题。');

    sendImageToAssetAgent({ imageId: 'image-a', title: '第一张图' });
    await waitFor(() => expect(mocks.updateContext).toHaveBeenCalledTimes(1));
    sendImageToAssetAgent({ imageId: 'image-b', title: '第二张图' });
    await waitFor(() => expect(mocks.updateContext).toHaveBeenCalledTimes(2));
    expect(mocks.updateContext.mock.calls[1][1].contextImages.map((image: { imageId: string }) => image.imageId))
      .toEqual(['image-b']);
    expect(screen.getByText('下一条消息将附带 1 张图片')).not.toBeNull();

    const input = screen.getByPlaceholderText('输入你想问的问题…');
    fireEvent.change(input, { target: { value: '新图讲了什么？' } });
    fireEvent.keyDown(input, { key: 'Enter', metaKey: true });
    await waitFor(() => expect(mocks.streamMessage).toHaveBeenCalledTimes(1));
    expect(mocks.streamMessage.mock.calls[0][1].imageIds).toEqual(['image-b']);
    expect(mocks.streamMessage.mock.calls[0][1].conversationId).toBe('session-1');
  });

  it('keeps a sent temporary image in its message and continues the same chat', async () => {
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: vi.fn(() => 'blob:preview-image'),
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: vi.fn(),
    });
    mocks.uploadTemporaryImage.mockResolvedValue({ token: 'temporary-token' });
    mocks.streamMessage.mockImplementation(async (_sessionId, _payload, onEvent) => {
      onEvent({
        type: 'final',
        response: {
          answer: '这张图是一所学校。',
          conversationId: 'session-1',
          session: { ...SESSION, contextImages: [] },
          suggestedQuestions: [],
          contextCards: [],
          usedModel: true,
          providerAttempts: [],
        },
      });
    });
    const { container } = render(
      <MemoryRouter>
        <AssetAgentWidget open />
      </MemoryRouter>,
    );
    await screen.findByText('你好，可以把图片发给我后再输入问题。');
    const fileInput = container.querySelector('input[type="file"]');
    expect(fileInput).not.toBeNull();
    fireEvent.change(fileInput!, {
      target: { files: [new File(['image'], '学校照片.png', { type: 'image/png' })] },
    });
    await screen.findByText('学校照片.png');
    const input = screen.getByPlaceholderText('输入你想问的问题…');
    fireEvent.change(input, { target: { value: '这张图是什么？' } });
    fireEvent.keyDown(input, { key: 'Enter', metaKey: true });
    await waitFor(() => expect(mocks.streamMessage).toHaveBeenCalledTimes(1));
    expect(mocks.streamMessage.mock.calls[0][1].temporaryImageToken).toBe('temporary-token');
    await waitFor(() => expect(screen.queryByText('学校照片.png')).toBeNull());
    expect(screen.getByText('学校照片')).not.toBeNull();

    fireEvent.change(input, { target: { value: '我刚才发的图是什么？' } });
    fireEvent.keyDown(input, { key: 'Enter', metaKey: true });
    await waitFor(() => expect(mocks.streamMessage).toHaveBeenCalledTimes(2));
    expect(mocks.streamMessage.mock.calls[1][1].temporaryImageToken).toBeNull();
    expect(mocks.streamMessage.mock.calls[1][1].conversationId).toBe('session-1');
  });

  it('uses the server session id when a stale browser conversation was replaced', async () => {
    mocks.streamMessage.mockImplementation(async (_sessionId, payload, onEvent) => {
      onEvent({
        type: 'final',
        response: {
          answer: '继续对话成功。',
          conversationId: 'session-recovered',
          session: {
            ...SESSION,
            id: 'session-recovered',
            messages: [
              ...SESSION.messages,
              { id: 'user-recovered', role: 'user', content: payload.message, createdAt: '2026-09-14T00:01:00Z' },
              { id: 'answer-recovered', role: 'assistant', content: '继续对话成功。', createdAt: '2026-09-14T00:02:00Z' },
            ],
          },
          suggestedQuestions: [],
          contextCards: [],
          usedModel: true,
          providerAttempts: [],
        },
      });
    });
    render(<MemoryRouter><AssetAgentWidget open /></MemoryRouter>);
    await screen.findByText('你好，可以把图片发给我后再输入问题。');
    const input = screen.getByPlaceholderText('输入你想问的问题…');
    fireEvent.change(input, { target: { value: '第一问' } });
    fireEvent.keyDown(input, { key: 'Enter', metaKey: true });
    await screen.findByText('继续对话成功。');
    fireEvent.change(input, { target: { value: '继续追问' } });
    fireEvent.keyDown(input, { key: 'Enter', metaKey: true });
    await waitFor(() => expect(mocks.streamMessage).toHaveBeenCalledTimes(2));
    expect(mocks.streamMessage.mock.calls[1][0]).toBe('session-recovered');
  });
});
