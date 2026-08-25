import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes, useParams } from 'react-router-dom';

import Layout from './components/Layout';
import { AdminRoute, DesignerRoute, ProtectedRoute } from './lib/auth';


const AdminUsers = lazy(() => import('./pages/AdminUsers/AdminUsers'));
const AdminAudit = lazy(() => import('./pages/AdminAudit/AdminAudit'));
const AdminApiCenter = lazy(() => import('./pages/AdminApiCenter/AdminApiCenter'));
const AdminIdentityCodes = lazy(() => import('./pages/AdminIdentityCodes/AdminIdentityCodes'));
const AdminChannels = lazy(() => import('./pages/AdminChannels/AdminChannels'));
const AdminConcepts = lazy(() => import('./pages/AdminConcepts/AdminConcepts'));
const AdminSearchOps = lazy(() => import('./pages/AdminSearchOps/AdminSearchOps'));
const ImageDetail = lazy(() => import('./pages/ImageDetail/ImageDetail'));
const ImageHome = lazy(() => import('./pages/ImageHome/ImageHome'));
const Login = lazy(() => import('./pages/Login/Login'));
const NotFound = lazy(() => import('./pages/NotFound/NotFound'));
const Trash = lazy(() => import('./pages/Trash/Trash'));

const SharedAssetRedirect = () => {
  const { code } = useParams<{ code: string }>();
  return <Navigate to={`/image/${code ?? ''}`} replace />;
};

const PageFallback = () => (
  <div className="grid min-h-[50vh] place-items-center text-sm text-muted-foreground">
    正在加载...
  </div>
);

const RoutesComponent = () => (
  <Suspense fallback={<PageFallback />}>
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<ImageHome />} />
          <Route path="image/:id" element={<ImageDetail />} />
          <Route path="share/:code" element={<SharedAssetRedirect />} />
          <Route element={<DesignerRoute />}>
            <Route path="trash" element={<Trash />} />
            <Route path="search-ops" element={<AdminSearchOps />} />
            <Route path="admin/search-ops" element={<AdminSearchOps />} />
          </Route>
          <Route element={<AdminRoute />}>
            <Route path="admin/users" element={<AdminUsers />} />
            <Route path="admin/audit" element={<AdminAudit />} />
            <Route path="admin/channels" element={<AdminChannels />} />
            <Route path="admin/api-center" element={<AdminApiCenter />} />
            <Route path="admin/identity-codes" element={<AdminIdentityCodes />} />
            <Route path="admin/concepts" element={<AdminConcepts />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  </Suspense>
);

export default RoutesComponent;
