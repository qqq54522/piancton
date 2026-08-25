import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'piancton:animated-gif-preview';

export function useAnimatedGifPreview() {
  const [enabled, setEnabled] = useState(() => readPreference());

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, enabled ? '1' : '0');
  }, [enabled]);

  const toggle = useCallback(() => {
    setEnabled((current) => !current);
  }, []);

  return { enabled, setEnabled, toggle };
}

function readPreference(): boolean {
  return window.localStorage.getItem(STORAGE_KEY) !== '0';
}
