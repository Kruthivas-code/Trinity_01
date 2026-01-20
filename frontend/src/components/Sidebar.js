import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, List, Clock, UserCheck, CheckCircle, Settings, User, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, Menu, X, Mail, LogOut } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const Sidebar = ({ user }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isTicketsExpanded, setIsTicketsExpanded] = useState(true);
  const [isCollapsedMenuOpen, setIsCollapsedMenuOpen] = useState(false);
  const collapsedMenuRef = useRef(null);

  const ticketViews = [
    { id: 'all-tickets', label: 'All Tickets', icon: List, path: '/all-tickets' },
    { id: 'open-tickets', label: 'Open Tickets', icon: UserCheck, path: '/open-tickets' },
    { id: 'waiting-tickets', label: 'Waiting on Customer', icon: Clock, path: '/waiting-tickets' },
    { id: 'closed-tickets', label: 'Closed Tickets', icon: CheckCircle, path: '/closed-tickets' },
  ];

  const otherItems = [
    { id: 'emails', label: 'Emails', icon: Mail, path: '/emails' },
    { id: 'profile', label: 'Profile', icon: User, path: '/profile' },
    { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
  ];

  // Close collapsed menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (collapsedMenuRef.current && !collapsedMenuRef.current.contains(event.target)) {
        setIsCollapsedMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close collapsed menu when sidebar expands
  useEffect(() => {
    if (isExpanded) {
      setIsCollapsedMenuOpen(false);
    }
  }, [isExpanded]);

  const isActive = (path) => location.pathname === path;
  const isTicketViewActive = ticketViews.some(view => isActive(view.path));

  const handleNavigate = (path) => {
    navigate(path);
    setIsMobileOpen(false);
    setIsCollapsedMenuOpen(false);
  };

  const handleLogout = async () => {
    try {
      await fetch(`${BACKEND_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
      localStorage.removeItem('theme');
      toast.success('Logged out successfully');
      navigate('/login', { replace: true });
    } catch (error) {
      console.error('Logout error:', error);
      navigate('/login', { replace: true });
    }
  };

  const renderNavItem = (item, isNested = false) => {
    const Icon = item.icon;
    const active = isActive(item.path);
    
    return (
      <button
        key={item.id}
        onClick={() => handleNavigate(item.path)}
        className={`
          w-full flex items-center gap-3 h-11 rounded-lg
          transition-interactive
          ${active 
            ? 'bg-gradient-primary text-white shadow-lg shadow-primary/25' 
            : 'hover:bg-white/10 text-foreground opacity-100'
          }
          ${!isExpanded && !isNested && 'justify-center'}
          ${isNested ? 'px-3 ml-8' : 'px-3'}
        `}
        data-testid={`nav-${item.id}`}
        title={!isExpanded ? item.label : undefined}
      >
        <Icon size={18} className="shrink-0" />
        {(isExpanded || isNested) && <span className="text-sm font-medium">{item.label}</span>}
      </button>
    );
  };

  const renderDesktopNav = () => (
    <nav className="flex-1 py-4 px-2 space-y-1">
      {/* Dashboard */}
      <button
        onClick={() => handleNavigate('/dashboard')}
        className={`
          w-full flex items-center gap-3 px-3 h-11 rounded-lg
          transition-interactive
          ${isActive('/dashboard')
            ? 'bg-gradient-primary text-white shadow-lg shadow-primary/25' 
            : 'hover:bg-white/10 text-foreground'
          }
          ${!isExpanded && 'justify-center'}
        `}
        data-testid="nav-dashboard"
        title={!isExpanded ? 'Dashboard' : undefined}
      >
        <LayoutDashboard size={20} className={isActive('/dashboard') ? 'opacity-100' : 'opacity-70'} />
        {isExpanded && <span className="text-sm font-medium">Dashboard</span>}
      </button>

      {/* Tickets Dropdown */}
      {isExpanded ? (
        <div className="space-y-1">
          <button
            onClick={() => setIsTicketsExpanded(!isTicketsExpanded)}
            className={`
              w-full flex items-center justify-between px-3 h-11 rounded-lg
              transition-interactive
              ${isTicketViewActive ? 'text-primary' : 'text-foreground'}
              hover:bg-white/10
            `}
            data-testid="nav-tickets-toggle"
          >
            <div className="flex items-center gap-3">
              <List size={20} className="opacity-70" />
              <span className="text-sm font-medium">Tickets</span>
            </div>
            {isTicketsExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          
          {isTicketsExpanded && (
            <div className="space-y-1 pl-2">
              {ticketViews.map(view => renderNavItem(view, true))}
            </div>
          )}
        </div>
      ) : (
        // When collapsed, show icon that opens submenu on hover
        <div className="relative group">
          <button
            className={`
              w-full flex items-center justify-center px-3 h-11 rounded-lg
              transition-interactive
              ${isTicketViewActive ? 'bg-primary/10 text-primary' : 'hover:bg-white/10 text-foreground'}
            `}
            title="Tickets"
          >
            <List size={20} className="opacity-70" />
          </button>
          
          {/* Hover submenu for collapsed state */}
          <div className="absolute left-full top-0 ml-2 hidden group-hover:block z-50">
            <div 
              className="rounded-lg border border-border/60 p-2 min-w-[200px] shadow-xl backdrop-blur-xl backdrop-saturate-150"
              style={{
                background: 'var(--glass-elevated-bg)',
                backgroundColor: 'hsl(var(--card))',
              }}
            >
              {ticketViews.map(view => {
                const Icon = view.icon;
                const active = isActive(view.path);
                return (
                  <button
                    key={view.id}
                    onClick={() => handleNavigate(view.path)}
                    className={`
                      w-full flex items-center gap-3 px-3 h-10 rounded-lg
                      transition-interactive text-left
                      ${active 
                        ? 'bg-gradient-primary text-white' 
                        : 'hover:bg-white/10 text-foreground'
                      }
                    `}
                    data-testid={`collapsed-nav-${view.id}`}
                  >
                    <Icon size={18} />
                    <span className="text-sm font-medium">{view.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Other Items */}
      <div className="pt-2 border-t border-border/40 mt-2">
        {otherItems.map(item => renderNavItem(item, false))}
      </div>
    </nav>
  );

  const renderMobileNav = () => (
    <nav className="flex-1 py-4 px-2 space-y-1">
      {/* Dashboard */}
      <button
        onClick={() => handleNavigate('/dashboard')}
        className={`
          w-full flex items-center gap-3 px-3 h-11 rounded-lg
          transition-interactive
          ${isActive('/dashboard')
            ? 'bg-gradient-primary text-white shadow-lg shadow-primary/25' 
            : 'hover:bg-white/10 text-foreground'
          }
        `}
      >
        <LayoutDashboard size={20} />
        <span className="text-sm font-medium">Dashboard</span>
      </button>

      {/* Tickets Section */}
      <div className="space-y-1">
        <button
          onClick={() => setIsTicketsExpanded(!isTicketsExpanded)}
          className={`
            w-full flex items-center justify-between px-3 h-11 rounded-lg
            transition-interactive
            ${isTicketViewActive ? 'text-primary' : 'text-foreground'}
            hover:bg-white/10
          `}
        >
          <div className="flex items-center gap-3">
            <List size={20} />
            <span className="text-sm font-medium">Tickets</span>
          </div>
          {isTicketsExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        
        {isTicketsExpanded && (
          <div className="space-y-1 pl-2">
            {ticketViews.map(view => {
              const Icon = view.icon;
              const active = isActive(view.path);
              return (
                <button
                  key={view.id}
                  onClick={() => handleNavigate(view.path)}
                  className={`
                    w-full flex items-center gap-3 px-3 ml-6 h-11 rounded-lg
                    transition-interactive
                    ${active 
                      ? 'bg-gradient-primary text-white shadow-lg shadow-primary/25' 
                      : 'hover:bg-white/10 text-foreground'
                    }
                  `}
                >
                  <Icon size={18} />
                  <span className="text-sm font-medium">{view.label}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Other Items */}
      <div className="pt-2 border-t border-border/40 mt-2">
        {otherItems.map(item => {
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
                  ? 'bg-gradient-primary text-white shadow-lg shadow-primary/25' 
                  : 'hover:bg-white/10 text-foreground'
                }
              `}
            >
              <Icon size={20} />
              <span className="text-sm font-medium">{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 h-10 w-10 flex items-center justify-center rounded-lg glass border border-border/60 hover:bg-white/10 transition-interactive"
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

      {/* Desktop Sidebar Wrapper */}
      <div className={`shrink-0 transition-all duration-300 ${isExpanded ? 'w-64' : 'w-16'} hidden lg:block`}>
        <aside
          className={`
            fixed top-0 left-0 h-full z-40 glass border-r border-border/60 backdrop-saturate-150
            transition-all duration-300 ease-in-out
            ${isExpanded ? 'w-64' : 'w-16'}
          `}
          data-testid="sidebar"
        >
          <div className="flex flex-col h-full">
            {/* Logo/Brand */}
            <div className="h-16 flex items-center justify-between px-4 border-b border-border/40">
              {isExpanded ? (
                <h2 className="text-lg font-semibold brand">TickFlow</h2>
              ) : (
                <div className="w-8 h-8 rounded-lg bg-gradient-primary flex items-center justify-center text-white font-bold text-sm brand">
                  TF
                </div>
              )}
            </div>

            {renderDesktopNav()}

            {/* User Info & Toggle */}
            <div className="border-t border-border/40 p-2">
              {isExpanded && user && (
                <div className="px-3 py-2 mb-2">
                  <div className="flex items-center gap-2 mb-2">
                    {user.picture ? (
                      <img src={user.picture} alt={user.name} className="w-8 h-8 rounded-full" />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-gradient-primary flex items-center justify-center text-white text-xs font-medium">
                        {user.name?.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{user.name}</p>
                      <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                    </div>
                  </div>
                  {/* Logout Button */}
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-3 h-9 rounded-lg text-destructive hover:bg-destructive/10 transition-interactive text-sm"
                    data-testid="logout-button-sidebar"
                  >
                    <LogOut size={16} />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
              
              {/* Collapsed state - show logout icon */}
              {!isExpanded && (
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center justify-center h-10 rounded-lg text-destructive hover:bg-destructive/10 transition-interactive mb-1"
                  data-testid="logout-button-collapsed"
                  title="Sign Out"
                >
                  <LogOut size={18} />
                </button>
              )}
              
              {/* Desktop Toggle Button */}
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full flex items-center justify-center h-10 rounded-lg hover:bg-white/10 transition-interactive"
                data-testid="sidebar-toggle"
              >
                {isExpanded ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
              </button>
            </div>
          </div>
        </aside>
      </div>

      {/* Mobile Sidebar */}
      <aside
        className={`
          lg:hidden fixed top-0 left-0 h-full w-64 z-40 glass border-r border-border/60 backdrop-saturate-150
          transition-transform duration-300 ease-in-out
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="flex flex-col h-full">
          {/* Logo/Brand */}
          <div className="h-16 flex items-center justify-between px-4 border-b border-border/40">
            <h2 className="text-lg font-semibold brand">TickFlow</h2>
          </div>

          {renderMobileNav()}

          {/* User Info */}
          {user && (
            <div className="border-t border-border/40 p-4">
              <div className="flex items-center gap-2 mb-3">
                {user.picture ? (
                  <img src={user.picture} alt={user.name} className="w-8 h-8 rounded-full" />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-gradient-primary flex items-center justify-center text-white text-xs font-medium">
                    {user.name?.charAt(0).toUpperCase()}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                </div>
              </div>
              {/* Mobile Logout Button */}
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 h-10 rounded-lg text-destructive hover:bg-destructive/10 transition-interactive"
                data-testid="logout-button-mobile"
              >
                <LogOut size={18} />
                <span className="text-sm font-medium">Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
