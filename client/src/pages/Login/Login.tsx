import { useState, type FormEvent } from 'react';
import { Images, LockKeyhole, UserRound } from 'lucide-react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { getApiError } from '@client/src/api/client';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { useAuth } from '@client/src/lib/auth';


const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  if (user) return <Navigate to="/" replace />;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!username.trim() || !password) {
      setError('请输入账号和密码');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      await login(username.trim(), password);
      const destination = (location.state as { from?: string } | null)?.from || '/';
      navigate(destination, { replace: true });
    } catch (requestError) {
      setError(getApiError(requestError).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden bg-background px-4 py-10">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,hsl(221_75%_55%/0.12),transparent_36%),radial-gradient(circle_at_bottom_right,hsl(160_60%_45%/0.09),transparent_32%)]" />
      <section className="relative w-full max-w-md overflow-hidden rounded-2xl border border-border bg-card shadow-xl">
        <div className="border-b border-border bg-gradient-to-br from-primary/10 via-card to-card px-7 pb-6 pt-7">
          <div className="flex size-11 items-center justify-center rounded-xl bg-primary shadow-md">
            <Images className="size-5 text-primary-foreground" />
          </div>
          <h1 className="mt-5 text-2xl font-semibold tracking-tight">登录标签图片仓库</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            使用管理员分配的账号登录，工作端由账号角色决定。
          </p>
        </div>
        <form className="space-y-5 p-7" onSubmit={submit}>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">账号</span>
            <div className="relative">
              <UserRound className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="请输入账号"
                className="h-10 pl-9"
                autoComplete="username"
              />
            </div>
          </label>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">密码</span>
            <div className="relative">
              <LockKeyhole className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="至少 8 位密码"
                className="h-10 pl-9"
                autoComplete="current-password"
              />
            </div>
          </label>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="h-10 w-full" disabled={submitting}>
            {submitting ? '登录中...' : '登录'}
          </Button>
        </form>
      </section>
    </main>
  );
};

export default Login;
