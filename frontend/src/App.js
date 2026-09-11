import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import './App.css';
import { ThemeProvider } from './contexts/ThemeContext';
import { RealtimeProvider, useRealtime } from './contexts/RealtimeContext';
import LoginPage from './components/auth/LoginPage';
import AuthCallback from './components/auth/AuthCallback';
import ProtectedRoute from './components/auth/ProtectedRoute';
import MainLayout from './components/layout/MainLayout';
import PageLayout from './components/layout/PageLayout';
import ProfilePage from './components/pages/ProfilePage';
import SettingsPage from './components/admin/SettingsPage';
import TeamsPage from './components/pages/TeamsPage';
import AdminPage from './components/admin/AdminPage';
import LeavePage from './components/pages/LeavePage';
import SearchResultsPage from './components/pages/SearchResultsPage';
import CommandPalette from './components/common/CommandPalette';
import FeatureRequestsPage from './components/pages/FeatureRequestsPage';
import CustomersPage from './components/pages/CustomersPage';
import AnalyticsPage from './components/pages/AnalyticsPage';
import CSATPage from './components/pages/CSATPage';
import StarredTicketsPage from './components/tickets/StarredTicketsPage';
import CannedResponsesPage from './components/pages/CannedResponsesPage';
import KnowledgeBasePage from './components/pages/KnowledgeBasePage';

// Portal imports
import { PortalAuthProvider } from './portal/PortalAuthContext';
import PortalLayout from './portal/PortalLayout';
import PortalHome from './portal/PortalHome';
import PortalCategory from './portal/PortalCategory';
import PortalHelpTopic from './portal/PortalHelpTopic';
import PortalSubmit from './portal/PortalSubmit';
import PortalLogin from './portal/PortalLogin';
import PortalTickets from './portal/PortalTickets';
import PortalTicketDetail from './portal/PortalTicketDetail';

// KB Docs imports
import PublicDocs from './pages/kb/PublicDocs';
import KBEditor from './pages/KBEditor';
import ReviewConsole from './pages/review/ReviewConsole';
import ReviewPage from './pages/review/ReviewPage';

