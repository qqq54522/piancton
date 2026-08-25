import { describe, expect, it } from 'vitest';

import { shouldIgnoreEnterForIme } from './ime';

describe('IME keyboard handling', () => {
  it('ignores Enter while composition is active', () => {
    expect(shouldIgnoreEnterForIme({
      key: 'Enter',
      nativeEvent: { isComposing: true },
    })).toBe(true);
  });

  it('ignores Enter reported as keyCode 229 by Chinese input methods', () => {
    expect(shouldIgnoreEnterForIme({
      key: 'Enter',
      nativeEvent: { keyCode: 229 },
    })).toBe(true);
  });

  it('allows a normal Enter after composition has ended', () => {
    expect(shouldIgnoreEnterForIme({
      key: 'Enter',
      nativeEvent: { isComposing: false, keyCode: 13 },
    })).toBe(false);
  });

  it('does not ignore non-Enter keys', () => {
    expect(shouldIgnoreEnterForIme({
      key: 'a',
      nativeEvent: { isComposing: true },
    })).toBe(false);
  });
});
