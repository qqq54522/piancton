import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import * as adminApi from '@client/src/api/admin';
import { getApiError } from '@client/src/api/client';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import type { UserRole } from '@client/src/types/api';


const roles: UserRole[] = ['business', 'designer', 'admin'];

export default function AdminUsers() {
  const client = useQueryClient();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>('business');
  const users = useQuery({ queryKey: ['admin-users'], queryFn: adminApi.fetchUsers });
  const refresh = () => client.invalidateQueries({ queryKey: ['admin-users'] });
  const create = useMutation({
    mutationFn: adminApi.createUser,
    onSuccess: () => {
      setUsername('');
      setPassword('');
      refresh();
      toast.success('账号已创建');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });
  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { role?: UserRole; isActive?: boolean } }) =>
      adminApi.updateUser(id, data),
    onSuccess: refresh,
    onError: (error) => toast.error(getApiError(error).message),
  });

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
      <h1 className="text-2xl font-semibold">用户管理</h1>
      <div className="mt-5 grid gap-3 rounded-xl border bg-card p-4 md:grid-cols-[1fr_1fr_160px_auto]">
        <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="新账号" />
        <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="初始密码（至少 8 位）" />
        <select className="rounded-md border bg-background px-3 text-sm" value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
          {roles.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
        <Button
          disabled={create.isPending || username.trim().length < 3 || password.length < 8}
          onClick={() => create.mutate({ username: username.trim(), password, role })}
        >
          创建账号
        </Button>
      </div>
      <div className="mt-5 overflow-hidden rounded-xl border bg-card">
        {users.isLoading ? (
          <p className="p-5 text-sm text-muted-foreground">正在加载...</p>
        ) : users.isError ? (
          <p className="p-5 text-sm text-destructive">
            {getApiError(users.error).message}
          </p>
        ) : users.data?.map((user) => (
          <div key={user.id} className="grid items-center gap-3 border-b p-4 last:border-0 md:grid-cols-[1fr_180px_120px_auto]">
            <div>
              <div className="font-medium">{user.username}</div>
              <div className="text-xs text-muted-foreground">{user.isActive ? '正常' : '已停用'}</div>
            </div>
            <select
              className="h-9 rounded-md border bg-background px-2 text-sm"
              value={user.role}
              onChange={(e) => update.mutate({ id: user.id, data: { role: e.target.value as UserRole } })}
            >
              {roles.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => update.mutate({ id: user.id, data: { isActive: !user.isActive } })}
            >
              {user.isActive ? '停用' : '启用'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                const next = window.prompt(`为 ${user.username} 设置新密码（至少 8 位）`);
                if (!next) return;
                try {
                  await adminApi.resetPassword(user.id, next);
                  toast.success('密码已重置，旧会话已失效');
                } catch (error) {
                  toast.error(getApiError(error).message);
                }
              }}
            >
              重置密码
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
