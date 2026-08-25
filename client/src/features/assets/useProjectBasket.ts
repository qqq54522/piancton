import { useCallback, useEffect, useMemo, useState } from 'react';

const STORAGE_KEY = 'piancton:project-basket';

export interface ProjectBasketItem {
  assetGroupId: string;
  title: string;
  imageId?: string | null;
}

export function useProjectBasket() {
  const [items, setItems] = useState<ProjectBasketItem[]>(() => readBasket());

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) setItems(readBasket());
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const persist = useCallback((next: ProjectBasketItem[]) => {
    setItems(next);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }, []);

  const add = useCallback((item: ProjectBasketItem) => {
    persist(upsertBasketItem(items, item));
  }, [items, persist]);

  const remove = useCallback((assetGroupId: string) => {
    persist(items.filter((item) => item.assetGroupId !== assetGroupId));
  }, [items, persist]);

  const toggle = useCallback((item: ProjectBasketItem) => {
    if (items.some((current) => current.assetGroupId === item.assetGroupId)) {
      remove(item.assetGroupId);
      return;
    }
    add(item);
  }, [add, items, remove]);

  const clear = useCallback(() => {
    persist([]);
  }, [persist]);

  const ids = useMemo(() => items.map((item) => item.assetGroupId), [items]);
  const has = useCallback(
    (assetGroupId?: string | null) => Boolean(assetGroupId && ids.includes(assetGroupId)),
    [ids],
  );

  return { items, ids, add, remove, toggle, clear, has };
}

function readBasket(): ProjectBasketItem[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((item): item is ProjectBasketItem => (
        Boolean(item)
        && typeof item.assetGroupId === 'string'
        && typeof item.title === 'string'
      ))
      .slice(0, 50);
  } catch {
    return [];
  }
}

function upsertBasketItem(
  items: ProjectBasketItem[],
  item: ProjectBasketItem,
): ProjectBasketItem[] {
  const normalized = {
    assetGroupId: item.assetGroupId,
    title: item.title.trim() || '未命名素材',
    imageId: item.imageId ?? null,
  };
  return [
    normalized,
    ...items.filter((current) => current.assetGroupId !== item.assetGroupId),
  ].slice(0, 50);
}
