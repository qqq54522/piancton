import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Copy, KeyRound, Plus, ShieldCheck, UserCheck, UserRoundCog } from 'lucide-react';
import { toast } from 'sonner';

import * as adminApi from '@client/src/api/admin';
import { getApiError } from '@client/src/api/client';
import PageHeader from '@client/src/components/PageHeader';
import { Badge } from '@client/src/components/ui/badge';
import { Button } from '@client/src/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@client/src/components/ui/dialog';
import { Input } from '@client/src/components/ui/input';
import { Select } from '@client/src/components/ui/select';
import { copyTextToClipboard } from '@client/src/lib/clipboard';
import type { UserRole } from '@client/src/types/api';

const roles: UserRole[] = ['business', 'designer', 'admin'];
const roleLabels: Record<UserRole, string> = {
  business: '业务用户',
  designer: '设计师',
  admin: '管理员',
};

export default function AdminUsers() {
  const client = useQueryClient();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>('business');
  const [resetTarget, setResetTarget] = useState<{ id: string; username: string } | null>(null);
  const [nextPassword, setNextPassword] = useState('');
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
  const resetPassword = useMutation({
    mutationFn: ({ id, password: value }: { id: string; password: string }) => adminApi.resetPassword(id, value),
    onSuccess: () => {
      setResetTarget(null);
      setNextPassword('');
      toast.success('密码已重置，旧会话已失效');
    },
    onError: (error) => toast.error(getApiError(error).message),
  });
  const copyUserIdentity = async (userId: string) => {
    if (await copyTextToClipboard(userId)) {
      toast.success('用户身份码已复制');
      return;
    }
    toast.error('复制失败，请手动选择身份码');
  };

  return (
    <div className="page-shell max-w-6xl">
      <PageHeader title="用户与权限" />

      <section className="surface-card mt-7 p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <div className="flex size-10 items-center justify-center rounded-xl bg-accent text-primary">
            <Plus className="size-5" />
          </div>
          <div>
            <h2 className="font-semibold">创建新账号</h2>
            <p className="mt-1 text-xs text-muted-foreground">账号创建后即可按角色进入对应工作区。</p>
          </div>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-[1fr_1fr_180px_auto] md:items-end">
          <label>
            <span className="field-label">账号</span>
            <Input value={username} onChange={(event) => setUsername(event.target.value)} placeholder="至少 3 个字符" />
          </label>
          <label>
            <span className="field-label">初始密码</span>
            <Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="至少 8 位" />
          </label>
          <label>
            <span className="field-label">角色</span>
            <Select value={role} onChange={(event) => setRole(event.target.value as UserRole)}>
              {roles.map((item) => <option key={item} value={item}>{roleLabels[item]}</option>)}
            </Select>
          </label>
          <Button
            disabled={create.isPending || username.trim().length < 3 || password.length < 8}
            onClick={() => create.mutate({ username: username.trim(), password, role })}
          >
            <Plus className="size-4" />创建账号
          </Button>
        </div>
      </section>

      <section className="surface-card mt-6 overflow-hidden">
        <div className="flex items-center justify-between border-b border-border/80 px-5 py-4">
          <div>
            <h2 className="font-semibold">现有账号</h2>
            <p className="mt-1 text-xs text-muted-foreground">角色修改即时生效，停用后所有旧会话失效。</p>
          </div>
          {users.data && <Badge variant="secondary">{users.data.length} 个账号</Badge>}
        </div>
        {users.isLoading ? (
          <p className="p-6 text-sm text-muted-foreground">正在加载账号…</p>
        ) : users.isError ? (
          <p className="p-6 text-sm text-destructive">{getApiError(users.error).message}</p>
        ) : users.data?.map((user) => (
          <div key={user.id} className="grid items-center gap-4 border-b border-border/70 px-5 py-4 last:border-0 md:grid-cols-[minmax(180px,1fr)_180px_120px_110px]">
            <div className="flex min-w-0 items-center gap-3">
              <div className={`flex size-9 shrink-0 items-center justify-center rounded-xl ${user.isActive ? 'bg-emerald-50 text-emerald-700' : 'bg-secondary text-muted-foreground'}`}>
                {user.role === 'admin' ? <ShieldCheck className="size-4" /> : <UserCheck className="size-4" />}
              </div>
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold">{user.username}</div>
                <div className="mt-0.5 text-xs text-muted-foreground">{user.isActive ? '可正常登录' : '账号已停用'}</div>
                <div className="mt-1.5 flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="shrink-0">用户身份码</span>
                  <code className="truncate font-mono text-[11px] text-foreground/70" title={user.id}>{user.id}</code>
                  <button
                    type="button"
                    className="inline-flex size-6 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                    aria-label={`复制 ${user.username} 的用户身份码`}
                    title="复制用户身份码"
                    onClick={() => void copyUserIdentity(user.id)}
                  >
                    <Copy className="size-3.5" />
                  </button>
                </div>
              </div>
            </div>
            <Select
              value={user.role}
              onChange={(event) => update.mutate({ id: user.id, data: { role: event.target.value as UserRole } })}
            >
              {roles.map((item) => <option key={item} value={item}>{roleLabels[item]}</option>)}
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => update.mutate({ id: user.id, data: { isActive: !user.isActive } })}
            >
              {user.isActive ? '停用账号' : '重新启用'}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setResetTarget({ id: user.id, username: user.username })}>
              <KeyRound className="size-4" />重置密码
            </Button>
          </div>
        ))}
      </section>

      <Dialog open={Boolean(resetTarget)} onOpenChange={(open) => !open && setResetTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <div className="mb-2 flex size-10 items-center justify-center rounded-xl bg-accent text-primary">
              <UserRoundCog className="size-5" />
            </div>
            <DialogTitle>重置 {resetTarget?.username} 的密码</DialogTitle>
            <DialogDescription>保存后，该账号的旧登录会话会立即失效。</DialogDescription>
          </DialogHeader>
          <label>
            <span className="field-label">新密码</span>
            <Input type="password" value={nextPassword} onChange={(event) => setNextPassword(event.target.value)} placeholder="至少 8 位" autoFocus />
          </label>
          <DialogFooter>
            <Button variant="outline" onClick={() => setResetTarget(null)}>取消</Button>
            <Button
              disabled={!resetTarget || nextPassword.length < 8 || resetPassword.isPending}
              onClick={() => resetTarget && resetPassword.mutate({ id: resetTarget.id, password: nextPassword })}
            >
              确认重置
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
