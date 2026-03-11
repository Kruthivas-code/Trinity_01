import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Clock, User as UserIcon, ArrowUpDown, ArrowUp, ArrowDown, Check, Tag, Mail } from 'lucide-react';
import { useRealtime } from '../../contexts/RealtimeContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const FilterBuilder = React.lazy(() => import('./FilterBuilder'));
const SaveInboxModal = React.lazy(() => import('../inbox/SaveInboxModal'));
const ITEMS_PER_PAGE = 50;

const SORT_OPTIONS = [
  { value: 'created_at', label: 'Created' },
  { value: 'updated_at', label: 'Updated' },
  { value: 'last_message_at', label: 'Last message' },
  { value: 'last_customer_message_at', label: 'Last customer msg' },
  { value: 'last_agent_message_at', label: 'Last agent msg' },
  { value: 'priority', label: 'Priority' },
  { value: 'status', label: 'Status' },
  { value: 'escalation_level', label: 'Escalation' },
];

// Get the best preview text for a ticket
const getPreviewText = (ticket) => {
  // For email tickets, prefer the pre-generated preview
  if (ticket.source === 'email' && ticket.email_preview) {
    return ticket.email_preview;
  }
  // For email tickets without preview, use email_text
  if (ticket.source === 'email' && ticket.email_text) {
    const text = ticket.email_text.slice(0, 200);
    return text.length < ticket.email_text.length ? text + '...' : text;
  }
  // Fall back to description
  if (ticket.description) {
    return stripHtml(ticket.description);
  }
  return '';
};

