import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, List, Settings, User, ChevronLeft, ChevronRight, Menu, X } from 'lucide-react';

const Sidebar = ({ user }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
    { id: 'all-tickets', label: 'All Tickets', icon: List, path: '/all-tickets' },
    { id: 'profile', label: 'Profile', icon: User, path: '/profile' },
    { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
  ];

  const isActive = (path) => location.pathname === path;

  const handleNavigate = (path) => {
    navigate(path);
    setIsMobileOpen(false);
  };

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 h-10 w-10 flex items-center justify-center rounded-lg glass border border-border/60 hover:bg-white/5 transition-interactive"
        data-testid="mobile-menu-button"
      >
        {isMobileOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed top-0 left-0 h-full z-40 glass border-r border-border/60 backdrop-saturate-150
          transition-all duration-300 ease-in-out
          ${isExpanded ? 'w-64' : 'w-16'}
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
        data-testid="sidebar"
      >
        <div className="flex flex-col h-full">
          {/* Logo/Brand */}
          <div className="h-16 flex items-center justify-between px-4 border-b border-border/40">
            {isExpanded ? (
              <h2 className="text-lg font-semibold">TickFlow</h2>
            ) : (
              <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary font-bold text-sm">
                TF
              </div>
            )}
          </div>

          {/* Navigation Items */}
          <nav className="flex-1 py-4 px-2 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);
              
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavigate(item.path)}
                  className={`
                    w-full flex items-center gap-3 px-3 h-11 rounded-lg
                    transition-interactive
                    ${active 
                      ? 'bg-primary/20 text-primary' 
                      : 'hover:bg-white/5 text-foreground'
                    }
                    ${!isExpanded && 'justify-center'}
                  `}
                  data-testid={`nav-${item.id}`}
                  title={!isExpanded ? item.label : undefined}
                >
                  <Icon size={20} />
                  {isExpanded && <span className="text-sm font-medium">{item.label}</span>}
                </button>
              );
            })}
          </nav>

          {/* User Info & Toggle */}
          <div className="border-t border-border/40 p-2">
            {isExpanded && user && (
              <div className="px-3 py-2 mb-2">
                <div className="flex items-center gap-2 mb-1">
                  {user.picture ? (
                    <img src={user.picture} alt={user.name} className="w-8 h-8 rounded-full" />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary text-xs font-medium">
                      {user.name?.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{user.name}</p>
                    <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Desktop Toggle Button */}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="hidden lg:flex w-full items-center justify-center h-10 rounded-lg hover:bg-white/5 transition-interactive"
              data-testid="sidebar-toggle"
            >
              {isExpanded ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
            </button>
          </div>
        </div>
      </aside>

      {/* Spacer to push content */}
      <div className={`hidden lg:block transition-all duration-300 ${isExpanded ? 'w-64' : 'w-16'}`} />
    </>
  );
};

export default Sidebar;
