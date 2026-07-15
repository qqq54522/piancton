import { useState, type FormEvent } from 'react';
import { Images, LockKeyhole, Sparkles, UserRound } from 'lucide-react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { getApiError } from '@client/src/api/client';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { useAuth } from '@client/src/lib/auth';
import { PRODUCT_NAME } from '@client/src/lib/branding';


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
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,hsl(224_76%_54%/0.14),transparent_34rem),radial-gradient(circle_at_bottom_right,hsl(199_85%_60%/0.10),transparent_30rem)]" />
      <section className="relative w-full max-w-md overflow-hidden rounded-[28px] border border-white/80 bg-card/95 shadow-2xl shadow-slate-900/10 backdrop-blur">
        <div className="border-b border-border/70 bg-gradient-to-br from-primary/10 via-card to-card px-7 pb-6 pt-7">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-indigo-400 shadow-md shadow-primary/20">
            <Images className="size-5 text-primary-foreground" />
          </div>
          <p className="mt-5 flex items-center gap-1.5 text-xs font-semibold tracking-[0.08em] text-primary"><Sparkles className="size-3.5" />{PRODUCT_NAME}</p>
          <h1 className="mt-1.5 text-2xl font-semibold tracking-tight">欢迎登录</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            一个入口完成素材搜索、上传和业务关系维护。
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
                className="h-11 pl-9"
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
                className="h-11 pl-9"
                autoComplete="current-password"
              />
            </div>
          </label>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="h-11 w-full" disabled={submitting}>
            {submitting ? '登录中...' : '登录'}
          </Button>
        </form>
      </section>
    </main>
  );
};

export default Login;
