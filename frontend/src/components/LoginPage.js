import React from 'react';
import { LogIn } from 'lucide-react';
import { TridentIcon } from './TridentIcon';

const LoginPage = () => {
  const handleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative bg-background">
      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-subtle opacity-50" />
      <div className="gradient-overlay" />
      
      <div className="glass max-w-md w-full mx-auto rounded-2xl p-8 md:p-10 border border-border/60 relative z-10">
        <div className="text-center mb-8">
          {/* Trident Logo */}
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
              <TridentIcon size={28} className="text-primary" strokeWidth={2.5} />
            </div>
          </div>
          <h1 className="text-3xl font-bold tracking-tight brand mb-2" data-testid="auth-title">
            Trinity
          </h1>
          <p className="text-sm text-muted-foreground">
            Email-First Support Management
          </p>
        </div>

        <div className="space-y-5">
          <div className="card-premium rounded-xl p-4">
            <p className="text-sm text-foreground font-medium mb-1">Secure ticket management platform</p>
            <p className="text-xs text-muted-foreground">Sign in with your Google account to continue</p>
          </div>

          <button
            onClick={handleLogin}
            className="w-full h-12 px-5 flex items-center justify-center gap-3 rounded-xl btn-premium font-medium active:scale-[0.985] focus-visible:ring-2 focus-visible:ring-primary/50 transition-interactive"
            data-testid="login-button"
          >
            <LogIn size={20} />
            Sign in with Google
          </button>
        </div>

        <div className="mt-8 text-center text-xs text-muted-foreground">
          <p>Powered by Emergent Auth</p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
