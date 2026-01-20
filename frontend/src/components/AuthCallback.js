import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AuthCallback = () => {
  const navigate = useNavigate();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Use ref to prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processSession = async () => {
      try {
        // Extract session_id from URL fragment
        const hash = window.location.hash;
        console.log('AuthCallback: Processing hash:', hash);
        const sessionIdMatch = hash.match(/session_id=([^&]+)/);
        
        if (!sessionIdMatch) {
          throw new Error('No session_id found in URL');
        }

        const sessionId = sessionIdMatch[1];
        console.log('AuthCallback: Found session_id, calling backend...');

        // Exchange session_id for session_token
        const response = await fetch(`${BACKEND_URL}/api/auth/session`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ session_id: sessionId })
        });

        console.log('AuthCallback: Response status:', response.status);
        const data = await response.json();
        console.log('AuthCallback: Response data:', data);

        if (!response.ok) {
          throw new Error(data.detail || 'Authentication failed');
        }

        const userData = data;

        // Navigate to dashboard with user data
        console.log('AuthCallback: Success! Navigating to dashboard');
        navigate('/dashboard', {
          replace: true,
          state: { user: userData }
        });
        
        toast.success(`Welcome, ${userData.name}!`);
      } catch (error) {
        console.error('Auth callback error:', error);
        toast.error(error.message || 'Authentication failed');
        navigate('/login', { replace: true });
      }
    };

    processSession();
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="glass rounded-xl p-6">
        <div className="animate-pulse text-foreground">Completing sign in...</div>
      </div>
    </div>
  );
};

export default AuthCallback;
