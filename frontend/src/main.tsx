import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import './index.css';

import { useAuthStore } from './store';
import Layout from './components/layout/Layout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import BotsPage from './pages/BotsPage';
import BacktestPage from './pages/BacktestPage';
import TradesPage from './pages/TradesPage';
import JournalPage from './pages/JournalPage';
import MarketsPage from './pages/MarketsPage';
import SettingsPage from './pages/SettingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

function RequireAuth({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#111827',
              color: '#e8f0fe',
              border: '1px solid #1e2d45',
              borderRadius: '10px',
              fontSize: '13px',
            },
            success: { iconTheme: { primary: '#00ff87', secondary: '#111827' } },
            error:   { iconTheme: { primary: '#ff3b6b', secondary: '#111827' } },
          }}
        />
        <Routes>
          <Route path="/login"    element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/" element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }>
            <Route index                element={<DashboardPage />} />
            <Route path="bots"          element={<BotsPage />} />
            <Route path="backtest"      element={<BacktestPage />} />
            <Route path="trades"        element={<TradesPage />} />
            <Route path="journal"       element={<JournalPage />} />
            <Route path="markets"       element={<MarketsPage />} />
            <Route path="settings"      element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>
);
