// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import AdminIdentityCodes from './AdminIdentityCodes';

const mocks = vi.hoisted(() => ({ fetchIdentityCodes: vi.fn() }));
vi.mock('@client/src/api/admin', () => ({ fetchIdentityCodes: mocks.fetchIdentityCodes }));

describe('AdminIdentityCodes', () => {
  it('shows one active-image code model without type, status, or history controls', async () => {
    mocks.fetchIdentityCodes.mockResolvedValue({
      items: [{
        code: 'PC-8F4K2M',
        imageId: 'image-1',
        imageTitle: '合作案例竖版',
        fileName: 'case.png',
        channel: '手机端大图',
        width: 1080,
        height: 1920,
        createdAt: '2026-09-09T00:00:00Z',
        detailPath: '/image/image-1',
      }],
      total: 1,
      page: 1,
      pageSize: 20,
      summary: { imageTotal: 1 },
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <AdminIdentityCodes />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByText('PC-8F4K2M')).toBeTruthy());
    expect(screen.getByText('这里只显示未删除图片，不保留已删除身份码历史。')).toBeTruthy();
    expect(screen.queryByText('码类型')).toBeNull();
    expect(screen.queryByText('状态')).toBeNull();
    expect(screen.queryByText('版本码')).toBeNull();
    expect(screen.queryByText('素材码')).toBeNull();
  });
});
