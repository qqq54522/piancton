// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest';

import { copyTextToClipboard } from './clipboard';

describe('copyTextToClipboard', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('uses the Clipboard API in a secure context', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', { clipboard: { writeText } });
    vi.stubGlobal('isSecureContext', true);

    expect(await copyTextToClipboard('PC-8F4K2M')).toBe(true);
    expect(writeText).toHaveBeenCalledWith('PC-8F4K2M');
  });

  it('falls back to execCommand on a plain HTTP deployment', async () => {
    const execCommand = vi.fn().mockReturnValue(true);
    Object.defineProperty(document, 'execCommand', {
      configurable: true,
      value: execCommand,
    });
    vi.stubGlobal('isSecureContext', false);

    expect(await copyTextToClipboard('PC-7PMTR6')).toBe(true);
    expect(execCommand).toHaveBeenCalledWith('copy');
    expect(document.querySelector('textarea')).toBeNull();
  });

  it('returns false when neither copy path is available', async () => {
    Object.defineProperty(document, 'execCommand', {
      configurable: true,
      value: undefined,
    });
    vi.stubGlobal('isSecureContext', false);

    expect(await copyTextToClipboard('PC-29DOBJ')).toBe(false);
  });
});
