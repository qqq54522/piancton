interface KeyboardEventLike {
  key: string;
  isComposing?: boolean;
  keyCode?: number;
  which?: number;
  nativeEvent?: {
    isComposing?: boolean;
    keyCode?: number;
    which?: number;
  };
}

export function shouldIgnoreEnterForIme(event: KeyboardEventLike): boolean {
  if (event.key !== 'Enter') return false;
  const native = event.nativeEvent;
  return Boolean(
    event.isComposing
    || native?.isComposing
    || event.keyCode === 229
    || native?.keyCode === 229
    || event.which === 229
    || native?.which === 229,
  );
}
