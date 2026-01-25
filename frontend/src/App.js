import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import './App.css';
import { ThemeProvider } from './contexts/ThemeContext';
import { RealtimeProvider } from './contexts/RealtimeContext';
import LoginPage from './components/LoginPage';
import AuthCallback from './components/AuthCallback';
import ProtectedRoute from './components/ProtectedRoute';
import MainLayout from './components/MainLayout';
import PageLayout from './components/PageLayout';
import ProfilePage from './components/ProfilePage';
import SettingsPage from './components/SettingsPage';
import TeamsPage from './components/TeamsPage';
import AdminPage from './components/AdminPage';
import SearchResultsPage from './components/SearchResultsPage';
import CommandPalette from './components/CommandPalette';
import { Toaster } from './components/ui/sonner';

function AppRouter() {
  const location = useLocation();
  
  // Check URL fragment for session_id BEFORE rendering routes
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <MainLayout view="dashboard" user={user} />
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/all-tickets"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <MainLayout view="all-tickets" user={user} />
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/open-tickets"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <MainLayout view="open-tickets" user={user} />
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/waiting-tickets"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <MainLayout view="waiting-tickets" user={user} />
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/closed-tickets"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <MainLayout view="closed-tickets" user={user} />
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <PageLayout user={user}>
                  <ProfilePage user={user} />
                </PageLayout>
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <PageLayout user={user}>
                  <SettingsPage user={user} />
                </PageLayout>
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/teams"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <PageLayout user={user}>
                  <TeamsPage user={user} />
                </PageLayout>
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <PageLayout user={user}>
                  <AdminPage user={user} />
                </PageLayout>
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/search"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <PageLayout user={user}>
                  <SearchResultsPage user={user} />
                </PageLayout>
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

// Create a context to share command palette state
export const CommandPaletteContext = React.createContext({
  openCommandPalette: () => {},
});

// Wrapper component that provides realtime context to authenticated routes
function AppWithRealtime({ user, children }) {
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  // Global keyboard shortcut for Command Palette
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Cmd+K (Mac) or Ctrl+K (Windows/Linux)
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Store current user ID for presence filtering
  useEffect(() => {
    if (user?.user_id) {
      window.__CURRENT_USER_ID__ = user.user_id;
    }
  }, [user]);

  const openCommandPalette = useCallback(() => {
    setCommandPaletteOpen(true);
  }, []);

  return (
    <RealtimeProvider user={user}>
      <CommandPaletteContext.Provider value={{ openCommandPalette }}>
        {children}
      </CommandPaletteContext.Provider>
      <CommandPalette 
        isOpen={commandPaletteOpen} 
        onClose={() => setCommandPaletteOpen(false)} 
      />
    </RealtimeProvider>
  );
}

function App() {
  return (
    <ThemeProvider>
      <Router>
        <div className="App min-h-screen bg-background">
          <AppRouter />
          <Toaster richColors position="top-right" />
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;
