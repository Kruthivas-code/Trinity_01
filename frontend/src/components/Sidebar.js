import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, List, Clock, UserCheck, CheckCircle, Settings, 
  User, ChevronDown, Menu, X, LogOut, Users, Shield, CalendarDays,
  Bookmark, BarChart3, UserCircle, Star, MessageSquare,
  Inbox, AlertTriangle, Zap, ChevronRight, MoreHorizontal, Pencil, Trash2, Share2
} from 'lucide-react';
import { clearCachedUser } from './ProtectedRoute';
import ShareInboxModal from './ShareInboxModal';
import EditInboxModal from './EditInboxModal';

import { TridentIcon } from './TridentIcon';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const MIN_WIDTH = 56;
const MAX_WIDTH = 280;
const DEFAULT_WIDTH = 260;
const COLLAPSE_THRESHOLD = 100;

const Sidebar = ({ user, customInboxes = [], onInboxesChange }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem('sidebarWidth');
    return saved ? parseInt(saved, 10) : DEFAULT_WIDTH;
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isTicketsExpanded, setIsTicketsExpanded] = useState(true);
  const [isEscalationExpanded, setIsEscalationExpanded] = useState(true);
  const [escalationCounts, setEscalationCounts] = useState({ L1: { total: 0 }, L2: { total: 0 }, L3: { total: 0 } });
  const [inboxMenuOpen, setInboxMenuOpen] = useState(null); // inbox_id of open menu
  const [shareModalInbox, setShareModalInbox] = useState(null);
  const [editModalInbox, setEditModalInbox] = useState(null);
  const sidebarRef = useRef(null);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  const isExpanded = sidebarWidth > COLLAPSE_THRESHOLD;

  // Fetch escalation counts
  useEffect(() => {
    const fetchCounts = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/tickets/escalation-counts`, {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          setEscalationCounts(data);
        }
      } catch (error) {
        console.error('Failed to fetch escalation counts:', error);
      }
    };
    fetchCounts();
    const interval = setInterval(fetchCounts, 30000);
    return () => clearInterval(interval);
  }, []);

  const ticketViews = [
    { id: 'all-tickets', label: 'All Tickets', icon: Inbox, path: '/all-tickets' },
    { id: 'starred-tickets', label: 'Starred', icon: Star, path: '/starred-tickets' },
    { id: 'open-tickets', label: 'Open', icon: UserCheck, path: '/open-tickets' },
    { id: 'waiting-tickets', label: 'Waiting', icon: Clock, path: '/waiting-tickets' },
    { id: 'closed-tickets', label: 'Closed', icon: CheckCircle, path: '/closed-tickets' },
  ];

  const escalationFolders = [
    { 
      id: 'l1', level: 'L1', label: 'L1 - Basic', icon: Inbox,
      dotColor: 'bg-emerald-500', chipBg: 'bg-emerald-50', chipText: 'text-emerald-800', chipBorder: 'border-emerald-200',
      path: '/all-tickets?level=L1'
    },
    { 
      id: 'l2', level: 'L2', label: 'L2 - Intermediate', icon: AlertTriangle,
      dotColor: 'bg-amber-500', chipBg: 'bg-amber-50', chipText: 'text-amber-900', chipBorder: 'border-amber-200',
      path: '/all-tickets?level=L2'
    },
    { 
      id: 'l3', level: 'L3', label: 'L3 - Advanced', icon: Zap,
      dotColor: 'bg-rose-500', chipBg: 'bg-rose-50', chipText: 'text-rose-800', chipBorder: 'border-rose-200',
      path: '/all-tickets?level=L3'
    },
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

  useEffect(() => {
    localStorage.setItem('sidebarWidth', sidebarWidth.toString());
  }, [sidebarWidth]);

  const handleDragStart = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
    dragStartX.current = e.clientX || e.touches?.[0]?.clientX || 0;
    dragStartWidth.current = sidebarWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [sidebarWidth]);

  const handleDragMove = useCallback((e) => {
    if (!isDragging) return;
    const clientX = e.clientX || e.touches?.[0]?.clientX || 0;
    const delta = clientX - dragStartX.current;
    let newWidth = dragStartWidth.current + delta;
    if (newWidth < COLLAPSE_THRESHOLD) {
      newWidth = MIN_WIDTH;
    } else {
      newWidth = Math.min(Math.max(newWidth, COLLAPSE_THRESHOLD), MAX_WIDTH);
    }
    setSidebarWidth(newWidth);
  }, [isDragging]);

  const handleDragEnd = useCallback(() => {
    setIsDragging(false);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }, []);

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

  const isActive = (path) => {
    if (path.includes('?level=')) {
      const level = path.split('level=')[1];
      return location.pathname === '/all-tickets' && location.search.includes(`level=${level}`);
    }
    return location.pathname === path;
  };
  
  const isTicketViewActive = ticketViews.some(view => isActive(view.path));

  const handleNavigate = (path) => {
    // Handle paths with query params
    if (path.includes('?')) {
      const [pathname, search] = path.split('?');
      navigate(`${pathname}?${search}`);
    } else {
      navigate(path);
    }
    setIsMobileOpen(false);
    setInboxMenuOpen(null);
  };

  const handleLogout = async () => {
    try {
      await fetch(`${BACKEND_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
      localStorage.removeItem('theme');
      clearCachedUser();
      navigate('/login', { replace: true });
    } catch (error) {
      console.error('Logout error:', error);
      clearCachedUser();
      navigate('/login', { replace: true });
    }
  };

  const handleDoubleClick = () => {
    if (sidebarWidth <= MIN_WIDTH) {
      setSidebarWidth(DEFAULT_WIDTH);
    } else {
      setSidebarWidth(MIN_WIDTH);
    }
  };

  const renderNavItem = (item, nested = false) => {
    const Icon = item.icon;
    const active = isActive(item.path);
    
    return (
      <button
        key={item.id}
        onClick={() => handleNavigate(item.path)}
        className={`
          w-full flex items-center gap-2.5 rounded-lg text-[14px] overflow-hidden relative
          transition-colors duration-150
          ${active 
            ? 'bg-foreground/8 text-foreground font-semibold' 
            : 'text-foreground/55 hover:text-foreground hover:bg-foreground/[0.05]'
          }
          ${!isExpanded && !nested ? 'justify-center px-2 h-9' : nested ? 'px-3 ml-4 h-9' : 'px-3 h-9'}
        `}
        data-testid={`nav-${item.id}`}
        title={!isExpanded ? item.label : undefined}
      >
        {active && (
          <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-foreground" />
        )}
        <Icon size={16} className={`shrink-0 ${active ? 'text-foreground' : ''}`} />
        {(isExpanded || nested) && <span className="truncate">{item.label}</span>}
      </button>
    );
  };

  const renderDesktopNav = () => (
    <div className="flex-1 flex flex-col min-h-0 overflow-y-auto overflow-x-hidden">
      <nav className="px-2 py-3 space-y-0.5">
        {/* Dashboard */}
        <button
          onClick={() => handleNavigate('/dashboard')}
          className={`
            w-full flex items-center gap-2.5 rounded-lg text-[14px] overflow-hidden relative
            transition-colors duration-150
            ${isActive('/dashboard')
              ? 'bg-foreground/8 text-foreground font-semibold' 
              : 'text-foreground/55 hover:text-foreground hover:bg-foreground/[0.05]'
            }
            ${!isExpanded ? 'justify-center px-2 h-9' : 'px-3 h-9'}
          `}
          data-testid="nav-dashboard"
          title={!isExpanded ? 'Dashboard' : undefined}
        >
          {isActive('/dashboard') && (
            <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-foreground" />
          )}
          <LayoutDashboard size={16} className={isActive('/dashboard') ? 'text-foreground' : ''} />
          {isExpanded && <span>Dashboard</span>}
        </button>

        {/* Tickets Section */}
        {isExpanded && (
          <div>
            <button
              onClick={() => setIsTicketsExpanded(!isTicketsExpanded)}
              className={`
                w-full flex items-center justify-between px-3 h-9 rounded-lg text-[14px] overflow-hidden
                transition-colors duration-150
                ${isTicketViewActive ? 'text-foreground font-semibold' : 'text-foreground/55 hover:text-foreground hover:bg-foreground/[0.05]'}
              `}
              data-testid="nav-tickets-toggle"
            >
              <div className="flex items-center gap-2.5">
                <List size={16} />
                <span>Tickets</span>
              </div>
              <ChevronDown size={14} className={`transition-transform duration-200 ${isTicketsExpanded ? '' : '-rotate-90'}`} />
            </button>
            
            {isTicketsExpanded && (
              <div className="mt-0.5 space-y-0.5">
                {ticketViews.map(view => renderNavItem(view, true))}
                
                {/* Custom Inboxes */}
                {customInboxes.length > 0 && (
                  <>
                    <div className="!my-2 mx-3 h-px bg-border/40" />
                    {customInboxes.map(inbox => {
                      const inboxPath = `/inbox/${inbox.inbox_id}`;
                      const active = location.pathname === inboxPath;
                      return (
                        <div key={inbox.inbox_id} className="relative group" data-testid={`sidebar-inbox-${inbox.inbox_id}`}>
                          <button
                            onClick={() => handleNavigate(inboxPath)}
                            className={`
                              w-full flex items-center gap-2.5 px-3 ml-4 h-9 rounded-lg text-[14px] overflow-hidden relative
                              transition-colors duration-150
                              ${active 
                                ? 'bg-foreground/8 text-foreground font-semibold' 
                                : 'text-foreground/55 hover:text-foreground hover:bg-foreground/[0.05]'
                              }
                            `}
                          >
                            {active && (
                              <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-foreground" />
                            )}
                            <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: inbox.color || '#6b7280' }} />
                            <span className="truncate flex-1 text-left">{inbox.name}</span>
                          </button>
                          {/* 3-dot menu trigger */}
                          <button
                            onClick={(e) => { e.stopPropagation(); setInboxMenuOpen(inboxMenuOpen === inbox.inbox_id ? null : inbox.inbox_id); }}
                            className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 flex items-center justify-center rounded-md opacity-0 group-hover:opacity-100 hover:bg-muted transition-opacity"
                            data-testid={`inbox-menu-trigger-${inbox.inbox_id}`}
                          >
                            <MoreHorizontal size={14} />
                          </button>
                          {/* 3-dot dropdown */}
                          {inboxMenuOpen === inbox.inbox_id && (
                            <div className="absolute right-0 top-full z-50 mt-1 w-40 rounded-lg border border-border bg-background shadow-lg py-1 animate-in fade-in zoom-in-95 duration-150" data-testid={`inbox-menu-${inbox.inbox_id}`}>
                              <button
                                onClick={() => { handleNavigate(inboxPath); setInboxMenuOpen(null); }}
                                className="w-full flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-muted text-left"
                                data-testid={`inbox-edit-${inbox.inbox_id}`}
                              >
                                <Pencil size={13} /> Edit filters
                              </button>
                              <button
                                onClick={async () => {
                                  setInboxMenuOpen(null);
                                  const users = await fetch(`${BACKEND_URL}/api/users`, { credentials: 'include' }).then(r => r.json());
                                  const userIds = users.filter(u => u.user_id !== user?.user_id).map(u => u.user_id);
                                  if (userIds.length === 0) { alert('No other users to share with'); return; }
                                  const res = await fetch(`${BACKEND_URL}/api/inboxes/${inbox.inbox_id}/share`, {
                                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                                    body: JSON.stringify({ user_ids: userIds })
                                  });
                                  if (res.ok) { const d = await res.json(); alert(`Shared with ${d.total} user(s)`); }
                                }}
                                className="w-full flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-muted text-left"
                                data-testid={`inbox-share-${inbox.inbox_id}`}
                              >
                                <Share2 size={13} /> Share
                              </button>
                              <div className="my-1 h-px bg-border" />
                              <button
                                onClick={async () => {
                                  setInboxMenuOpen(null);
                                  if (!window.confirm(`Delete "${inbox.name}"?`)) return;
                                  const res = await fetch(`${BACKEND_URL}/api/inboxes/${inbox.inbox_id}`, { method: 'DELETE', credentials: 'include' });
                                  if (res.ok && onInboxesChange) onInboxesChange();
                                }}
                                className="w-full flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-muted text-left text-red-500"
                                data-testid={`inbox-delete-${inbox.inbox_id}`}
                              >
                                <Trash2 size={13} /> Delete
                              </button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* Divider */}
        <div className="!my-3 h-px bg-border/60" />

        {/* L1 / L2 / L3 Escalation Folders */}
        {isExpanded && (
          <div>
            <button
              onClick={() => setIsEscalationExpanded(!isEscalationExpanded)}
              className="w-full flex items-center justify-between px-3 h-9 rounded-lg text-[14px] text-foreground/55 hover:text-foreground hover:bg-foreground/[0.05] transition-colors duration-150"
              data-testid="nav-escalation-toggle"
            >
              <div className="flex items-center gap-2.5">
                <Zap size={16} />
                <span className="font-medium text-foreground/80">Escalation</span>
              </div>
              <ChevronDown size={14} className={`transition-transform duration-200 ${isEscalationExpanded ? '' : '-rotate-90'}`} />
            </button>

            {isEscalationExpanded && (
              <div className="mt-1 space-y-0.5">
                {escalationFolders.map(folder => {
                  const Icon = folder.icon;
                  const active = isActive(folder.path);
                  const count = escalationCounts[folder.level]?.total || 0;
                  
                  return (
                    <button
                      key={folder.id}
                      onClick={() => handleNavigate(folder.path)}
                      className={`
                        w-full flex items-center gap-2.5 px-3 ml-4 h-10 rounded-lg text-[14px] overflow-hidden relative
                        transition-colors duration-150
                        ${active 
                          ? 'bg-foreground/8 text-foreground font-semibold' 
                          : 'text-foreground/55 hover:text-foreground hover:bg-foreground/[0.05]'
                        }
                      `}
                      data-testid={`sidebar-${folder.id}-folder-button`}
                    >
                      {active && (
                        <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-foreground" />
                      )}
                      <div className={`w-2 h-2 rounded-full ${folder.dotColor} shrink-0`} />
                      <span className="truncate flex-1 text-left">{folder.label}</span>
                      {count > 0 && (
                        <span className={`shrink-0 text-[11px] font-medium px-1.5 py-0.5 rounded-md border ${folder.chipBg} ${folder.chipText} ${folder.chipBorder}`}>
                          {count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Divider */}
        <div className="!my-3 h-px bg-border/60" />

        {/* Other Items */}
        {mainItems.map(item => renderNavItem(item, false))}
      </nav>

      <div className="flex-1" />

      {/* User Section */}
      <div className="p-2 border-t border-border/40">
        {isExpanded && user && (
          <div className="px-3 py-2.5 mb-1">
            <div className="flex items-center gap-2.5">
              {user.picture ? (
                <img src={user.picture} alt={user.name} className="w-8 h-8 rounded-full" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-foreground/10 flex items-center justify-center text-foreground text-sm font-semibold">
                  {user.name?.charAt(0).toUpperCase()}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-[14px] font-medium truncate">{user.name}</p>
                <p className="text-[12px] text-muted-foreground truncate">{user.email}</p>
              </div>
            </div>
          </div>
        )}
        
        <button
          onClick={handleLogout}
          className={`
            w-full flex items-center gap-2.5 h-9 rounded-lg text-[14px]
            text-muted-foreground hover:text-foreground hover:bg-foreground/[0.05]
            transition-colors duration-150
            ${!isExpanded ? 'justify-center px-2' : 'px-3'}
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

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 h-10 w-10 flex items-center justify-center rounded-lg border border-border bg-background hover:bg-secondary transition-colors duration-150"
        data-testid="mobile-menu-button"
      >
        {isMobileOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/30 z-40"
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
          className="fixed top-0 left-0 h-screen z-40 bg-card border-r border-border flex flex-col"
          style={{ width: sidebarWidth }}
          data-testid="sidebar"
        >
          {/* Header */}
          <div className="h-14 flex items-center justify-center px-3 border-b border-border shrink-0">
            {isExpanded ? (
              <div className="flex items-center gap-2.5">
                <TridentIcon size={22} className="text-foreground" strokeWidth={2.5} />
                <span className="brand text-lg font-bold tracking-tight text-foreground">Trinity</span>
              </div>
            ) : (
              <TridentIcon size={22} className="text-foreground" strokeWidth={2.5} />
            )}
          </div>

          {renderDesktopNav()}
          
          {/* Drag Handle */}
          <div
            className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize group hover:bg-foreground/10 transition-colors duration-150"
            onMouseDown={handleDragStart}
            onTouchStart={handleDragStart}
            onDoubleClick={handleDoubleClick}
            title="Drag to resize"
            data-testid="sidebar-drag-handle"
          >
            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-12 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-150">
              <div className="w-1 h-8 rounded-full bg-foreground/20" />
            </div>
          </div>
        </aside>
      </div>

      {isDragging && (
        <div className="fixed inset-0 z-50 cursor-col-resize" />
      )}

      {/* Mobile Sidebar */}
      <aside
        className={`
          lg:hidden fixed top-0 left-0 h-screen w-64 z-40 
          bg-card border-r border-border
          transition-transform duration-200 ease-out flex flex-col
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
        data-testid="sidebar-mobile"
      >
        <div className="h-14 flex items-center px-4 border-b border-border shrink-0">
          <div className="flex items-center gap-2.5">
            <TridentIcon size={22} className="text-foreground" strokeWidth={2.5} />
            <span className="brand text-lg font-bold text-foreground">Trinity</span>
          </div>
        </div>
        {renderDesktopNav()}
      </aside>
    </>
  );
};

export default Sidebar;
