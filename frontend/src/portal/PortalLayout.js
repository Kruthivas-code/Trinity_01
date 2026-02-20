import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { Sun, Moon, LogOut, ArrowRight } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { usePortalAuth } from './PortalAuthContext';

const PortalLayout = () => {
  const { theme, toggleTheme } = useTheme();
  const { customer, logout } = usePortalAuth();
  const isLight = theme === 'light';

  return (
    <div className={`min-h-screen ${isLight ? 'bg-white text-gray-900' : 'bg-[#0a0a0a] text-white'}`} data-testid="portal-layout">
      <header className={`fixed top-0 left-0 right-0 z-50 ${isLight ? 'bg-white border-gray-200' : 'bg-[#0a0a0a] border-white/10'} border-b`}>
        <div className="h-14 px-4 sm:px-6 flex items-center justify-between">
          <Link to="/portal" className="flex items-center gap-2 flex-shrink-0" data-testid="portal-logo">
            <img
              src="/images/emergent-logo-dark.png"
              alt="Emergent"
              className={`h-6 ${isLight ? 'invert' : ''}`}
            />
          </Link>

          <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
            {customer && (
              <>
                <Link
                  to="/portal/my-tickets"
                  className={`hidden sm:flex items-center px-3 py-1.5 text-sm ${isLight ? 'text-gray-500 hover:text-gray-900' : 'text-[#999999] hover:text-white'} transition-colors`}
                  data-testid="portal-my-tickets-link"
                >
                  My Tickets
                </Link>
                <span className={`hidden sm:inline text-xs ${isLight ? 'text-gray-400' : 'text-[#787878]'}`}>{customer.name?.split(' ')[0]}</span>
                <button
                  onClick={logout}
                  className={`p-2 rounded-lg ${isLight ? 'text-gray-400 hover:text-gray-900 hover:bg-gray-100' : 'text-[#999999] hover:text-white hover:bg-white/5'} transition-colors`}
                  data-testid="portal-logout-btn"
                  title="Sign out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
                <div className={`w-px h-4 ${isLight ? 'bg-gray-200' : 'bg-white/10'}`} />
              </>
            )}
            {!customer && (
              <Link
                to="/portal/login"
                className={`px-3 py-1.5 text-sm ${isLight ? 'text-gray-500 hover:text-gray-900' : 'text-[#999999] hover:text-white'} transition-colors`}
                data-testid="portal-signin-link"
              >
                Sign in
              </Link>
            )}
            <Link
              to="/"
              className="flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-[#00A1B2] text-white text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
              data-testid="portal-docs-link"
            >
              Docs
            </Link>
            <button
              onClick={toggleTheme}
              className={`p-2 rounded-lg transition-colors ${isLight ? 'text-gray-400 hover:text-gray-900 hover:bg-gray-100' : 'text-[#999999] hover:text-white hover:bg-white/5'}`}
              data-testid="theme-toggle"
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </header>

      <main className="pt-14">
        <Outlet />
      </main>
    </div>
  );
};

export default PortalLayout;
