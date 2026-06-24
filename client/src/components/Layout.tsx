import { useState } from 'react';
import { BriefcaseBusiness, FileClock, Images, LogOut, Menu, Palette, ScrollText, Shield, X } from 'lucide-react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import { Button } from '@client/src/components/ui/button';
import { useAuth } from '@client/src/lib/auth';


const Layout = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isDesigner = user?.role === 'designer';
  const canManageAssets = user?.role === 'designer' || user?.role === 'admin';

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="flex h-screen w-screen flex-col bg-background">
      <header className="sticky top-0 z-50 flex h-14 items-center border-b border-border bg-card/80 px-6 backdrop-blur-md">
        <NavLink to="/" className="flex items-center gap-2.5">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary">
            <Images className="size-4 text-primary-foreground" />
          </div>
          <span className="text-base font-semibold tracking-tight text-foreground">
            标签图片仓库
          </span>
        </NavLink>

        <nav className="ml-8 hidden items-center md:flex">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
              }`
            }
          >
            图片库
          </NavLink>
          {user?.role === 'admin' && (
            <NavLink
              to="/admin/users"
              className={({ isActive }) =>
                `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-secondary'
                }`
              }
            >
              用户管理
            </NavLink>
          )}
          {canManageAssets && (
            <NavLink
              to="/trash"
              className={({ isActive }) =>
                `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-secondary'
                }`
              }
            >
              <FileClock className="mr-1 inline size-3.5" />
              回收站
            </NavLink>
          )}
          {user?.role === 'admin' && (
            <NavLink
              to="/admin/audit"
              className={({ isActive }) =>
                `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-secondary'
                }`
              }
            >
              <ScrollText className="mr-1 inline size-3.5" />
              审计日志
            </NavLink>
          )}
        </nav>

        <div className="ml-auto hidden items-center gap-2 md:flex">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-1.5">
            {user?.role === 'admin'
              ? <Shield className="size-4 text-primary" />
              : isDesigner ? <Palette className="size-4 text-primary" />
              : <BriefcaseBusiness className="size-4 text-primary" />}
            <div className="leading-tight">
              <div className="text-xs font-medium">
                {user?.role === 'admin' ? '管理员' : isDesigner ? '设计师端' : '业务端'}
              </div>
              <div className="max-w-28 truncate text-[10px] text-muted-foreground">
                {user?.username}
              </div>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            <LogOut className="mr-1 size-4" />
            退出/切换
          </Button>
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="ml-auto md:hidden"
          aria-label={mobileMenuOpen ? '关闭导航菜单' : '打开导航菜单'}
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-navigation"
          onClick={() => setMobileMenuOpen((value) => !value)}
        >
          {mobileMenuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </Button>
      </header>

      {mobileMenuOpen && (
        <nav
          id="mobile-navigation"
          aria-label="移动端主导航"
          className="border-b border-border bg-card px-4 py-2 md:hidden"
        >
          <NavLink
            to="/"
            onClick={() => setMobileMenuOpen(false)}
            className="block rounded-md px-3 py-2 text-sm font-medium"
          >
            图片库
          </NavLink>
          {canManageAssets && (
            <NavLink
              to="/trash"
              onClick={() => setMobileMenuOpen(false)}
              className="mt-1 block rounded-md px-3 py-2 text-sm font-medium"
            >
              回收站
            </NavLink>
          )}
          {user?.role === 'admin' && (
            <>
              <NavLink
                to="/admin/users"
                onClick={() => setMobileMenuOpen(false)}
                className="mt-1 block rounded-md px-3 py-2 text-sm font-medium"
              >
                用户管理
              </NavLink>
              <NavLink
                to="/admin/audit"
                onClick={() => setMobileMenuOpen(false)}
                className="mt-1 block rounded-md px-3 py-2 text-sm font-medium"
              >
                审计日志
              </NavLink>
            </>
          )}
          <div className="mt-2 flex items-center justify-between border-t border-border pt-2">
            <span className="text-xs text-muted-foreground">
              {user?.role === 'admin' ? '管理员' : isDesigner ? '设计师端' : '业务端'} · {user?.username}
            </span>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOut className="mr-1 size-4" />
              切换
            </Button>
          </div>
        </nav>
      )}

      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
