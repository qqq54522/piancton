import { api } from './client';
import type { LoginResponse, User } from '@client/src/types/api';


export async function login(username: string, password: string): Promise<LoginResponse> {
  return (await api.post('/api/auth/login', { username, password })).data;
}

export async function logout(): Promise<void> {
  await api.post('/api/auth/logout');
}

export async function me(): Promise<User> {
  return (await api.get('/api/auth/me')).data;
}
