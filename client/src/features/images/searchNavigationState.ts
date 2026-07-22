const HOME_SCROLL_KEY = 'piancton:image-home-scroll-y';

export function rememberImageHomeScroll(): void {
  window.sessionStorage.setItem(HOME_SCROLL_KEY, String(window.scrollY));
}

export function takeImageHomeScroll(): number | null {
  const value = window.sessionStorage.getItem(HOME_SCROLL_KEY);
  if (value === null) return null;
  window.sessionStorage.removeItem(HOME_SCROLL_KEY);
  const scrollY = Number(value);
  return Number.isFinite(scrollY) ? scrollY : null;
}