// Strip HTML tags and CSS for display
const stripHtml = (html) => {
  if (!html) return '';
  // Remove style tags and their content
  let text = html.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
  // Remove script tags
  text = text.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
  // Remove HTML tags
  text = text.replace(/<[^>]*>/g, ' ');
  // Remove CSS properties that might be in text
  text = text.replace(/[\w-]+\s*:\s*[^;]+;/g, ' ');
  // Decode common HTML entities
  text = text.replace(/&nbsp;/g, ' ')
             .replace(/&amp;/g, '&')
             .replace(/&lt;/g, '<')
             .replace(/&gt;/g, '>')
             .replace(/&quot;/g, '"')
             .replace(/&#39;/g, "'")
             .replace(/&#\d+;/g, ' ');
  // Remove multiple spaces and trim
  return text.replace(/\s+/g, ' ').trim();
};

const getPriorityColor = (priority) => {
  switch (priority) {
    case 'urgent': return 'bg-red-500';
    case 'high': return 'bg-orange-500';
    case 'medium': return 'bg-yellow-500';
    case 'low': return 'bg-green-500';
    default: return 'bg-gray-500';
  }
};

const getStatusBadge = (status) => {
  const badges = {
    todo: { label: 'To Do', class: 'bg-slate-100 text-slate-700 border-slate-200' },
    in_progress: { label: 'In Progress', class: 'bg-blue-50 text-blue-700 border-blue-200' },
    waiting: { label: 'Waiting', class: 'bg-amber-50 text-amber-700 border-amber-200' },
    review: { label: 'Review', class: 'bg-violet-50 text-violet-700 border-violet-200' },
    closed: { label: 'Closed', class: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  };
  return badges[status] || { label: status, class: 'bg-gray-100 text-gray-600 border-gray-200' };
};

const formatTimeAgo = (dateString) => {
  const date = new Date(dateString?.endsWith?.('Z') ? dateString : dateString + 'Z');
  return date.toLocaleString('en-US', {
    timeZone: 'Asia/Kolkata',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
};

const formatRelativeAge = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString?.endsWith?.('Z') ? dateString : dateString + 'Z');
  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d`;
  const months = Math.floor(days / 30);
  return `${months}mo`;
};

const TicketsListView = ({ title, subtitle, filterStatuses, escalationLevel, user, onTicketClick, refreshKey, filterTree: propFilterTree, showFilterBuilder, onSaveInbox, customParams, excludeZeus }) => {
  const [tickets, setTickets] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const observerTarget = useRef(null);
  const [activeFilterTree, setActiveFilterTree] = useState(propFilterTree || null);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [showSortMenu, setShowSortMenu] = useState(false);
  const sortRef = useRef(null);
  
  const { onTicketUpdate } = useRealtime();

  // Close sort menu on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (sortRef.current && !sortRef.current.contains(e.target)) {
        setShowSortMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Subscribe to real-time ticket updates
  useEffect(() => {
    const unsubscribe = onTicketUpdate((data) => {
      if (data.ticket) {
        const ticket = data.ticket;
        const matchesFilter = !filterStatuses || filterStatuses.includes(ticket.status);
        
        setTickets(prev => {
          const existingIndex = prev.findIndex(t => t.ticket_id === ticket.ticket_id);
          
          if (existingIndex >= 0) {
            if (matchesFilter) {
              const updated = [...prev];
              updated[existingIndex] = { ...updated[existingIndex], ...ticket };
              return updated;
            } else {
              return prev.filter(t => t.ticket_id !== ticket.ticket_id);
            }
          } else if (matchesFilter) {
            return [ticket, ...prev];
          }
          return prev;
        });
      } else if (data.ticket_id && data.deleted) {
        setTickets(prev => prev.filter(t => t.ticket_id !== data.ticket_id));
      }
    });
    
    return unsubscribe;
  }, [onTicketUpdate, filterStatuses]);

  const fetchUsers = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/users`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to fetch users');
      const data = await response.json();
      setUsers(Array.isArray(data) ? data : (data.items || []));
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const fetchTickets = async (pageNum) => {
    try {
      setLoading(true);
      let data;
      
      if (activeFilterTree) {
        // Use advanced filter endpoint
        const response = await fetch(`${BACKEND_URL}/api/filter/tickets`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            filter_tree: activeFilterTree,
            page: pageNum,
            limit: ITEMS_PER_PAGE,
            sort_by: sortBy,
            sort_order: sortOrder,
          }),
        });
        if (!response.ok) throw new Error('Failed to filter tickets');
        data = await response.json();
      } else {
        // Use existing simple filter endpoint
        const params = new URLSearchParams();
        if (escalationLevel) {
          params.set('escalation_level', escalationLevel);
        }
        if (filterStatuses && filterStatuses.length > 0) {
          filterStatuses.forEach(s => params.append('status', s));
        }
        params.set('page', pageNum);
        params.set('limit', ITEMS_PER_PAGE);
        params.set('sort_by', sortBy);
        params.set('sort_order', sortOrder);
        // Append custom params (e.g., atlas_assigned_to_zeus=true)
        if (customParams) {
          Object.entries(customParams).forEach(([k, v]) => params.set(k, v));
        }
        if (excludeZeus) {
          params.set('atlas_assigned_to_zeus', 'false');
        }
        
        const url = `${BACKEND_URL}/api/tickets?${params.toString()}`;
        const response = await fetch(url, { credentials: 'include' });
        if (!response.ok) throw new Error('Failed to fetch tickets');
        data = await response.json();
      }
      
      const newTickets = data.tickets || [];
      setTotalCount(data.total || newTickets.length);
      
      if (pageNum === 1) {
        setTickets(newTickets);
      } else {
        setTickets(prev => [...prev, ...newTickets]);
      }
      
      setHasMore(data.has_more || false);
    } catch (error) {
      console.error('Failed to fetch tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    setPage(1);
    setTickets([]);
    setHasMore(true);
    fetchTickets(1);
  }, [escalationLevel, activeFilterTree, sortBy, sortOrder]);

  // Sync propFilterTree changes
  useEffect(() => {
    if (propFilterTree) {
      setActiveFilterTree(propFilterTree);
    }
  }, [propFilterTree]);

  // Re-fetch tickets when refreshKey changes (e.g., after merge)
  useEffect(() => {
    if (refreshKey !== undefined && refreshKey > 0) {
      setTickets([]);
      setPage(1);
      setHasMore(true);
      fetchTickets(1);
    }
  }, [refreshKey, escalationLevel]);

  useEffect(() => {
    if (page > 1) {
      fetchTickets(page);
    }
  }, [page]);

  // Infinite scroll observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          setPage(prev => prev + 1);
        }
      },
      { threshold: 0.1 }
    );

    const currentTarget = observerTarget.current;
    if (currentTarget) {
      observer.observe(currentTarget);
    }

    return () => {
      if (currentTarget) {
        observer.unobserve(currentTarget);
      }
    };
  }, [hasMore, loading]);

  const getUserName = (assigneeId) => {
    if (!Array.isArray(users)) return 'Unassigned';
    const user = users.find(u => u.id === assigneeId);
    return user ? user.name : 'Unassigned';
  };

  const handleFilterApply = useCallback((tree) => {
    setActiveFilterTree(tree);
    setPage(1);
    setTickets([]);
    setHasMore(true);
  }, []);

  const handleSaveInbox = useCallback(({ name, color }) => {
    if (!activeFilterTree || !onSaveInbox) return;
    onSaveInbox({ name, color, filter_tree: activeFilterTree });
  }, [activeFilterTree, onSaveInbox]);

  const handleSortChange = useCallback((field) => {
    if (field === sortBy) {
      setSortOrder(prev => prev === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
    setShowSortMenu(false);
    setPage(1);
    setTickets([]);
    setHasMore(true);
  }, [sortBy]);

  if (loading && page === 1 && !activeFilterTree) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="glass rounded-xl p-6">
          <div className="animate-pulse text-foreground">Loading tickets...</div>
        </div>
      </div>
    );
  }

  const currentSortLabel = SORT_OPTIONS.find(o => o.value === sortBy)?.label || 'Created';

  return (
    <div className="h-full flex flex-col">
      {/* Compact Header — title + controls on one line */}
      <div className="px-4 py-1.5 border-b border-border">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <h1 className="text-sm font-semibold text-foreground truncate">{title}</h1>
            <span className="text-[11px] text-muted-foreground tabular-nums shrink-0">{totalCount}</span>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            {/* Sort dropdown */}
            <div ref={sortRef} className="relative">
              <button
                onClick={() => setShowSortMenu(!showSortMenu)}
                className="flex items-center gap-1 h-7 px-2 rounded-md border border-border text-[12px] text-foreground hover:bg-muted transition-colors"
                data-testid="sort-toggle-btn"
              >
                {sortOrder === 'desc' ? <ArrowDown size={12} /> : <ArrowUp size={12} />}
                <span>{currentSortLabel}</span>
              </button>
              {showSortMenu && (
                <div className="absolute right-0 top-full mt-1 w-52 bg-background border border-border rounded-lg shadow-lg z-50 py-1" data-testid="sort-menu">
                  {SORT_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => handleSortChange(opt.value)}
                      className={`w-full flex items-center justify-between px-3 py-1.5 text-[12px] hover:bg-muted transition-colors ${
                        opt.value === sortBy ? 'text-foreground font-medium' : 'text-muted-foreground'
                      }`}
                      data-testid={`sort-option-${opt.value}`}
                    >
                      <span>{opt.label}</span>
                      {opt.value === sortBy && (
                        <div className="flex items-center gap-1">
                          {sortOrder === 'desc' ? <ArrowDown size={11} /> : <ArrowUp size={11} />}
                          <Check size={11} />
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {/* Filter builder inline */}
            {showFilterBuilder && (
              <React.Suspense fallback={null}>
                <FilterBuilder
                  onFilter={handleFilterApply}
                  onSaveInbox={onSaveInbox ? () => setShowSaveModal(true) : null}
                  initialFilters={propFilterTree}
                />
              </React.Suspense>
            )}
          </div>
        </div>
      </div>

      <React.Suspense fallback={null}>
        <SaveInboxModal
          isOpen={showSaveModal}
          onClose={() => setShowSaveModal(false)}
          onSave={handleSaveInbox}
        />
      </React.Suspense>

      {/* Tickets List */}
      <div className="flex-1 overflow-y-auto">
        {tickets.length === 0 ? (
          <div className="flex flex-col items-start justify-center h-full px-6 py-12">
            <h3 className="text-base font-medium mb-2 text-foreground">No tickets found</h3>
            <p className="text-sm text-muted-foreground">All clear in this view. New tickets will appear here.</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {tickets.map((ticket) => {
              const statusBadge = getStatusBadge(ticket.status);
              const priorityColor = getPriorityColor(ticket.priority);
              const levelBadge = ticket.escalation_level || 'L1';
              
              return (
                <button
                  key={ticket.id}
                  onClick={() => onTicketClick(ticket)}
                  className="w-full px-4 py-1.5 hover:bg-secondary/60 active:bg-secondary/80 transition-colors duration-150 text-left group"
                  data-testid={`ticket-row-${ticket.ticket_id || ticket.id}`}
                >
                  <div className="flex items-start gap-2">
                    {/* Priority Indicator */}
                    <div className={`shrink-0 w-1 self-stretch rounded-full ${priorityColor} mt-0.5 group-hover:w-1.5 transition-all duration-150`} style={{minHeight: '28px'}} />

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      {/* Row 1: Title + badges */}
                      <div className="flex items-center justify-between gap-2 mb-0">
                        <h3 className="text-[13px] font-medium text-foreground line-clamp-1">
                          {ticket.title}
                        </h3>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className={`text-[11px] font-semibold px-1.5 py-0.5 rounded border ${
                            levelBadge === 'L1' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                            levelBadge === 'L2' ? 'bg-amber-50 text-amber-800 border-amber-200' :
                            'bg-rose-50 text-rose-700 border-rose-200'
                          }`}>
                            {levelBadge}
                          </span>
                          <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${statusBadge.class}`}>
                            {statusBadge.label}
                          </span>
                        </div>
                      </div>

                      {/* Row 2: Preview + Metadata */}
                      <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                        {(ticket.description || ticket.email_preview || ticket.email_text) && (
                          <span className="line-clamp-1 flex-1 min-w-0">
                            {getPreviewText(ticket)}
                          </span>
                        )}
                        <div className="flex items-center gap-2 shrink-0">
                          <div className="flex items-center gap-1">
                            <UserIcon size={11} />
                            <span>{getUserName(ticket.assignee_id)}</span>
                          </div>
                          <span className="text-muted-foreground/50 tabular-nums" title={formatTimeAgo(ticket.created_at)}>
                            {formatRelativeAge(ticket.created_at)}
                          </span>
                          <span className="text-muted-foreground/70 font-mono text-[10px]">
                            #{ticket.ticket_id || ticket.id?.slice(-6) || 'N/A'}
                          </span>
                        </div>
                      </div>

                      {/* Row 3: Tags + Customer Email */}
                      {((ticket.tags && ticket.tags.length > 0) || ticket.customer_email) && (
                        <div className="flex items-center gap-2 mt-0.5 text-[10px]">
                          {ticket.tags && ticket.tags.length > 0 && (
                            <div className="flex items-center gap-1 min-w-0">
                              <Tag size={9} className="text-muted-foreground/50 shrink-0" />
                              {ticket.tags.slice(0, 3).map((tag, idx) => (
                                <span key={idx} className="px-1.5 py-px rounded bg-secondary text-muted-foreground font-medium truncate max-w-[80px]" data-testid={`list-tag-${tag}`}>
                                  {tag}
                                </span>
                              ))}
                              {ticket.tags.length > 3 && <span className="text-muted-foreground/40">+{ticket.tags.length - 3}</span>}
                            </div>
                          )}
                          {ticket.customer_email && (
                            <div className="flex items-center gap-1 text-muted-foreground/60 truncate ml-auto shrink-0">
                              <Mail size={9} />
                              <span className="truncate max-w-[160px]">{ticket.customer_email}</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}

            {/* Loading indicator */}
            {hasMore && (
              <div ref={observerTarget} className="flex justify-center py-6">
                <div className="text-muted-foreground text-sm">Loading more...</div>
              </div>
            )}

            {!hasMore && tickets.length > 0 && (
              <div className="text-center py-4 text-sm text-muted-foreground">
                All tickets loaded
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TicketsListView;
