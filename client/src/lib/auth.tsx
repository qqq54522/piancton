import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import * as authApi from '@client/src/api/auth';
import type { User, UserRole } from '@client/src/types/api';


export const ROLE_SUBJECT = 'role';
const ROLE_LEVEL: Record<UserRole, number> = { business: 1, designer: 2, admin: 3 };

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  ability: { can: (action: string, subject?: string) => boolean };
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    authApi.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setIsLoading(false));
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    isLoading,
    login: async (username, password) => {
      const result = await authApi.login(username, password);
      setUser(result.user);
    },
    logout: async () => {
      try {
        await authApi.logout();
      } finally {
        setUser(null);
      }
    },
    ability: {
      can: (action, subject) => {
        if (!user) return false;
        if (subject === ROLE_SUBJECT && action in ROLE_LEVEL) {
          return ROLE_LEVEL[user.role] >= ROLE_LEVEL[action as UserRole];
        }
        return true;
      },
    },
  }), [user, isLoading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function CanRole({
  children,
  roles,
}: PropsWithChildren<{ roles: UserRole[] }>) {
  const { user } = useAuth();
  return user && roles.some((role) => ROLE_LEVEL[user.role] >= ROLE_LEVEL[role])
    ? <>{children}</>
    : null;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth 必须在 AuthProvider 内使用');
  return value;
}

export function ProtectedRoute() {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) return <div className="grid min-h-screen place-items-center">正在加载...</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}

export function AdminRoute() {
  return <RoleRoute minRole="admin" />;
}

export function DesignerRoute() {
  return <RoleRoute minRole="designer" />;
}

function RoleRoute({ minRole }: { minRole: UserRole }) {
  const { user } = useAuth();
  return user && ROLE_LEVEL[user.role] >= ROLE_LEVEL[minRole]
    ? <Outlet />
    : <Navigate to="/" replace />;
}
