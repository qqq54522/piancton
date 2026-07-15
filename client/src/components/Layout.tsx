import { useState } from 'react';
import {
  BriefcaseBusiness,
  ChevronDown,
  FileClock,
  Images,
  LayoutGrid,
  LogOut,
  Menu,
  Palette,
  ScrollText,
  Search,
  Shield,
  Users,
  X,
} from 'lucide-react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import { Avatar, AvatarFallback } from '@client/src/components/ui/avatar';
import { Button } from '@client/src/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@client/src/components/ui/dropdown-menu';
import { useAuth } from '@client/src/lib/auth';
import { PRODUCT_DESCRIPTOR, PRODUCT_NAME } from '@client/src/lib/branding';

const navClass = ({ isActive }: { isActive: boolean }) => (
  `inline-flex h-9 items-center gap-1.5 rounded-lg px-3 text-sm font-medium transition-colors ${
    isActive
      ? 'bg-accent text-accent-foreground'
      : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
  }`
);

const mobileNavClass = ({ isActive }: { isActive: boolean }) => (
  `flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium ${
    isActive ? 'bg-accent text-accent-foreground' : 'text-muted-foreground'
  }`
);

const Layout = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isDesigner = user?.role === 'designer';
  const canManageAssets = user?.role === 'designer' || user?.role === 'admin';
  const roleLabel = user?.role === 'admin' ? '管理员' : isDesigner ? '设计师' : '业务用户';
  const RoleIcon = user?.role === 'admin' ? Shield : isDesigner ? Palette : BriefcaseBusiness;

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="flex min-h-screen w-full flex-col bg-transparent">
      <header className="sticky top-0 z-50 border-b border-border/80 bg-card/90 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1536px] items-center px-4 sm:px-6 lg:px-8">
          <NavLink to="/" className="group flex shrink-0 items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-indigo-400 shadow-sm shadow-primary/20 transition-transform group-hover:scale-[1.03]">
              <Images className="size-[18px] text-primary-foreground" />
            </div>
            <div className="hidden leading-tight sm:block">
              <span className="block text-sm font-semibold tracking-tight text-foreground">{PRODUCT_NAME}</span>
              <span className="block text-[10px] tracking-[0.08em] text-muted-foreground">{PRODUCT_DESCRIPTOR}</span>
            </div>
          </NavLink>

          <nav className="ml-8 hidden items-center gap-1 lg:flex" aria-label="主导航">
            <NavLink to="/" className={navClass} end>
              <LayoutGrid className="size-4" />素材库
            </NavLink>
            {user?.role === 'admin' && (
              <NavLink to="/admin/search-ops" className={navClass}>
                <Search className="size-4" />搜索运营
              </NavLink>
            )}
            {user?.role === 'admin' && (
              <NavLink to="/admin/users" className={navClass}>
                <Users className="size-4" />用户
              </NavLink>
            )}
            {canManageAssets && (
              <NavLink to="/trash" className={navClass}>
                <FileClock className="size-4" />回收站
              </NavLink>
            )}
            {user?.role === 'admin' && (
              <NavLink to="/admin/audit" className={navClass}>
                <ScrollText className="size-4" />审计
              </NavLink>
            )}
          </nav>

          <div className="ml-auto hidden items-center lg:flex">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="h-11 gap-2 px-2.5" aria-label="打开账号菜单">
                  <Avatar className="size-8 border border-primary/15 bg-accent">
                    <AvatarFallback className="bg-accent text-accent-foreground">
                      <RoleIcon className="size-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="max-w-32 text-left leading-tight">
                    <div className="truncate text-xs font-semibold text-foreground">{user?.username}</div>
                    <div className="text-[10px] font-normal text-muted-foreground">{roleLabel}</div>
                  </div>
                  <ChevronDown className="size-3.5 text-muted-foreground" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52 rounded-xl p-1.5">
                <DropdownMenuLabel className="px-2.5 py-2">
                  <span className="block text-xs font-semibold">{user?.username}</span>
                  <span className="mt-0.5 block text-[11px] font-normal text-muted-foreground">当前身份：{roleLabel}</span>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="rounded-lg px-2.5 py-2" onClick={handleLogout}>
                  <LogOut className="size-4" />退出并切换账号
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          <Button
            variant="ghost"
            size="icon"
            className="ml-auto lg:hidden"
            aria-label={mobileMenuOpen ? '关闭导航菜单' : '打开导航菜单'}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMobileMenuOpen((value) => !value)}
          >
            {mobileMenuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
          </Button>
        </div>

        {mobileMenuOpen && (
          <nav id="mobile-navigation" aria-label="移动端主导航" className="border-t border-border/70 bg-card px-4 py-3 lg:hidden">
            <div className="mx-auto grid max-w-xl gap-1">
              <NavLink to="/" end onClick={() => setMobileMenuOpen(false)} className={mobileNavClass}>
                <LayoutGrid className="size-4" />素材库
              </NavLink>
              {user?.role === 'admin' && (
                <NavLink to="/admin/search-ops" onClick={() => setMobileMenuOpen(false)} className={mobileNavClass}>
                  <Search className="size-4" />搜索运营
                </NavLink>
              )}
              {user?.role === 'admin' && (
                <NavLink to="/admin/users" onClick={() => setMobileMenuOpen(false)} className={mobileNavClass}>
                  <Users className="size-4" />用户管理
                </NavLink>
              )}
              {canManageAssets && (
                <NavLink to="/trash" onClick={() => setMobileMenuOpen(false)} className={mobileNavClass}>
                  <FileClock className="size-4" />回收站
                </NavLink>
              )}
              {user?.role === 'admin' && (
                <NavLink to="/admin/audit" onClick={() => setMobileMenuOpen(false)} className={mobileNavClass}>
                  <ScrollText className="size-4" />审计日志
                </NavLink>
              )}
              <div className="mt-2 flex items-center justify-between border-t border-border pt-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <RoleIcon className="size-4" />{user?.username} · {roleLabel}
                </div>
                <Button variant="ghost" size="sm" onClick={handleLogout}>
                  <LogOut className="size-4" />切换账号
                </Button>
              </div>
            </div>
          </nav>
        )}
      </header>

      <main className="min-h-0 flex-1">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
