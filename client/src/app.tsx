import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';

import Layout from './components/Layout';
import { AdminRoute, BusinessRoute, DesignerRoute, ProtectedRoute } from './lib/auth';


const AdminUsers = lazy(() => import('./pages/AdminUsers/AdminUsers'));
const AdminAudit = lazy(() => import('./pages/AdminAudit/AdminAudit'));
const AdminUsage = lazy(() => import('./pages/AdminUsage/AdminUsage'));
const AdminIdentityCodes = lazy(() => import('./pages/AdminIdentityCodes/AdminIdentityCodes'));
const AdminChannels = lazy(() => import('./pages/AdminChannels/AdminChannels'));
const AdminConcepts = lazy(() => import('./pages/AdminConcepts/AdminConcepts'));
const AdminSearchOps = lazy(() => import('./pages/AdminSearchOps/AdminSearchOps'));
const AdminAnnouncements = lazy(() => import('./pages/AdminAnnouncements/AdminAnnouncements'));
const ImageDetail = lazy(() => import('./pages/ImageDetail/ImageDetail'));
const ImageHome = lazy(() => import('./pages/ImageHome/ImageHome'));
const Login = lazy(() => import('./pages/Login/Login'));
const MyLikes = lazy(() => import('./pages/MyLikes/MyLikes'));
const MyCollections = lazy(() => import('./pages/MyCollections/MyCollections'));
const MyMessages = lazy(() => import('./pages/MyMessages/MyMessages'));
const NotFound = lazy(() => import('./pages/NotFound/NotFound'));
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
          <Route path="image/:id" element={<ImageDetail />} />
          <Route element={<BusinessRoute />}>
            <Route path="my-likes" element={<MyLikes />} />
            <Route path="my-collections" element={<MyCollections />} />
            <Route path="my-collections/:boardId" element={<MyCollections />} />
            <Route path="my-messages" element={<MyMessages />} />
          </Route>
          <Route element={<DesignerRoute />}>
            <Route path="trash" element={<Trash />} />
            <Route path="search-ops" element={<AdminSearchOps />} />
            <Route path="admin/search-ops" element={<AdminSearchOps />} />
            <Route path="announcements/manage" element={<AdminAnnouncements />} />
          </Route>
          <Route element={<AdminRoute />}>
            <Route path="admin/users" element={<AdminUsers />} />
            <Route path="admin/audit" element={<AdminAudit />} />
            <Route path="admin/channels" element={<AdminChannels />} />
            <Route path="admin/usage" element={<AdminUsage />} />
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
