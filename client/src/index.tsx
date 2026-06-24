import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ErrorBoundary } from 'react-error-boundary';
import { createPortal } from 'react-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import RoutesComponent from './app';
import { Toaster } from '@client/src/components/ui/sonner';
import { AuthProvider } from '@client/src/lib/auth';
import './index.css';


const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

const MainApp = () => (
  <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
      <ErrorBoundary
        fallbackRender={({ error, resetErrorBoundary }) => (
          <main className="grid min-h-screen place-items-center p-6">
            <div className="max-w-lg rounded-xl border bg-card p-6 text-center">
              <h1 className="text-lg font-semibold">页面发生错误</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                {error instanceof Error ? error.message : String(error)}
              </p>
              <button className="mt-4 underline" onClick={resetErrorBoundary}>
                重试
              </button>
            </div>
          </main>
        )}
      >
        <RoutesComponent />
        {createPortal(<Toaster />, document.body)}
      </ErrorBoundary>
      </AuthProvider>
    </QueryClientProvider>
  </BrowserRouter>
);

createRoot(document.getElementById('root')!).render(<MainApp />);
