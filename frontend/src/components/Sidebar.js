import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, List, Clock, UserCheck, CheckCircle, Settings, 
  User, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, 
  Menu, X, LogOut, Users, Shield 
} from 'lucide-react';
import { toast } from 'sonner';
import { TridentIcon } from './TridentIcon';

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
    { id: 'teams', label: 'Teams', icon: Users, path: '/teams' },
    { id: 'profile', label: 'Profile', icon: User, path: '/profile' },
    { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
    { id: 'admin', label: 'Admin', icon: Shield, path: '/admin' },
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
          w-full flex items-center gap-3 h-10 rounded-lg
          transition-interactive focus-ring
          ${active 
            ? 'bg-primary/15 text-primary border border-primary/20' 
            : 'hover:bg-secondary/60 text-foreground/80 hover:text-foreground border border-transparent'
          }
          ${!isExpanded && !isNested && 'justify-center'}
          ${isNested ? 'px-3 ml-7' : 'px-3'}
        `}
        data-testid={`nav-${item.id}`}
        title={!isExpanded ? item.label : undefined}
      >
        <Icon size={18} className={`shrink-0 ${active ? 'text-primary' : 'opacity-70'}`} />
        {(isExpanded || isNested) && (
          <span className={`text-sm font-medium ${active ? 'text-primary' : ''}`}>
            {item.label}
          </span>
        )}
      </button>
    );
  };

  const renderDesktopNav = () => (
    <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
      {/* Dashboard */}
      <button
        onClick={() => handleNavigate('/dashboard')}
        className={`
          w-full flex items-center gap-3 px-3 h-10 rounded-lg
          transition-interactive focus-ring
          ${isActive('/dashboard')
            ? 'bg-primary/15 text-primary border border-primary/20' 
            : 'hover:bg-secondary/60 text-foreground/80 hover:text-foreground border border-transparent'
          }
          ${!isExpanded && 'justify-center'}
        `}
        data-testid="nav-dashboard"
        title={!isExpanded ? 'Dashboard' : undefined}
      >
        <LayoutDashboard size={18} className={isActive('/dashboard') ? 'text-primary' : 'opacity-70'} />
        {isExpanded && <span className="text-sm font-medium">Dashboard</span>}
      </button>

      {/* Tickets Dropdown */}
      {isExpanded ? (
        <div className="space-y-1">
          <button
            onClick={() => setIsTicketsExpanded(!isTicketsExpanded)}
            className={`
              w-full flex items-center justify-between px-3 h-10 rounded-lg
              transition-interactive focus-ring border border-transparent
              ${isTicketViewActive ? 'text-primary' : 'text-foreground/80'}
              hover:bg-secondary/60 hover:text-foreground
            `}
            data-testid="nav-tickets-toggle"
          >
            <div className="flex items-center gap-3">
              <List size={18} className={isTicketViewActive ? 'text-primary' : 'opacity-70'} />
              <span className="text-sm font-medium">Tickets</span>
            </div>
            {isTicketsExpanded ? <ChevronUp size={16} className="opacity-50" /> : <ChevronDown size={16} className="opacity-50" />}
          </button>
          
          {isTicketsExpanded && (
            <div className="space-y-0.5 pl-1">
              {ticketViews.map(view => renderNavItem(view, true))}
            </div>
          )}
        </div>
      ) : (
        // When collapsed, show icon that opens submenu on click
        <div className="relative" ref={collapsedMenuRef}>
          <button
            onClick={() => setIsCollapsedMenuOpen(!isCollapsedMenuOpen)}
            className={`
              w-full flex items-center justify-center px-3 h-10 rounded-lg
              transition-interactive focus-ring border
              ${isTicketViewActive || isCollapsedMenuOpen 
                ? 'bg-primary/15 text-primary border-primary/20' 
                : 'hover:bg-secondary/60 text-foreground/80 border-transparent'
              }
            `}
            title="Tickets"
            data-testid="collapsed-tickets-toggle"
          >
            <List size={18} className={isCollapsedMenuOpen || isTicketViewActive ? 'text-primary' : 'opacity-70'} />
          </button>
          
          {/* Click submenu for collapsed state */}
          {isCollapsedMenuOpen && (
            <div className="absolute left-full top-0 ml-2 z-50">
              <div 
                className="card-premium rounded-xl p-2 min-w-[200px]"
              >
                <div className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b border-border/40 mb-2">
                  Tickets
                </div>
                {ticketViews.map(view => {
                  const Icon = view.icon;
                  const active = isActive(view.path);
                  return (
                    <button
                      key={view.id}
                      onClick={() => handleNavigate(view.path)}
                      className={`
                        w-full flex items-center gap-3 px-3 h-10 rounded-lg
                        transition-interactive text-left focus-ring
                        ${active 
                          ? 'bg-primary/15 text-primary' 
                          : 'hover:bg-secondary/60 text-foreground/80 hover:text-foreground'
                        }
                      `}
                      data-testid={`collapsed-nav-${view.id}`}
                    >
                      <Icon size={16} className={active ? 'text-primary' : 'opacity-70'} />
                      <span className="text-sm font-medium">{view.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Other Items */}
      <div className="pt-3 mt-3 border-t border-border/40 space-y-0.5">
        {otherItems.map(item => renderNavItem(item, false))}
      </div>
    </nav>
  );

  const renderMobileNav = () => (
    <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
      {/* Dashboard */}
      <button
        onClick={() => handleNavigate('/dashboard')}
        className={`
          w-full flex items-center gap-3 px-3 h-10 rounded-lg
          transition-interactive focus-ring
          ${isActive('/dashboard')
            ? 'bg-primary/15 text-primary border border-primary/20' 
            : 'hover:bg-secondary/60 text-foreground/80 border border-transparent'
          }
        `}
      >
        <LayoutDashboard size={18} className={isActive('/dashboard') ? 'text-primary' : 'opacity-70'} />
        <span className="text-sm font-medium">Dashboard</span>
      </button>

      {/* Tickets Section */}
      <div className="space-y-1">
        <button
          onClick={() => setIsTicketsExpanded(!isTicketsExpanded)}
          className={`
            w-full flex items-center justify-between px-3 h-10 rounded-lg
            transition-interactive focus-ring border border-transparent
            ${isTicketViewActive ? 'text-primary' : 'text-foreground/80'}
            hover:bg-secondary/60
          `}
        >
          <div className="flex items-center gap-3">
            <List size={18} className={isTicketViewActive ? 'text-primary' : 'opacity-70'} />
            <span className="text-sm font-medium">Tickets</span>
          </div>
          {isTicketsExpanded ? <ChevronUp size={16} className="opacity-50" /> : <ChevronDown size={16} className="opacity-50" />}
        </button>
        
        {isTicketsExpanded && (
          <div className="space-y-0.5 pl-1">
            {ticketViews.map(view => {
              const Icon = view.icon;
              const active = isActive(view.path);
              return (
                <button
                  key={view.id}
                  onClick={() => handleNavigate(view.path)}
                  className={`
                    w-full flex items-center gap-3 px-3 ml-7 h-10 rounded-lg
                    transition-interactive focus-ring
                    ${active 
                      ? 'bg-primary/15 text-primary border border-primary/20' 
                      : 'hover:bg-secondary/60 text-foreground/80 border border-transparent'
                    }
                  `}
                >
                  <Icon size={16} className={active ? 'text-primary' : 'opacity-70'} />
                  <span className="text-sm font-medium">{view.label}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Other Items */}
      <div className="pt-3 mt-3 border-t border-border/40 space-y-0.5">
        {otherItems.map(item => {
          const Icon = item.icon;
          const active = isActive(item.path);
          return (
            <button
              key={item.id}
              onClick={() => handleNavigate(item.path)}
              className={`
                w-full flex items-center gap-3 px-3 h-10 rounded-lg
                transition-interactive focus-ring
                ${active 
                  ? 'bg-primary/15 text-primary border border-primary/20' 
                  : 'hover:bg-secondary/60 text-foreground/80 border border-transparent'
                }
              `}
            >
              <Icon size={18} className={active ? 'text-primary' : 'opacity-70'} />
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
        className="lg:hidden fixed top-4 left-4 z-50 h-10 w-10 flex items-center justify-center rounded-xl glass border border-border/60 hover:bg-secondary/60 transition-interactive focus-ring"
        data-testid="mobile-menu-button"
      >
        {isMobileOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Desktop Sidebar Wrapper */}
      <div className={`shrink-0 transition-all duration-300 ${isExpanded ? 'w-60' : 'w-16'} hidden lg:block`}>
        <aside
          className={`
            fixed top-0 left-0 h-full z-40 glass border-r border-border/50
            transition-all duration-300 ease-out
            ${isExpanded ? 'w-60' : 'w-16'}
          `}
          data-testid="sidebar"
        >
          <div className="flex flex-col h-full">
            {/* Logo/Brand */}
            <div className="h-16 flex items-center justify-center px-4 border-b border-border/40">
              {isExpanded ? (
                <div className="flex items-center gap-2.5">
                  <TridentIcon size={22} className="text-primary" strokeWidth={2.5} />
                  <span className="brand text-lg font-bold tracking-tight">Trinity</span>
                </div>
              ) : (
                <div className="w-9 h-9 flex items-center justify-center rounded-lg bg-primary/10 hover:bg-primary/15 transition-interactive">
                  <TridentIcon size={20} className="text-primary" strokeWidth={2.5} />
                </div>
              )}
            </div>

            {renderDesktopNav()}

            {/* User Info & Toggle */}
            <div className="border-t border-border/40 p-2">
              {isExpanded && user && (
                <div className="px-2 py-3 mb-2">
                  <div className="flex items-center gap-2.5 mb-3">
                    {user.picture ? (
                      <img src={user.picture} alt={user.name} className="w-9 h-9 rounded-full ring-2 ring-border/50" />
                    ) : (
                      <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/40 to-accent/40 flex items-center justify-center text-primary text-sm font-semibold ring-2 ring-border/50">
                        {user.name?.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{user.name}</p>
                      <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                    </div>
                  </div>
                  {/* Logout Button - Subtle design */}
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-3 h-9 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-interactive text-sm group focus-ring"
                    data-testid="logout-button-sidebar"
                  >
                    <LogOut size={15} className="opacity-60 group-hover:opacity-100 transition-interactive" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
              
              {/* Collapsed state - show logout icon */}
              {!isExpanded && (
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center justify-center h-10 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-interactive mb-1 focus-ring"
                  data-testid="logout-button-collapsed"
                  title="Sign Out"
                >
                  <LogOut size={18} />
                </button>
              )}
              
              {/* Desktop Toggle Button */}
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full flex items-center justify-center h-10 rounded-lg hover:bg-secondary/50 transition-interactive focus-ring text-muted-foreground hover:text-foreground"
                data-testid="sidebar-toggle"
              >
                {isExpanded ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
              </button>
            </div>
          </div>
        </aside>
      </div>

      {/* Mobile Sidebar */}
      <aside
        className={`
          lg:hidden fixed top-0 left-0 h-full w-64 z-40 glass border-r border-border/50
          transition-transform duration-300 ease-out
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="flex flex-col h-full">
          {/* Logo/Brand */}
          <div className="h-16 flex items-center justify-between px-4 border-b border-border/40">
            <div className="flex items-center gap-2.5">
              <TridentIcon size={22} className="text-primary" strokeWidth={2.5} />
              <span className="brand text-lg font-bold">Trinity</span>
            </div>
          </div>

          {renderMobileNav()}

          {/* User Info */}
          {user && (
            <div className="border-t border-border/40 p-4">
              <div className="flex items-center gap-2.5 mb-3">
                {user.picture ? (
                  <img src={user.picture} alt={user.name} className="w-9 h-9 rounded-full ring-2 ring-border/50" />
                ) : (
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/40 to-accent/40 flex items-center justify-center text-primary text-sm font-medium ring-2 ring-border/50">
                    {user.name?.charAt(0).toUpperCase()}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                </div>
              </div>
              {/* Mobile Logout Button - Subtle, not harsh red */}
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 h-10 rounded-lg btn-destructive-subtle transition-interactive focus-ring"
                data-testid="logout-button-mobile"
              >
                <LogOut size={16} />
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
