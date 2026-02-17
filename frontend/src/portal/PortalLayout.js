import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Sun, Moon, User, LogOut, Ticket, HelpCircle } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { usePortalAuth } from './PortalAuthContext';

const PortalLayout = () => {
  const { theme, toggleTheme } = useTheme();
  const { customer, logout } = usePortalAuth();
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background text-foreground" data-testid="portal-layout">
      {/* Header */}
      <header className="border-b border-border/40 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link to="/portal" className="flex items-center gap-2.5 group" data-testid="portal-logo">
            <div className="h-7 w-7 rounded bg-foreground flex items-center justify-center">
              <span className="text-background text-xs font-bold tracking-tight">E</span>
            </div>
            <span className="text-sm font-medium text-foreground/70 group-hover:text-foreground transition-colors">
              Support
            </span>
          </Link>

          <nav className="flex items-center gap-1">
            <Link
              to="/portal"
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${location.pathname === '/portal' || location.pathname === '/portal/categories' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
              data-testid="nav-home"
            >
              Home
            </Link>
            {customer && (
              <Link
                to="/portal/my-tickets"
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${location.pathname.startsWith('/portal/my-tickets') ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                data-testid="nav-my-tickets"
              >
                My Tickets
              </Link>
            )}
            <Link
              to="/portal/submit"
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${location.pathname === '/portal/submit' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
              data-testid="nav-submit"
            >
              Submit Ticket
            </Link>
            <Link
              to="/docs"
              className="px-3 py-1.5 rounded-md text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
              data-testid="nav-docs"
            >
              Docs
            </Link>

            <div className="w-px h-5 bg-border/50 mx-1" />

            <button
              onClick={toggleTheme}
              className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              data-testid="theme-toggle"
            >
              {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
            </button>

            {customer ? (
              <div className="flex items-center gap-1 ml-1">
                <span className="text-xs text-muted-foreground">{customer.name?.split(' ')[0]}</span>
                <button
                  onClick={logout}
                  className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  data-testid="portal-logout-btn"
                  title="Logout"
                >
                  <LogOut size={14} />
                </button>
              </div>
            ) : (
              <Link
                to="/portal/login"
                className="ml-1 px-3 py-1.5 rounded-md text-xs font-medium bg-foreground text-background hover:opacity-90 transition-opacity"
                data-testid="portal-login-link"
              >
                Sign in
              </Link>
            )}
          </nav>
        </div>
      </header>

      {/* Content */}
      <main>
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-border/30 mt-20 py-8">
        <div className="max-w-5xl mx-auto px-6 flex items-center justify-between text-xs text-muted-foreground/50">
          <span>Emergent Support</span>
          <div className="flex items-center gap-4">
            <a href="https://help.emergent.sh" target="_blank" rel="noopener noreferrer" className="hover:text-muted-foreground transition-colors">Docs</a>
            <a href="https://emergent.sh" target="_blank" rel="noopener noreferrer" className="hover:text-muted-foreground transition-colors">emergent.sh</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default PortalLayout;
