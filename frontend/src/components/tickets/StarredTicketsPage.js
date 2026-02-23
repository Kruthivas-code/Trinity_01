import React, { useState, useEffect, useRef } from 'react';
import { Star, Clock, User as UserIcon } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const ITEMS_PER_PAGE = 50;

// Strip HTML tags and CSS for display
const stripHtml = (html) => {
  if (!html) return '';
  let text = html.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
  text = text.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
  text = text.replace(/<[^>]*>/g, ' ');
  text = text.replace(/[\w-]+\s*:\s*[^;]+;/g, ' ');
  text = text.replace(/&nbsp;/g, ' ')
             .replace(/&amp;/g, '&')
             .replace(/&lt;/g, '<')
             .replace(/&gt;/g, '>')
             .replace(/&quot;/g, '"')
             .replace(/&#39;/g, "'")
             .replace(/&#\d+;/g, ' ');
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
    todo: { label: 'To Do', class: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
    in_progress: { label: 'In Progress', class: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
    waiting: { label: 'Waiting', class: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
    review: { label: 'Review', class: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
    resolved: { label: 'Resolved', class: 'bg-green-500/20 text-green-400 border-green-500/30' },
    closed: { label: 'Closed', class: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
  };
  return badges[status] || { label: status, class: 'bg-gray-500/20 text-gray-400 border-gray-500/30' };
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

const StarredTicketsPage = ({ user, onTicketClick, refreshKey }) => {
  const [tickets, setTickets] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const observerTarget = useRef(null);

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

  const fetchStarredTickets = async (pageNum) => {
    try {
      setLoading(true);
      const response = await fetch(`${BACKEND_URL}/api/tickets/starred`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to fetch starred tickets');
      const data = await response.json();
      
      // Sort by updated_at (most recent first)
      const sortedTickets = data.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
      
      // Simulate pagination
      const startIdx = (pageNum - 1) * ITEMS_PER_PAGE;
      const endIdx = startIdx + ITEMS_PER_PAGE;
      const paginatedTickets = sortedTickets.slice(startIdx, endIdx);
      
      if (pageNum === 1) {
        setTickets(paginatedTickets);
      } else {
        setTickets(prev => [...prev, ...paginatedTickets]);
      }
      
      setHasMore(endIdx < sortedTickets.length);
    } catch (error) {
      console.error('Failed to fetch starred tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchStarredTickets(1);
  }, []);

  // Re-fetch when refreshKey changes (e.g., after merge)
  useEffect(() => {
    if (refreshKey !== undefined && refreshKey > 0) {
      setTickets([]);
      setPage(1);
      setHasMore(true);
      fetchStarredTickets(1);
    }
  }, [refreshKey]);

  useEffect(() => {
    if (page > 1) {
      fetchStarredTickets(page);
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
    const foundUser = users.find(u => u.id === assigneeId || u.user_id === assigneeId);
    return foundUser ? foundUser.name : 'Unassigned';
  };

  if (loading && page === 1) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="glass rounded-xl p-6">
          <div className="animate-pulse text-foreground">Loading starred tickets...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col" data-testid="starred-tickets-page">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border/40">
        <div className="flex items-center gap-2 mb-1">
          <Star size={24} className="text-amber-500 fill-amber-500" />
          <h1 className="text-2xl font-semibold">Starred Tickets</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Your saved tickets for quick access • {tickets.length} ticket{tickets.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Tickets List */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {tickets.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="glass rounded-xl p-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-500/10 flex items-center justify-center">
                <Star size={32} className="text-amber-500" />
              </div>
              <h3 className="text-lg font-medium mb-2">No starred tickets</h3>
              <p className="text-sm text-muted-foreground max-w-sm">
                Star tickets you want to follow up on or save for later. They'll appear here regardless of their status.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {tickets.map((ticket) => {
              const statusBadge = getStatusBadge(ticket.status);
              const priorityColor = getPriorityColor(ticket.priority);
              
              return (
                <button
                  key={ticket.id || ticket.ticket_id}
                  onClick={() => onTicketClick(ticket)}
                  className="w-full glass rounded-lg p-4 border border-border/40 hover:border-border/60 transition-interactive text-left group"
                  data-testid="starred-ticket-item"
                >
                  <div className="flex items-start gap-4">
                    {/* Priority Indicator */}
                    <div className={`shrink-0 w-1 h-16 rounded-full ${priorityColor}`} />

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      {/* Title and Status */}
                      <div className="flex items-start justify-between gap-4 mb-2">
                        <div className="flex items-center gap-2">
                          <Star size={14} className="text-amber-500 fill-amber-500 shrink-0" />
                          <h3 className="font-medium text-foreground group-hover:text-primary transition-colors line-clamp-1">
                            {ticket.title}
                          </h3>
                        </div>
                        <span className={`shrink-0 text-xs px-2 py-1 rounded-md border ${statusBadge.class}`}>
                          {statusBadge.label}
                        </span>
                      </div>

                      {/* Description */}
                      {ticket.description && (
                        <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
                          {stripHtml(ticket.description)}
                        </p>
                      )}

                      {/* Metadata */}
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <UserIcon size={14} />
                          <span>{getUserName(ticket.assignee_id)}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Clock size={14} />
                          <span>{formatTimeAgo(ticket.updated_at || ticket.created_at)}</span>
                        </div>
                        <div className="text-muted-foreground/60">
                          #{ticket.ticket_id || ticket.id?.slice(-6) || 'N/A'}
                        </div>
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}

            {/* Loading indicator for infinite scroll */}
            {hasMore && (
              <div ref={observerTarget} className="flex justify-center py-4">
                <div className="animate-pulse text-muted-foreground text-sm">Loading more...</div>
              </div>
            )}

            {!hasMore && tickets.length > 0 && (
              <div className="text-center py-4 text-sm text-muted-foreground">
                All starred tickets loaded
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default StarredTicketsPage;