function AppRouter() {
  const location = useLocation();
  
  // Check URL fragment for session_id BEFORE rendering routes
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      {/* ==================== KB Docs (homepage) ==================== */}
      <Route path="/" element={<PublicDocs />} />
      <Route path="/docs/:slug" element={<PublicDocs />} />

      {/* ==================== Public Portal Routes ==================== */}
      <Route element={<PortalAuthProvider><PortalLayout /></PortalAuthProvider>}>
        <Route path="/portal" element={<PortalHome />} />
        <Route path="/portal/categories" element={<PortalHome />} />
        <Route path="/portal/category/:slug" element={<PortalCategory />} />
        <Route path="/portal/topic/:topicKey" element={<PortalHelpTopic />} />
        <Route path="/portal/submit" element={<PortalSubmit />} />
        <Route path="/portal/login" element={<PortalLogin />} />
        <Route path="/portal/my-tickets" element={<PortalTickets />} />
        <Route path="/portal/my-tickets/:ticketId" element={<PortalTicketDetail />} />
      </Route>

      {/* ==================== Trinity Admin Routes ==================== */}
      <Route path="/login" element={<LoginPage />} />
      {/* CSAT Page - Public route (no auth required) */}
      <Route path="/csat/:token" element={<CSATPage />} />
      {/* KB Editor - Full-page editor (protected) */}
      <Route path="/dashboard/kb-editor" element={<ProtectedRoute>{() => <KBEditor />}</ProtectedRoute>} />
      <Route path="/dashboard/kb-editor/:slug" element={<ProtectedRoute>{() => <KBEditor />}</ProtectedRoute>} />
      <Route path="/dashboard/review" element={<ProtectedRoute>{(user) => <ReviewConsole user={user} />}</ProtectedRoute>} />
      <Route path="/dashboard/review/:slug" element={<ProtectedRoute>{(user) => <ReviewPage user={user} />}</ProtectedRoute>} />
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
        path="/starred-tickets"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <MainLayout view="starred-tickets" user={user} />
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/ai-assigned"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <MainLayout view="ai-assigned" user={user} />
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/inbox/:inboxId"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <MainLayout view="custom-inbox" user={user} />
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
        path="/leaves"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <PageLayout user={user}>
                  <LeavePage user={user} />
                </PageLayout>
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/feature-requests"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <PageLayout user={user}>
                  <FeatureRequestsPage user={user} />
                </PageLayout>
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/canned-responses"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <PageLayout user={user}>
                  <CannedResponsesPage user={user} />
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
      <Route
        path="/customers"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <PageLayout user={user}>
                  <CustomersPage user={user} />
                </PageLayout>
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/knowledge-base"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <PageLayout user={user}>
                  <KnowledgeBasePage user={user} />
                </PageLayout>
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      <Route
        path="/analytics"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <PageLayout user={user}>
                  <AnalyticsPage user={user} />
                </PageLayout>
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
      {/* Individual ticket view with unique URL */}
      <Route
        path="/ticket/:ticketId"
        element={
          <ProtectedRoute>
            {(user) => (
              <AppWithRealtime user={user}>
                <MainLayout view="ticket" user={user} />
              </AppWithRealtime>
            )}
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

// Create a context to share command palette state
export const CommandPaletteContext = React.createContext({
  openCommandPalette: () => {},
  openKeyboardHelp: () => {},
});

// Component to handle mention notifications
function MentionNotificationHandler() {
  const { onMentionNotification } = useRealtime();
  const navigate = useNavigate();

  useEffect(() => {
    if (!onMentionNotification) return;

    const unsubscribe = onMentionNotification((data) => {
      // Navigate to the ticket on mention
      if (data.ticket_id) {
        navigate(`/dashboard?ticket=${data.ticket_id}`);
      }
    });

    return unsubscribe;
  }, [onMentionNotification, navigate]);

  return null;
}

// Lazy-loaded component (must be at module level, NOT inside a component)
const KeyboardShortcutsHelp = React.lazy(() => import('./components/common/KeyboardShortcutsHelp'));

// Wrapper component that provides realtime context to authenticated routes
function AppWithRealtime({ user, children }) {
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [keyboardHelpOpen, setKeyboardHelpOpen] = useState(false);

  // Global keyboard shortcut for Command Palette and Help
  useEffect(() => {
    const handleKeyDown = (e) => {
      const activeElement = document.activeElement;
      const isTyping = activeElement?.isContentEditable || 
                       activeElement?.tagName === 'INPUT' || 
                       activeElement?.tagName === 'TEXTAREA' ||
                       activeElement?.tagName === 'SELECT';
      
      // Cmd+K (Mac) or Ctrl+K (Windows/Linux) for command palette
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(prev => !prev);
        return;
      }
      
      // ? for keyboard shortcuts help (only when not typing)
      if (e.key === '?' && !isTyping) {
        e.preventDefault();
        setKeyboardHelpOpen(prev => !prev);
        return;
      }
      
      // Escape to close help
      if (e.key === 'Escape' && keyboardHelpOpen) {
        e.preventDefault();
        setKeyboardHelpOpen(false);
        return;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [keyboardHelpOpen]);

  const openCommandPalette = useCallback(() => {
    setCommandPaletteOpen(true);
  }, []);

  const openKeyboardHelp = useCallback(() => {
    setKeyboardHelpOpen(true);
  }, []);

  return (
    <RealtimeProvider user={user}>
      <MentionNotificationHandler />
      <CommandPaletteContext.Provider value={{ openCommandPalette, openKeyboardHelp }}>
        {children}
      </CommandPaletteContext.Provider>
      <CommandPalette 
        isOpen={commandPaletteOpen} 
        onClose={() => setCommandPaletteOpen(false)} 
      />
      <React.Suspense fallback={null}>
        <KeyboardShortcutsHelp 
          isOpen={keyboardHelpOpen} 
          onClose={() => setKeyboardHelpOpen(false)} 
        />
      </React.Suspense>
    </RealtimeProvider>
  );
}

function App() {
  return (
    <ThemeProvider>
      <Router>
        <div className="App min-h-screen bg-background">
          <AppRouter />
          <Toaster position="bottom-right" richColors closeButton />
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;
