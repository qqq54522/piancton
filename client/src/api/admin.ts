import { api } from './client';
import type { AuditLog, User, UserRole } from '@client/src/types/api';


export async function fetchUsers(): Promise<User[]> {
  return (await api.get('/api/admin/users')).data;
}

export async function createUser(data: {
  username: string;
  password: string;
  role: UserRole;
}): Promise<User> {
  return (await api.post('/api/admin/users', data)).data;
}

export async function updateUser(
  id: string,
  data: { role?: UserRole; isActive?: boolean },
): Promise<User> {
  return (await api.patch(`/api/admin/users/${id}`, data)).data;
}

export async function resetPassword(id: string, password: string): Promise<void> {
  await api.post(`/api/admin/users/${id}/reset-password`, { password });
}

export async function fetchAuditLogs(): Promise<AuditLog[]> {
  return (await api.get('/api/admin/users/audit-logs')).data;
}
