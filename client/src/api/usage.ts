import { api } from './client';
import type { PageViewCreate } from '@client/src/types/api';


export async function recordPageView(payload: PageViewCreate): Promise<void> {
  await api.post('/api/usage/page-view', payload);
}
