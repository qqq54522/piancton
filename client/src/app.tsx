import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';

import Layout from './components/Layout';
import { AdminRoute, DesignerRoute, ProtectedRoute } from './lib/auth';


const AdminUsers = lazy(() => import('./pages/AdminUsers/AdminUsers'));
const AdminAudit = lazy(() => import('./pages/AdminAudit/AdminAudit'));
const ImageDetail = lazy(() => import('./pages/ImageDetail/ImageDetail'));
const ImageHome = lazy(() => import('./pages/ImageHome/ImageHome'));
const Login = lazy(() => import('./pages/Login/Login'));
const NotFound = lazy(() => import('./pages/NotFound/NotFound'));
const TagExplorePage = lazy(() => import('./pages/TagExplorePage/TagExplorePage'));
const Trash = lazy(() => import('./pages/Trash/Trash'));

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
          <Route path="tag/:tagId" element={<TagExplorePage />} />
          <Route path="image/:id" element={<ImageDetail />} />
          <Route element={<DesignerRoute />}>
            <Route path="trash" element={<Trash />} />
          </Route>
          <Route element={<AdminRoute />}>
            <Route path="admin/users" element={<AdminUsers />} />
            <Route path="admin/audit" element={<AdminAudit />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  </Suspense>
);

export default RoutesComponent;
