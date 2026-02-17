import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { Sun, Moon, LogOut, FileText } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { usePortalAuth } from './PortalAuthContext';

const PortalLayout = () => {
  const { theme, toggleTheme } = useTheme();
  const { customer, logout } = usePortalAuth();

  return (
    <div className="min-h-screen bg-background text-foreground" data-testid="portal-layout">
      <header className="border-b border-border/40 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/portal" className="flex items-center gap-2.5" data-testid="portal-logo">
              <img
                src="/images/emergent-logo-dark.png"
                alt="Emergent"
                className={`h-5 ${theme === 'light' ? 'invert' : ''}`}
              />
            </Link>
            <div className="w-px h-4 bg-border/40" />
            <Link
              to="/"
              className="flex items-center gap-1.5 text-[11px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
              data-testid="portal-docs-link"
            >
              <FileText size={11} />
              Docs
            </Link>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={toggleTheme}
              className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              data-testid="theme-toggle"
            >
              {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
            </button>

            {customer ? (
              <div className="flex items-center gap-1.5 ml-1">
                <Link
                  to="/portal/my-tickets"
                  className="px-2.5 py-1 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  data-testid="portal-my-tickets-link"
                >
                  My Tickets
                </Link>
                <div className="w-px h-4 bg-border/40" />
                <span className="text-xs text-muted-foreground/60">{customer.name?.split(' ')[0]}</span>
                <button
                  onClick={logout}
                  className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  data-testid="portal-logout-btn"
                  title="Sign out"
                >
                  <LogOut size={13} />
                </button>
              </div>
            ) : (
              <Link
                to="/portal/login"
                className="ml-1 px-3 py-1.5 rounded-md text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                data-testid="portal-signin-link"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>

      <main>
        <Outlet />
      </main>
    </div>
  );
};

export default PortalLayout;
