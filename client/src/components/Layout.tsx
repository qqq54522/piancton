import { useState } from 'react';
import {
  BriefcaseBusiness,
  FileClock,
  Fingerprint,
  BarChart3,
  KeyRound,
  LayoutGrid,
  LibraryBig,
  LogOut,
  Menu,
  Palette,
  ScrollText,
  Search,
  Tags,
  Shield,
  Upload,
  Users,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import { Avatar, AvatarFallback } from '@client/src/components/ui/avatar';
import { Button } from '@client/src/components/ui/button';
import { PianctonAgentMark } from '@client/src/components/PianctonAgentMark';
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
import { usePageViewTracking } from '@client/src/lib/usePageViewTracking';

const sidebarNavClass = ({ isActive }: { isActive: boolean }) => (
  `sidebar-nav-pill group relative flex size-12 items-center justify-center rounded-full ${
    isActive
      ? 'bg-foreground text-background shadow-md shadow-foreground/10'
      : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
  }`
);

const mobileNavClass = ({ isActive }: { isActive: boolean }) => (
  `flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium ${
    isActive ? 'bg-accent text-accent-foreground' : 'text-muted-foreground'
  }`
);

interface SidebarNavItemProps {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

const SidebarNavItem = ({ to, label, icon: Icon, end }: SidebarNavItemProps) => (
  <NavLink to={to} end={end} className={sidebarNavClass} aria-label={label}>
    <Icon className="size-5" />
    <span className="pointer-events-none absolute left-[58px] top-1/2 z-50 -translate-y-1/2 whitespace-nowrap rounded-xl bg-foreground px-3 py-2 text-sm font-semibold text-background opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
      {label}
    </span>
  </NavLink>
);

const SidebarActionItem = ({
  label,
  icon: Icon,
  onClick,
}: {
  label: string;
  icon: LucideIcon;
  onClick: () => void;
}) => (
  <button
    type="button"
    className="sidebar-nav-pill group relative flex size-12 items-center justify-center rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground"
    aria-label={label}
    onClick={onClick}
  >
    <Icon className="size-5" />
    <span className="pointer-events-none absolute left-[58px] top-1/2 z-50 -translate-y-1/2 whitespace-nowrap rounded-xl bg-foreground px-3 py-2 text-sm font-semibold text-background opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
      {label}
    </span>
  </button>
);

const Layout = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  usePageViewTracking();
  const isDesigner = user?.role === 'designer';
  const canManageAssets = user?.role === 'designer' || user?.role === 'admin';
  const canViewSearchOps = canManageAssets;
  const searchOpsPath = user?.role === 'admin' ? '/admin/search-ops' : '/search-ops';
  const isBusiness = user?.role === 'business';
  const roleLabel = user?.role === 'admin' ? '管理员' : isDesigner ? '设计师' : '业务用户';
  const RoleIcon = user?.role === 'admin' ? Shield : isDesigner ? Palette : BriefcaseBusiness;
  const navItems = [
    { to: '/', label: '素材库', icon: LayoutGrid, end: true, show: true },
    { to: '/admin/concepts', label: '卖点管理', icon: LibraryBig, show: user?.role === 'admin' },
    { to: '/admin/channels', label: '渠道管理', icon: Tags, show: user?.role === 'admin' },
    { to: searchOpsPath, label: '搜索运营', icon: Search, show: canViewSearchOps },
    { to: '/admin/api-center', label: 'API 中心', icon: KeyRound, show: user?.role === 'admin' },
    { to: '/admin/usage', label: '使用统计', icon: BarChart3, show: user?.role === 'admin' },
    { to: '/admin/identity-codes', label: '身份码管理', icon: Fingerprint, show: user?.role === 'admin' },
    { to: '/admin/users', label: '用户管理', icon: Users, show: user?.role === 'admin' },
    { to: '/trash', label: '回收站', icon: FileClock, show: canManageAssets },
    { to: '/admin/audit', label: '审计日志', icon: ScrollText, show: user?.role === 'admin' },
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const handleOpenUpload = () => {
    navigate('/', { state: { openUpload: true } });
    window.dispatchEvent(new Event('piancton:open-upload'));
  };

  return (
    <div className="flex min-h-screen w-full bg-transparent">
      {!isBusiness && (
        <>
          <aside className="fixed inset-y-0 left-0 z-50 hidden w-20 flex-col items-center border-r border-border/70 bg-card/90 py-5 shadow-[1px_0_0_rgba(15,23,42,0.02)] backdrop-blur-xl sm:flex">
            <NavLink to="/" className="sidebar-nav-pill group relative mb-7 flex size-12 items-center justify-center rounded-[1.15rem] border border-border bg-white shadow-md shadow-foreground/10 hover:bg-secondary/70" aria-label={PRODUCT_NAME}>
              <PianctonAgentMark variant="flat" size="sm" />
              <span className="pointer-events-none absolute left-[58px] top-1/2 z-50 -translate-y-1/2 whitespace-nowrap rounded-xl bg-foreground px-3 py-2 text-sm font-semibold text-background opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
                {PRODUCT_NAME}
              </span>
            </NavLink>

            <nav className="flex flex-1 flex-col items-center gap-3" aria-label="主导航">
              {canManageAssets && (
                <SidebarActionItem label="上传主图" icon={Upload} onClick={handleOpenUpload} />
              )}
              {navItems.filter((item) => item.show).map((item) => (
                <SidebarNavItem
                  key={item.to}
                  to={item.to}
                  label={item.label}
                  icon={item.icon}
                  end={item.end}
                />
              ))}
            </nav>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="sidebar-nav-pill group relative mt-5 flex size-12 items-center justify-center rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground"
                  aria-label="打开账号菜单"
                >
                  <Avatar className="size-9 border border-border bg-white" data-sidebar-icon>
                    <AvatarFallback className="bg-white text-foreground">
                      <RoleIcon className="size-4" />
                    </AvatarFallback>
                  </Avatar>
                  <span className="pointer-events-none absolute left-[58px] top-1/2 z-50 -translate-y-1/2 whitespace-nowrap rounded-xl bg-foreground px-3 py-2 text-sm font-semibold text-background opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
                    {user?.username} · {roleLabel}
                  </span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" side="right" className="w-52 rounded-xl p-1.5">
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
          </aside>

          <header className="sticky top-0 z-50 border-b border-border/80 bg-card/90 backdrop-blur-xl sm:hidden">
            <div className="flex h-16 items-center px-4">
              <NavLink to="/" className="group flex shrink-0 items-center gap-3">
                <div className="flex size-9 items-center justify-center rounded-xl border border-border bg-white shadow-sm transition-transform group-hover:scale-[1.03]">
                  <PianctonAgentMark variant="flat" size="sm" className="scale-75" />
                </div>
                <div className="leading-tight">
                  <span className="block text-sm font-semibold tracking-tight text-foreground">{PRODUCT_NAME}</span>
                  <span className="block text-[10px] tracking-[0.08em] text-muted-foreground">{PRODUCT_DESCRIPTOR}</span>
                </div>
              </NavLink>
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto"
            aria-label={mobileMenuOpen ? '关闭导航菜单' : '打开导航菜单'}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMobileMenuOpen((value) => !value)}
          >
            {mobileMenuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
          </Button>
            </div>

        {mobileMenuOpen && (
          <nav id="mobile-navigation" aria-label="移动端主导航" className="border-t border-border/70 bg-card px-4 py-3">
            <div className="mx-auto grid max-w-xl gap-1">
              <NavLink to="/" end onClick={() => setMobileMenuOpen(false)} className={mobileNavClass}>
                <LayoutGrid className="size-4" />素材库
              </NavLink>
              {user?.role === 'admin' && (
                <NavLink to="/admin/concepts" onClick={() => setMobileMenuOpen(false)} className={mobileNavClass}>
                  <LibraryBig className="size-4" />卖点管理
                </NavLink>
              )}
              {user?.role === 'admin' && (
                <NavLink to="/admin/channels" onClick={() => setMobileMenuOpen(false)} className={mobileNavClass}>
                  <Tags className="size-4" />渠道管理
                </NavLink>
              )}
              {canViewSearchOps && (
                <NavLink to={searchOpsPath} onClick={() => setMobileMenuOpen(false)} className={mobileNavClass}>
                  <Search className="size-4" />搜索运营
                </NavLink>
              )}
              {user?.role === 'admin' && (
                <NavLink to="/admin/api-center" onClick={() => setMobileMenuOpen(false)} className={mobileNavClass}>
                  <KeyRound className="size-4" />API 中心
                </NavLink>
              )}
              {user?.role === 'admin' && (
                <NavLink to="/admin/usage" onClick={() => setMobileMenuOpen(false)} className={mobileNavClass}>
                  <BarChart3 className="size-4" />使用统计
                </NavLink>
              )}
              {user?.role === 'admin' && (
                <NavLink to="/admin/identity-codes" onClick={() => setMobileMenuOpen(false)} className={mobileNavClass}>
                  <Fingerprint className="size-4" />身份码管理
                </NavLink>
              )}
              {user?.role === 'admin' && (
                <NavLink to="/admin/users" onClick={() => setMobileMenuOpen(false)} className={mobileNavClass}>
                  <Users className="size-4" />用户管理
                </NavLink>
              )}
              {canManageAssets && (
                <button
                  type="button"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    handleOpenUpload();
                  }}
                  className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground"
                >
                  <Upload className="size-4" />上传主图
                </button>
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
        </>
      )}

      <main className={`min-h-0 flex-1 ${!isBusiness ? 'sm:pl-20' : ''}`}>
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
