import { api } from './client';
import type { LoginResponse, User } from '@client/src/types/api';
import type { components } from '@client/src/types/openapi';

export type AvatarPresetId = NonNullable<components['schemas']['RegisterRequest']['avatarPresetId']>;

export async function login(username: string, password: string): Promise<LoginResponse> {
  return (await api.post('/api/auth/login', { username, password })).data;
}

export async function register(username: string, password: string, confirmPassword: string, avatarPresetId?: AvatarPresetId): Promise<User> {
  const payload: components['schemas']['RegisterRequest'] = { username, password, confirmPassword, avatarPresetId };
  return (await api.post('/api/auth/register', payload)).data;
}

export async function uploadAvatar(file: File): Promise<User> {
  const form = new FormData();
  form.append('file', file);
  return (await api.post('/api/auth/avatar', form)).data;
}

export async function selectAvatarPreset(presetId: AvatarPresetId): Promise<User> {
  return (await api.post('/api/auth/avatar/preset', { presetId })).data;
}

export async function logout(): Promise<void> {
  await api.post('/api/auth/logout');
}

export async function me(): Promise<User> {
  return (await api.get('/api/auth/me')).data;
}

export async function completeOnboarding(): Promise<User> {
  return (await api.post('/api/auth/onboarding/complete')).data;
}
