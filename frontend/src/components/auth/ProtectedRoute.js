import React, { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Module-level auth cache - persists across route changes and remounts
let _cachedUser = null;

export const setCachedUser = (user) => {
  _cachedUser = user;
};

export const clearCachedUser = () => {
  _cachedUser = null;
};

const ProtectedRoute = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(
    _cachedUser ? true : null
  );
  const [user, setUser] = useState(_cachedUser);

  useEffect(() => {
    // If we already have a cached user, use it immediately
    if (_cachedUser) {
      setIsAuthenticated(true);
      setUser(_cachedUser);
      return;
    }

    const checkAuth = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
          credentials: 'include'
        });

        if (!response.ok) {
          throw new Error('Not authenticated');
        }

        const userData = await response.json();
        _cachedUser = userData;
        setIsAuthenticated(true);
        setUser(userData);
      } catch (error) {
        _cachedUser = null;
        setIsAuthenticated(false);
      }
    };

    checkAuth();
  }, []);

  // Loading state
  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass rounded-xl p-6">
          <div className="animate-pulse text-foreground">Verifying session...</div>
        </div>
      </div>
    );
  }

  // Not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Authenticated - render children with user prop
  if (typeof children === 'function') {
    return children(user);
  }
  return React.cloneElement(children, { user });
};

export default ProtectedRoute;
