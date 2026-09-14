import axios, { AxiosError } from 'axios';

import type { ApiErrorBody } from '@client/src/types/api';

export const AUTH_EXPIRED_EVENT = 'piancton:auth-expired';

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

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (
      error instanceof AxiosError
      && error.response?.status === 401
      && !isPublicAuthRequest(error.config?.url)
      && typeof window !== 'undefined'
    ) {
      window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
    }
    return Promise.reject(error);
  },
);

function isPublicAuthRequest(url?: string) {
  return ['/api/auth/login', '/api/auth/register', '/api/auth/me']
    .some((path) => url?.startsWith(path));
}

export function getApiError(error: unknown): ApiErrorBody {
  if (error instanceof AxiosError && error.response?.data) {
    return error.response.data as ApiErrorBody;
  }
  if (error instanceof AxiosError && error.code === 'ECONNABORTED') {
    return { code: 'request_timeout', message: '页面等待服务器返回结果已超时，请稍后重试' };
  }
  return { code: 'network_error', message: '网络请求失败，请稍后重试' };
}
