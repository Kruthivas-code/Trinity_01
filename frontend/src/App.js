import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Toaster } from 'sonner';
import './App.css';
import { ThemeProvider } from './contexts/ThemeContext';
import LoginPage from './components/auth/LoginPage';
import AuthCallback from './components/auth/AuthCallback';
import ProtectedRoute from './components/auth/ProtectedRoute';

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

      {/* ==================== Auth ==================== */}
      <Route path="/login" element={<LoginPage />} />

      {/* ==================== KB Editor (protected) ==================== */}
      <Route path="/dashboard/kb-editor" element={<ProtectedRoute>{() => <KBEditor />}</ProtectedRoute>} />
      <Route path="/dashboard/kb-editor/:slug" element={<ProtectedRoute>{() => <KBEditor />}</ProtectedRoute>} />

      {/* ==================== Review flow (protected) ==================== */}
      <Route path="/dashboard/review" element={<ProtectedRoute>{(user) => <ReviewConsole user={user} />}</ProtectedRoute>} />
      <Route path="/dashboard/review/:slug" element={<ProtectedRoute>{(user) => <ReviewPage user={user} />}</ProtectedRoute>} />

      {/* ==================== Fallback ==================== */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
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
