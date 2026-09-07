import { useState, type FormEvent } from 'react';
import { Images, LockKeyhole, Sparkles, UserRound } from 'lucide-react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { getApiError } from '@client/src/api/client';
import { register } from '@client/src/api/auth';
import { Button } from '@client/src/components/ui/button';
import { Input } from '@client/src/components/ui/input';
import { useAuth } from '@client/src/lib/auth';
import { PRODUCT_NAME } from '@client/src/lib/branding';


const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  if (user) return <Navigate to="/" replace />;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting) return;
    if (!username.trim() || !password) {
      setError('请输入账号和密码');
      return;
    }
    if (isRegistering && (username.trim().length < 3 || username.trim().length > 100)) {
      setError('账号长度需要为 3–100 个字符');
      return;
    }
    if (isRegistering && (password.length < 8 || password.length > 200 || !password.trim())) {
      setError('密码需要为 8–200 个字符，且不能全部为空格');
      return;
    }
    if (isRegistering && password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }
    setSubmitting(true);
    setError('');
    setNotice('');
    try {
      if (isRegistering) {
        const created = await register(username.trim(), password, confirmPassword);
        setUsername(created.username);
        setPassword('');
        setConfirmPassword('');
        setIsRegistering(false);
        setNotice('注册成功，请使用新账号登录');
        return;
      }
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
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,hsl(42_32%_92%/0.82),transparent_34rem),radial-gradient(circle_at_bottom_right,hsl(222_18%_92%/0.52),transparent_30rem)]" />
      <div className="absolute left-1/2 top-1/2 h-[32rem] w-[32rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-border/50 bg-white/30 blur-3xl" />
      <section className="relative w-full max-w-md overflow-hidden rounded-[30px] border border-white/85 bg-card/95 shadow-2xl shadow-slate-900/10 backdrop-blur-xl">
        <div className="border-b border-border/70 bg-gradient-to-br from-secondary/80 via-card to-card px-7 pb-6 pt-7">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-foreground shadow-md shadow-foreground/15">
            <Images className="size-5 text-primary-foreground" />
          </div>
          <p className="mt-5 flex items-center gap-1.5 text-xs font-semibold tracking-[0.12em] text-muted-foreground"><Sparkles className="size-3.5" />{PRODUCT_NAME}</p>
          <h1 className="mt-1.5 text-2xl font-semibold tracking-tight">{isRegistering ? '注册账号' : '欢迎登录'}</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            {isRegistering ? '注册后即可搜索、浏览和下载素材。' : '一个入口完成素材搜索、上传和业务关系维护。'}
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
                required
                maxLength={100}
                disabled={submitting}
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
                autoComplete={isRegistering ? 'new-password' : 'current-password'}
                required
                maxLength={200}
                disabled={submitting}
              />
            </div>
          </label>
          {isRegistering && (
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium">确认密码</span>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="请再次输入密码"
                className="h-11"
                autoComplete="new-password"
                required
                maxLength={200}
                disabled={submitting}
              />
            </label>
          )}
          {notice && <p role="status" className="text-sm text-emerald-700">{notice}</p>}
          {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="h-11 w-full" disabled={submitting}>
            {isRegistering ? (submitting ? '注册中...' : '注册账号') : (submitting ? '登录中...' : '登录')}
          </Button>
          <Button type="button" variant="ghost" className="w-full" disabled={submitting} onClick={() => {
            setIsRegistering(!isRegistering);
            setPassword('');
            setConfirmPassword('');
            setError('');
            setNotice('');
          }}>
            {isRegistering ? '已有账号？返回登录' : '还没有账号？注册账号'}
          </Button>
        </form>
      </section>
    </main>
  );
};

export default Login;
