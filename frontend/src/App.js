import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import './App.css';
import { ThemeProvider } from './contexts/ThemeContext';
import LoginPage from './components/LoginPage';
import AuthCallback from './components/AuthCallback';
import ProtectedRoute from './components/ProtectedRoute';
import MainLayout from './components/MainLayout';
import ProfilePage from './components/ProfilePage';
import SettingsPage from './components/SettingsPage';
import EmailsPage from './components/EmailsPage';
import TeamsPage from './components/TeamsPage';
import AdminPage from './components/AdminPage';

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
            <MainLayout view="dashboard" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/all-tickets"
        element={
          <ProtectedRoute>
            <MainLayout view="all-tickets" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/open-tickets"
        element={
          <ProtectedRoute>
            <MainLayout view="open-tickets" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/waiting-tickets"
        element={
          <ProtectedRoute>
            <MainLayout view="waiting-tickets" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/closed-tickets"
        element={
          <ProtectedRoute>
            <MainLayout view="closed-tickets" />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <SettingsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/emails"
        element={
          <ProtectedRoute>
            <EmailsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/teams"
        element={
          <ProtectedRoute>
            <TeamsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <AdminPage />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider>
      <Router>
        <div className="App min-h-screen bg-background">
          <AppRouter />
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;
