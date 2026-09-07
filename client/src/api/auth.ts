import { api } from './client';
import type { LoginResponse, User } from '@client/src/types/api';
import type { components } from '@client/src/types/openapi';


export async function login(username: string, password: string): Promise<LoginResponse> {
  return (await api.post('/api/auth/login', { username, password })).data;
}

export async function register(username: string, password: string, confirmPassword: string): Promise<User> {
  const payload: components['schemas']['RegisterRequest'] = { username, password, confirmPassword };
  return (await api.post('/api/auth/register', payload)).data;
}

export async function logout(): Promise<void> {
  await api.post('/api/auth/logout');
}

export async function me(): Promise<User> {
  return (await api.get('/api/auth/me')).data;
}
