import React from 'react';
import { ArrowLeft, Sun, Moon } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const SettingsPage = ({ user }) => {
  const navigate = useNavigate();
  const { theme, setThemeMode } = useTheme();

  if (!user) {
    return null;
  }

  const handleThemeChange = async (newTheme) => {
    try {
      // Update theme in UI
      setThemeMode(newTheme);

      // Save to backend
      const response = await fetch(`${BACKEND_URL}/api/users/me/preferences`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ theme: newTheme })
      });

      if (!response.ok) throw new Error('Failed to save preferences');
      
      toast.success(`Theme changed to ${newTheme} mode`);
    } catch (error) {
      toast.error('Failed to save theme preference');
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="gradient-overlay" />
      <div className="content-wrapper relative z-10">
        {/* Header */}
        <header className="sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150">
          <div className="mx-auto max-w-[1200px] px-4 h-16 flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="h-9 w-9 flex items-center justify-center rounded-lg hover:bg-white/5 transition-interactive"
              data-testid="back-button"
            >
              <ArrowLeft size={20} />
            </button>
            <h1 className="text-xl font-semibold">Settings</h1>
          </div>
        </header>

        {/* Content */}
        <div className="mx-auto max-w-[1200px] px-4 py-8">
          <div className="glass rounded-2xl p-6 md:p-8 border border-border/60">
            {/* Appearance Section */}
            <div className="mb-8">
              <h3 className="text-lg font-medium mb-4">Appearance</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Customize how TickFlow looks on your device.
              </p>

              <div className="space-y-3">
                {/* Dark Mode */}
                <button
                  onClick={() => handleThemeChange('dark')}
                  className={`w-full flex items-center justify-between p-4 rounded-lg border transition-interactive ${
                    theme === 'dark'
                      ? 'bg-primary/10 border-primary'
                      : 'bg-secondary/30 border-border/40 hover:border-border/60'
                  }`}
                  data-testid="theme-dark-button"
                >
                  <div className="flex items-center gap-3">
                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                      theme === 'dark' ? 'bg-primary/20 text-primary' : 'bg-secondary/50'
                    }`}>
                      <Moon size={20} />
                    </div>
                    <div className="text-left">
                      <p className="font-medium">Dark Mode</p>
                      <p className="text-sm text-muted-foreground">Sleek glassmorphism dark theme</p>
                    </div>
                  </div>
                  {theme === 'dark' && (
                    <div className="h-5 w-5 rounded-full bg-primary flex items-center justify-center">
                      <svg
                        className="w-3 h-3 text-primary-foreground"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={3}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    </div>
                  )}
                </button>

                {/* Light Mode */}
                <button
                  onClick={() => handleThemeChange('light')}
                  className={`w-full flex items-center justify-between p-4 rounded-lg border transition-interactive ${
                    theme === 'light'
                      ? 'bg-primary/10 border-primary'
                      : 'bg-secondary/30 border-border/40 hover:border-border/60'
                  }`}
                  data-testid="theme-light-button"
                >
                  <div className="flex items-center gap-3">
                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                      theme === 'light' ? 'bg-primary/20 text-primary' : 'bg-secondary/50'
                    }`}>
                      <Sun size={20} />
                    </div>
                    <div className="text-left">
                      <p className="font-medium">Light Mode</p>
                      <p className="text-sm text-muted-foreground">Clean and bright interface</p>
                    </div>
                  </div>
                  {theme === 'light' && (
                    <div className="h-5 w-5 rounded-full bg-primary flex items-center justify-center">
                      <svg
                        className="w-3 h-3 text-primary-foreground"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={3}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    </div>
                  )}
                </button>
              </div>
            </div>

            {/* Account Section */}
            <div className="pt-8 border-t border-border/40">
              <h3 className="text-lg font-medium mb-4">Account</h3>
              <div className="glass rounded-lg p-4 bg-secondary/30">
                <p className="text-sm text-muted-foreground mb-2">Signed in as</p>
                <p className="font-medium">{user.email}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
