import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, List, Clock, UserCheck, CheckCircle, Settings, 
  User, ChevronDown, Menu, X, LogOut, Users, Shield, CalendarDays,
  GripVertical, Bookmark, BarChart3, UserCircle, Star, MessageSquare
} from 'lucide-react';

import { TridentIcon } from './TridentIcon';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Sidebar width constraints
const MIN_WIDTH = 56;  // Collapsed width
const MAX_WIDTH = 280; // Maximum expanded width
const DEFAULT_WIDTH = 220; // Default expanded width
const COLLAPSE_THRESHOLD = 100; // Below this, snap to collapsed

const Sidebar = ({ user }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem('sidebarWidth');
    return saved ? parseInt(saved, 10) : DEFAULT_WIDTH;
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isTicketsExpanded, setIsTicketsExpanded] = useState(true);
  const [isCollapsedMenuOpen, setIsCollapsedMenuOpen] = useState(false);
  const collapsedMenuRef = useRef(null);
  const sidebarRef = useRef(null);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  const isExpanded = sidebarWidth > COLLAPSE_THRESHOLD;

  const ticketViews = [
    { id: 'all-tickets', label: 'All Tickets', icon: List, path: '/all-tickets' },
    { id: 'starred-tickets', label: 'Starred', icon: Star, path: '/starred-tickets' },
    { id: 'open-tickets', label: 'Open', icon: UserCheck, path: '/open-tickets' },
    { id: 'waiting-tickets', label: 'Waiting', icon: Clock, path: '/waiting-tickets' },
    { id: 'closed-tickets', label: 'Closed', icon: CheckCircle, path: '/closed-tickets' },
  ];

  const mainItems = [
    { id: 'customers', label: 'Customers', icon: UserCircle, path: '/customers' },
    { id: 'analytics', label: 'Analytics', icon: BarChart3, path: '/analytics' },
    { id: 'canned-responses', label: 'Canned Responses', icon: MessageSquare, path: '/canned-responses' },
    { id: 'teams', label: 'Teams', icon: Users, path: '/teams' },
    { id: 'leaves', label: 'Leaves', icon: CalendarDays, path: '/leaves' },
    { id: 'feature-requests', label: 'Features', icon: Bookmark, path: '/feature-requests' },
    { id: 'profile', label: 'Profile', icon: User, path: '/profile' },
    { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
    { id: 'admin', label: 'Admin', icon: Shield, path: '/admin' },
  ];

  // Save width to localStorage
  useEffect(() => {
    localStorage.setItem('sidebarWidth', sidebarWidth.toString());
  }, [sidebarWidth]);

  // Handle drag start
  const handleDragStart = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
    dragStartX.current = e.clientX || e.touches?.[0]?.clientX || 0;
    dragStartWidth.current = sidebarWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [sidebarWidth]);

  // Handle drag move
  const handleDragMove = useCallback((e) => {
    if (!isDragging) return;
    
    const clientX = e.clientX || e.touches?.[0]?.clientX || 0;
    const delta = clientX - dragStartX.current;
    let newWidth = dragStartWidth.current + delta;
    
    // Snap to collapsed if below threshold
    if (newWidth < COLLAPSE_THRESHOLD) {
      newWidth = MIN_WIDTH;
    } else {
      // Clamp between threshold and max
      newWidth = Math.min(Math.max(newWidth, COLLAPSE_THRESHOLD), MAX_WIDTH);
    }
    
    setSidebarWidth(newWidth);
  }, [isDragging]);

  // Handle drag end
  const handleDragEnd = useCallback(() => {
    setIsDragging(false);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }, []);

  // Add/remove event listeners for dragging
  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleDragMove);
      window.addEventListener('mouseup', handleDragEnd);
      window.addEventListener('touchmove', handleDragMove);
      window.addEventListener('touchend', handleDragEnd);
    }
    
    return () => {
      window.removeEventListener('mousemove', handleDragMove);
      window.removeEventListener('mouseup', handleDragEnd);
      window.removeEventListener('touchmove', handleDragMove);
      window.removeEventListener('touchend', handleDragEnd);
    };
  }, [isDragging, handleDragMove, handleDragEnd]);

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
    if (isExpanded && isCollapsedMenuOpen) {
      const timer = setTimeout(() => setIsCollapsedMenuOpen(false), 0);
      return () => clearTimeout(timer);
    }
  }, [isExpanded, isCollapsedMenuOpen]);

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
      navigate('/login', { replace: true });
    } catch (error) {
      console.error('Logout error:', error);
      navigate('/login', { replace: true });
    }
  };

  // Double-click to toggle between collapsed and default
  const handleDoubleClick = () => {
    if (sidebarWidth <= MIN_WIDTH) {
      setSidebarWidth(DEFAULT_WIDTH);
    } else {
      setSidebarWidth(MIN_WIDTH);
    }
  };

  // Helper to render nav item inline
  const renderNavItem = (item, nested = false) => {
    const Icon = item.icon;
    const active = isActive(item.path);
    
    return (
      <button
        key={item.id}
        onClick={() => handleNavigate(item.path)}
        className={`
          w-full flex items-center gap-2 h-8 rounded-md text-[13px] overflow-hidden
          transition-colors
          ${active 
            ? 'bg-primary/12 text-primary font-medium' 
            : 'text-foreground/70 hover:text-foreground hover:bg-secondary/50'
          }
          ${!isExpanded && !nested ? 'justify-center px-2' : nested ? 'px-2 ml-5' : 'px-2.5'}
        `}
        data-testid={`nav-${item.id}`}
        title={!isExpanded ? item.label : undefined}
      >
        <Icon size={15} className={`shrink-0 ${active ? 'text-primary' : ''}`} />
        {(isExpanded || nested) && <span className="truncate">{item.label}</span>}
      </button>
    );
  };

  const renderDesktopNav = () => (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Main Navigation - No scroll */}
      <nav className="px-2 py-3 space-y-0.5">
        {/* Dashboard */}
        <button
          onClick={() => handleNavigate('/dashboard')}
          className={`
            w-full flex items-center gap-2.5 h-9 rounded-md text-[13px]
            transition-interactive focus-ring
            ${isActive('/dashboard')
              ? 'bg-primary/12 text-primary font-medium' 
              : 'text-foreground/70 hover:text-foreground hover:bg-secondary/50'
            }
            ${!isExpanded ? 'justify-center px-2' : 'px-2.5'}
          `}
          data-testid="nav-dashboard"
          title={!isExpanded ? 'Dashboard' : undefined}
        >
          <LayoutDashboard size={16} className={isActive('/dashboard') ? 'text-primary' : ''} />
          {isExpanded && <span>Dashboard</span>}
        </button>

        {/* Tickets Section */}
        {isExpanded ? (
          <div>
            <button
              onClick={() => setIsTicketsExpanded(!isTicketsExpanded)}
              className={`
                w-full flex items-center justify-between px-2.5 h-9 rounded-md text-[13px]
                transition-interactive focus-ring
                ${isTicketViewActive ? 'text-primary font-medium' : 'text-foreground/70 hover:text-foreground hover:bg-secondary/50'}
              `}
              data-testid="nav-tickets-toggle"
            >
              <div className="flex items-center gap-2.5">
                <List size={16} className={isTicketViewActive ? 'text-primary' : ''} />
                <span>Tickets</span>
              </div>
              <ChevronDown size={14} className={`transition-transform duration-200 ${isTicketsExpanded ? 'rotate-180' : ''}`} />
            </button>
            
            {isTicketsExpanded && (
              <div className="mt-0.5 space-y-0.5">
                {ticketViews.map(view => renderNavItem(view, true))}
              </div>
            )}
          </div>
        ) : (
          <div className="relative" ref={collapsedMenuRef}>
            <button
              onClick={() => setIsCollapsedMenuOpen(!isCollapsedMenuOpen)}
              className={`
                w-full flex items-center justify-center px-2 h-9 rounded-md
                transition-interactive focus-ring
                ${isTicketViewActive || isCollapsedMenuOpen 
                  ? 'bg-primary/12 text-primary' 
                  : 'text-foreground/70 hover:text-foreground hover:bg-secondary/50'
                }
              `}
              title="Tickets"
              data-testid="collapsed-tickets-toggle"
            >
              <List size={16} />
            </button>
            
            {isCollapsedMenuOpen && (
              <div className="absolute left-full top-0 ml-2 z-50">
                <div className="card-premium rounded-lg p-1.5 min-w-[180px] shadow-xl">
                  <div className="px-2.5 py-1.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
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
                          w-full flex items-center gap-2.5 px-2.5 h-9 rounded-md text-[13px]
                          transition-interactive focus-ring
                          ${active 
                            ? 'bg-primary/12 text-primary font-medium' 
                            : 'text-foreground/70 hover:text-foreground hover:bg-secondary/50'
                          }
                        `}
                      >
                        <Icon size={16} className={active ? 'text-primary' : ''} />
                        <span>{view.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Divider */}
        <div className="!my-2 h-px bg-border/50" />

        {/* Other Items */}
        {mainItems.map(item => renderNavItem(item, false))}
      </nav>

      {/* Spacer */}
      <div className="flex-1" />

      {/* User Section - Always at bottom */}
      <div className="p-2 border-t border-border/40">
        {isExpanded && user && (
          <div className="px-2 py-2 mb-1">
            <div className="flex items-center gap-2">
              {user.picture ? (
                <img src={user.picture} alt={user.name} className="w-8 h-8 rounded-full" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary text-xs font-semibold">
                  {user.name?.charAt(0).toUpperCase()}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-medium truncate">{user.name}</p>
                <p className="text-[11px] text-muted-foreground truncate">{user.email}</p>
              </div>
            </div>
          </div>
        )}
        
        {/* Sign Out */}
        <button
          onClick={handleLogout}
          className={`
            w-full flex items-center gap-2.5 h-9 rounded-md text-[13px]
            text-muted-foreground hover:text-foreground hover:bg-secondary/50
            transition-interactive focus-ring
            ${!isExpanded ? 'justify-center px-2' : 'px-2.5'}
          `}
          data-testid="logout-button-sidebar"
          title={!isExpanded ? 'Sign Out' : undefined}
        >
          <LogOut size={16} />
          {isExpanded && <span>Sign Out</span>}
        </button>
      </div>
    </div>
  );

  const renderMobileNav = () => (
    <div className="flex-1 flex flex-col min-h-0">
      <nav className="flex-1 px-2 py-3 space-y-0.5">
        <button
          onClick={() => handleNavigate('/dashboard')}
          className={`
            w-full flex items-center gap-2.5 px-2.5 h-9 rounded-md text-[13px]
            transition-interactive focus-ring
            ${isActive('/dashboard')
              ? 'bg-primary/12 text-primary font-medium' 
              : 'text-foreground/70 hover:text-foreground hover:bg-secondary/50'
            }
          `}
        >
          <LayoutDashboard size={16} />
          <span>Dashboard</span>
        </button>

        <div>
          <button
            onClick={() => setIsTicketsExpanded(!isTicketsExpanded)}
            className={`
              w-full flex items-center justify-between px-2.5 h-9 rounded-md text-[13px]
              transition-interactive focus-ring
              ${isTicketViewActive ? 'text-primary font-medium' : 'text-foreground/70 hover:text-foreground hover:bg-secondary/50'}
            `}
          >
            <div className="flex items-center gap-2.5">
              <List size={16} />
              <span>Tickets</span>
            </div>
            <ChevronDown size={14} className={`transition-transform duration-200 ${isTicketsExpanded ? 'rotate-180' : ''}`} />
          </button>
          
          {isTicketsExpanded && (
            <div className="mt-0.5 space-y-0.5">
              {ticketViews.map(view => {
                const Icon = view.icon;
                const active = isActive(view.path);
                return (
                  <button
                    key={view.id}
                    onClick={() => handleNavigate(view.path)}
                    className={`
                      w-full flex items-center gap-2.5 px-2.5 ml-6 h-9 rounded-md text-[13px]
                      transition-interactive focus-ring
                      ${active 
                        ? 'bg-primary/12 text-primary font-medium' 
                        : 'text-foreground/70 hover:text-foreground hover:bg-secondary/50'
                      }
                    `}
                  >
                    <Icon size={16} />
                    <span>{view.label}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="!my-2 h-px bg-border/50" />

        {mainItems.map(item => {
          const Icon = item.icon;
          const active = isActive(item.path);
          return (
            <button
              key={item.id}
              onClick={() => handleNavigate(item.path)}
              className={`
                w-full flex items-center gap-2.5 px-2.5 h-9 rounded-md text-[13px]
                transition-interactive focus-ring
                ${active 
                  ? 'bg-primary/12 text-primary font-medium' 
                  : 'text-foreground/70 hover:text-foreground hover:bg-secondary/50'
                }
              `}
            >
              <Icon size={16} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Mobile User Section */}
      {user && (
        <div className="p-3 border-t border-border/40">
          <div className="flex items-center gap-2.5 mb-2">
            {user.picture ? (
              <img src={user.picture} alt={user.name} className="w-8 h-8 rounded-full" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary text-xs font-semibold">
                {user.name?.charAt(0).toUpperCase()}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-medium truncate">{user.name}</p>
              <p className="text-[11px] text-muted-foreground truncate">{user.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 h-9 rounded-md text-[13px] text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-interactive"
            data-testid="logout-button-mobile"
          >
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 h-10 w-10 flex items-center justify-center rounded-lg glass hover:bg-secondary/60 transition-interactive focus-ring"
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

      {/* Desktop Sidebar */}
      <div 
        className="shrink-0 hidden lg:block"
        style={{ width: sidebarWidth }}
      >
        <aside
          ref={sidebarRef}
          className="fixed top-0 left-0 h-screen z-40 bg-card/80 backdrop-blur-xl border-r border-border/50 flex flex-col"
          style={{ width: sidebarWidth }}
          data-testid="sidebar"
        >
          {/* Header */}
          <div className="h-14 flex items-center justify-center px-3 border-b border-border/40 shrink-0">
            {isExpanded ? (
              <div className="flex items-center gap-2">
                <TridentIcon size={20} className="text-primary" strokeWidth={2.5} />
                <span className="brand text-base font-bold tracking-tight">Trinity</span>
              </div>
            ) : (
              <TridentIcon size={20} className="text-primary" strokeWidth={2.5} />
            )}
          </div>

          {renderDesktopNav()}
          
          {/* Drag Handle */}
          <div
            className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize group hover:bg-primary/30 transition-colors"
            onMouseDown={handleDragStart}
            onTouchStart={handleDragStart}
            onDoubleClick={handleDoubleClick}
            title="Drag to resize • Double-click to toggle"
            data-testid="sidebar-drag-handle"
          >
            {/* Visual indicator on hover */}
            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-12 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="w-1 h-8 rounded-full bg-primary/50" />
            </div>
          </div>
        </aside>
      </div>

      {/* Drag overlay to prevent text selection during drag */}
      {isDragging && (
        <div className="fixed inset-0 z-50 cursor-col-resize" />
      )}

      {/* Mobile Sidebar */}
      <aside
        className={`
          lg:hidden fixed top-0 left-0 h-screen w-56 z-40 
          bg-card/95 backdrop-blur-xl border-r border-border/50
          transition-transform duration-200 ease-out flex flex-col
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Header */}
        <div className="h-14 flex items-center px-4 border-b border-border/40 shrink-0">
          <div className="flex items-center gap-2">
            <TridentIcon size={20} className="text-primary" strokeWidth={2.5} />
            <span className="brand text-base font-bold">Trinity</span>
          </div>
        </div>

        {renderMobileNav()}
      </aside>
    </>
  );
};

export default Sidebar;
