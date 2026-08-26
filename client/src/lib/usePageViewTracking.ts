import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

import { recordPageView } from '@client/src/api/usage';


export function usePageViewTracking() {
  const location = useLocation();
  const lastPathRef = useRef('');

  useEffect(() => {
    const path = `${location.pathname}${location.search}`;
    if (path === lastPathRef.current) return;
    lastPathRef.current = path;
    recordPageView({ path, title: document.title }).catch(() => undefined);
  }, [location.pathname, location.search]);
}
