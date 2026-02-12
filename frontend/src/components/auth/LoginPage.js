import React from 'react';
import { LogIn } from 'lucide-react';
import { TridentIcon } from '../common/TridentIcon';

const LoginPage = () => {
  const handleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <div className="max-w-md w-full mx-auto rounded-2xl p-8 md:p-10 border border-border bg-card">
        <div className="text-center mb-8">
          {/* Trident Logo */}
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-foreground/5 border border-border flex items-center justify-center">
              <TridentIcon size={28} className="text-foreground" strokeWidth={2.5} />
            </div>
          </div>
          <h1 className="text-2xl font-bold tracking-tight brand mb-2" data-testid="auth-title">
            Trinity
          </h1>
          <p className="text-sm text-muted-foreground">
            Email-First Support Management
          </p>
        </div>

        <div className="space-y-5">
          <div className="rounded-xl p-4 bg-secondary/50 border border-border">
            <p className="text-sm text-foreground font-medium mb-1">Secure ticket management platform</p>
            <p className="text-[13px] text-muted-foreground">Sign in with your Google account to continue</p>
          </div>

          <button
            onClick={handleLogin}
            className="w-full h-12 px-5 flex items-center justify-center gap-3 rounded-xl bg-foreground text-background font-medium hover:bg-foreground/90 active:scale-[0.985] focus-visible:ring-2 focus-visible:ring-foreground/50 transition-all duration-150"
            data-testid="login-button"
          >
            <LogIn size={20} />
            Sign in with Google
          </button>
        </div>

        <div className="mt-8 text-center text-[13px] text-muted-foreground">
          <p>Powered by Emergent Auth</p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
