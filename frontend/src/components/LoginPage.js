import React from 'react';
import { LogIn } from 'lucide-react';

const LoginPage = () => {
  const handleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative">
      {/* Gradient overlay */}
      <div className="gradient-overlay" />
      
      <div className="glass max-w-md w-full mx-auto rounded-2xl p-6 md:p-8 border border-border/60 relative z-10 animate-fade-in-up">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-semibold tracking-tight brand mb-2" data-testid="auth-title">
            Trinity
          </h1>
          <p className="text-sm text-muted-foreground">
            Email-First Support Management
          </p>
        </div>

        <div className="space-y-4">
          <div className="glass rounded-lg p-4 text-sm text-muted-foreground">
            <p className="mb-2">Secure ticket management platform</p>
            <p className="text-xs">Sign in with your Google account to continue</p>
          </div>

          <button
            onClick={handleLogin}
            className="w-full h-12 px-5 flex items-center justify-center gap-3 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-cyan-400/90 active:scale-[0.985] focus-visible:ring-2 focus-visible:ring-cyan-300 transition-interactive"
            data-testid="login-button"
          >
            <LogIn size={20} />
            Sign in with Google
          </button>
        </div>

        <div className="mt-6 text-center text-xs text-muted-foreground">
          <p>Powered by Emergent Auth</p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
