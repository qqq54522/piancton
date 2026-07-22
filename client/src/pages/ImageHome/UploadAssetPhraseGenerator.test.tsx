// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import UploadAssetPhraseGenerator from './UploadAssetPhraseGenerator';

describe('UploadAssetPhraseGenerator', () => {
  afterEach(cleanup);

  it('lets the designer choose two through five phrases and trigger generation', () => {
    const onCountChange = vi.fn();
    const onGenerate = vi.fn();
    render(
      <UploadAssetPhraseGenerator
        count={5}
        onCountChange={onCountChange}
        onGenerate={onGenerate}
        generating={false}
        disabled={false}
        hint="读取当前图片"
      />,
    );

    fireEvent.change(screen.getByLabelText('AI 生成话术数量'), {
      target: { value: '3' },
    });
    fireEvent.click(screen.getByRole('button', { name: '生成并填充' }));

    expect(screen.getByText('AI 生成业务搜索话术')).toBeTruthy();
    expect(onCountChange).toHaveBeenCalledWith(3);
    expect(onGenerate).toHaveBeenCalledOnce();
  });

  it('disables generation when a single analyzable image is unavailable', () => {
    render(
      <UploadAssetPhraseGenerator
        count={5}
        onCountChange={() => undefined}
        onGenerate={() => undefined}
        generating={false}
        disabled
        hint="请选择单张图片"
      />,
    );

    const button = screen.getByRole('button', { name: '生成并填充' });
    expect((button as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText('请选择单张图片')).toBeTruthy();
  });
});
