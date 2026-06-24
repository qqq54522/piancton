import axios, { AxiosError } from 'axios';

import type { ApiErrorBody } from '@client/src/types/api';


function readCookie(name: string): string | undefined {
  const prefix = `${name}=`;
  return document.cookie
    .split(';')
    .map((value) => value.trim())
    .find((value) => value.startsWith(prefix))
    ?.slice(prefix.length);
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const method = config.method?.toUpperCase();
  if (method && !['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrf = readCookie('piancton_csrf');
    if (csrf) config.headers.set('X-CSRF-Token', decodeURIComponent(csrf));
  }
  return config;
});

export function getApiError(error: unknown): ApiErrorBody {
  if (error instanceof AxiosError && error.response?.data) {
    return error.response.data as ApiErrorBody;
  }
  return { code: 'network_error', message: '网络请求失败，请稍后重试' };
}
