import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Download, Upload, AtSign, User, RefreshCw, Filter, Calendar, Tag, X } from 'lucide-react';
import KanbanBoard from './KanbanBoard';
import TicketDrawer from './TicketDrawer';
import CreateTicketModal from './CreateTicketModal';
import ImportModal from './ImportModal';
import { useRealtime } from '../contexts/RealtimeContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const DashboardContainer = ({ user, onTicketClickFromExternal }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [tickets, setTickets] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  
  const { onTicketUpdate } = useRealtime();
  
  // Enhanced filters
  const [filters, setFilters] = useState({
    priority: 'all',
    status: 'all',
    tag: '',
    dateRange: 'all', // 'all' | 'today' | 'week' | 'month'
    search: '' // Search by ticket_id or uuid
  });
  
  // Available tags from tickets
  const [availableTags, setAvailableTags] = useState([]);

  // Subscribe to real-time ticket updates
  useEffect(() => {
    const unsubscribe = onTicketUpdate((data) => {
      if (data.ticket) {
        const ticket = data.ticket;
        setTickets(prev => {
          const existingIndex = prev.findIndex(t => t.ticket_id === ticket.ticket_id);
          if (existingIndex >= 0) {
            // Update existing ticket
            const updated = [...prev];
            updated[existingIndex] = { ...updated[existingIndex], ...ticket };
            return updated;
          } else {
            // New ticket - add to list
            return [ticket, ...prev];
          }
        });
      } else if (data.ticket_id && data.deleted) {
        // Ticket deleted - remove from list
        setTickets(prev => prev.filter(t => t.ticket_id !== data.ticket_id));
      }
    });
    
    return unsubscribe;
  }, [onTicketUpdate]);

  const fetchTickets = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to fetch tickets');
      const data = await response.json();
      
      // Collect all unique tags
      const tags = new Set();
      data.forEach(t => (t.tags || []).forEach(tag => tags.add(tag)));
      setAvailableTags(Array.from(tags).sort());
      
      // Filter to show tickets assigned to current user OR where user is mentioned
      // This combines both views into one unified kanban
      const userId = user?.user_id || user?.id;
      const myTickets = data.filter(t => 
        t.assignee_id === userId || 
        (Array.isArray(t.mentioned_users) && t.mentioned_users.includes(userId))
      );
      setTickets(myTickets);
    } catch (error) {
      console.error('Failed to fetch tickets:', error);
    }
  }, [user]);

  const fetchUsers = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/users`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to fetch users');
      const data = await response.json();
      setUsers(data);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/analytics/summary`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to fetch analytics');
      const data = await response.json();
      setAnalytics(data);
    } catch (error) {
      console.error('Analytics fetch error:', error);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchTickets(), fetchUsers(), fetchAnalytics()]);
      setLoading(false);
    };
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle opening ticket from URL query param
  useEffect(() => {
    const ticketId = searchParams.get('ticket');
    if (ticketId && tickets.length > 0) {
      // Find ticket in loaded tickets or fetch it
      const ticket = tickets.find(t => t.ticket_id === ticketId || t.id === ticketId);
      if (ticket) {
        setSelectedTicket(ticket);
        setIsDrawerOpen(true);
      } else {
        // Ticket not in current view, fetch it directly
        const fetchTicket = async () => {
          try {
            const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}`, {
              credentials: 'include'
            });
            if (response.ok) {
              const data = await response.json();
              setSelectedTicket(data);
              setIsDrawerOpen(true);
            }
          } catch (error) {
            console.error('Failed to fetch ticket from URL:', error);
          }
        };
        fetchTicket();
      }
    }
  }, [searchParams, tickets]);

  const handleTicketClick = (ticket) => {
    setSelectedTicket(ticket);
    setIsDrawerOpen(true);
    // Update URL with query param to maintain dashboard context
    window.history.pushState({}, '', `/dashboard?ticket=${ticket.ticket_id}`);
  };

  const handleCreateTicket = async (ticketData) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(ticketData)
      });

      if (!response.ok) throw new Error('Failed to create ticket');
      
      await fetchTickets();
      await fetchAnalytics();
      setIsCreateModalOpen(false);
    } catch (error) {
      console.error('Failed to create ticket:', error);
    }
  };

  const handleUpdateTicket = async (ticketId, updates, closeDrawer = false) => {
    try {
      // Handle merge completion - just refresh without making an update API call
      if (updates._merged) {
        await fetchTickets();
        await fetchAnalytics();
        setIsDrawerOpen(false);
        return;
      }
      
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(updates)
      });

      if (!response.ok) throw new Error('Failed to update ticket');
      
      const updatedTicket = await response.json();
      
      // Update the selected ticket with new data (keep drawer open)
      if (selectedTicket && selectedTicket.id === ticketId) {
        setSelectedTicket(updatedTicket);
      }
      
      await fetchTickets();
      await fetchAnalytics();
      
      // Only close drawer if explicitly requested
      if (closeDrawer) {
        setIsDrawerOpen(false);
      }
    } catch (error) {
      console.error('Failed to update ticket:', error);
    }
  };

  const handleDeleteTicket = async (ticketId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to delete ticket');
      
      await fetchTickets();
      await fetchAnalytics();
      setIsDrawerOpen(false);
    } catch (error) {
      console.error('Failed to delete ticket:', error);
    }
  };

  const handleDragEnd = async (ticketId, newStatus, newOrder) => {
    // Optimistic update - immediately update local state
    setTickets(prevTickets => {
      return prevTickets.map(ticket => {
        if (ticket.id === ticketId) {
          return { ...ticket, status: newStatus, order: newOrder };
        }
        return ticket;
      });
    });

    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/reorder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          ticket_id: ticketId,
          new_status: newStatus,
          new_order: newOrder
        })
      });

      if (!response.ok) {
        throw new Error('Failed to reorder tickets');
      }
      
      // Silently sync with backend (no visual change expected)
      await fetchAnalytics();
    } catch (error) {
      console.error('Failed to reorder:', error);
      // Revert on error - refetch the actual state
      await fetchTickets();
    }
  };

  const handleExport = async (format) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/export?format=${format}`, {
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to export tickets');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tickets.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  const handleImport = async (file) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${BACKEND_URL}/api/import`, {
        method: 'POST',
        credentials: 'include',
        body: formData
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to import tickets');
      }
      
      await fetchTickets();
      await fetchAnalytics();
      setIsImportModalOpen(false);
    } catch (error) {
      console.error('Import failed:', error);
    }
  };
  
  // Check if ticket matches date filter
  const matchesDateFilter = (ticket) => {
    if (filters.dateRange === 'all') return true;
    const createdAt = new Date(ticket.created_at);
    const now = new Date();
    
    switch (filters.dateRange) {
      case 'today':
        return createdAt.toDateString() === now.toDateString();
      case 'week':
        const weekAgo = new Date(now);
        weekAgo.setDate(weekAgo.getDate() - 7);
        return createdAt >= weekAgo;
      case 'month':
        const monthAgo = new Date(now);
        monthAgo.setMonth(monthAgo.getMonth() - 1);
        return createdAt >= monthAgo;
      default:
        return true;
    }
  };

  // Get tickets to display based on all filters
  const getFilteredTickets = () => {
    let baseTickets = tickets;
    
    // Apply priority filter
    if (filters.priority !== 'all') {
      baseTickets = baseTickets.filter(t => t.priority === filters.priority);
    }
    
    // Apply status filter
    if (filters.status !== 'all') {
      baseTickets = baseTickets.filter(t => t.status === filters.status);
    }
    
    // Apply tag filter
    if (filters.tag) {
      baseTickets = baseTickets.filter(t => (t.tags || []).includes(filters.tag));
    }
    
    // Apply date filter
    baseTickets = baseTickets.filter(matchesDateFilter);
    
    // Apply search (ticket_id or uuid)
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      baseTickets = baseTickets.filter(t => 
        (t.ticket_id && t.ticket_id.toLowerCase().includes(searchLower)) ||
        (t.uuid && t.uuid.toLowerCase().includes(searchLower))
      );
    }
    
    return baseTickets;
  };
  
  const displayTickets = getFilteredTickets();
  
  // Count mentioned tickets for display
  const userId = user?.user_id || user?.id;
  const mentionedCount = tickets.filter(t => 
    Array.isArray(t.mentioned_users) && 
    t.mentioned_users.includes(userId) &&
    t.assignee_id !== userId  // Only count mentions on tickets NOT assigned to user
  ).length;
  
  // Count active filters
  const activeFilterCount = [
    filters.priority !== 'all',
    filters.status !== 'all',
    filters.tag !== '',
    filters.dateRange !== 'all',
    filters.search !== ''
  ].filter(Boolean).length;
  
  const clearFilters = () => {
    setFilters({
      priority: 'all',
      status: 'all',
      tag: '',
      dateRange: 'all',
      search: ''
    });
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="glass rounded-xl p-6">
          <div className="animate-pulse text-foreground">Loading dashboard...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Mini Header for Dashboard */}
      <div className="sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150">
        <div className="px-4 md:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* View Mode Toggle */}
            <div className="flex items-center bg-secondary/50 rounded-lg p-1">
              <button
                onClick={() => setViewMode('assigned')}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  viewMode === 'assigned' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
                data-testid="view-assigned"
              >
                <User size={14} />
                <span className="hidden sm:inline">My Tickets</span>
                <span className="sm:hidden">Mine</span>
                {tickets.length > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-primary/20 text-primary">
                    {tickets.length}
                  </span>
                )}
              </button>
              <button
                onClick={() => setViewMode('mentioned')}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  viewMode === 'mentioned' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
                }`}
                data-testid="view-mentioned"
              >
                <AtSign size={14} />
                <span className="hidden sm:inline">Mentioned</span>
                <span className="sm:hidden">@</span>
                {mentionedTickets.length > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-amber-500/20 text-amber-400">
                    {mentionedTickets.length}
                  </span>
                )}
              </button>
            </div>
            
            {/* Search by Ticket ID / UUID */}
            <div className="hidden md:flex items-center">
              <input
                type="text"
                placeholder="Search by Ticket ID or UUID..."
                value={filters.search}
                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                className="h-9 px-3 w-56 rounded-lg bg-secondary/70 text-sm border border-white/10 placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                data-testid="search-ticket-id"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Active Filter Count Badge */}
            {activeFilterCount > 0 && (
              <button
                onClick={clearFilters}
                className="h-9 px-3 flex items-center gap-2 rounded-lg text-sm bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-interactive"
                data-testid="clear-filters"
              >
                <X size={14} />
                <span>{activeFilterCount} filter{activeFilterCount > 1 ? 's' : ''}</span>
              </button>
            )}
            
            {/* Filters Dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowFilterMenu(!showFilterMenu)}
                className={`h-9 px-3 flex items-center gap-2 rounded-lg text-sm border transition-interactive ${
                  activeFilterCount > 0 
                    ? 'bg-primary/20 text-primary border-primary/30' 
                    : 'bg-secondary/70 text-secondary-foreground border-white/10 hover:bg-secondary/90'
                }`}
                data-testid="filter-button"
              >
                <Filter size={16} />
                <span className="hidden sm:inline">Filter</span>
              </button>

              {showFilterMenu && (
                <div className="absolute right-0 top-12 glass rounded-lg border border-border/60 p-3 w-72 z-50 space-y-4">
                  {/* Priority Filter */}
                  <div>
                    <div className="text-[10px] text-muted-foreground uppercase font-medium mb-2">Priority</div>
                    <div className="flex flex-wrap gap-1">
                      {['all', 'urgent', 'high', 'medium', 'low'].map(priority => (
                        <button
                          key={priority}
                          onClick={() => setFilters(prev => ({ ...prev, priority }))}
                          className={`px-2 py-1 text-xs rounded flex items-center gap-1 transition-colors ${
                            filters.priority === priority ? 'bg-primary/20 text-primary' : 'hover:bg-white/5'
                          }`}
                          data-testid={`filter-priority-${priority}`}
                        >
                          {priority === 'urgent' && <span className="w-1.5 h-1.5 rounded-full bg-red-400" />}
                          {priority === 'high' && <span className="w-1.5 h-1.5 rounded-full bg-orange-400" />}
                          {priority === 'medium' && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />}
                          {priority === 'low' && <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />}
                          {priority === 'all' ? 'All' : priority.charAt(0).toUpperCase() + priority.slice(1)}
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  {/* Status Filter */}
                  <div>
                    <div className="text-[10px] text-muted-foreground uppercase font-medium mb-2">Status</div>
                    <div className="flex flex-wrap gap-1">
                      {['all', 'todo', 'in_progress', 'waiting_on_customer', 'review', 'resolved'].map(status => (
                        <button
                          key={status}
                          onClick={() => setFilters(prev => ({ ...prev, status }))}
                          className={`px-2 py-1 text-xs rounded transition-colors ${
                            filters.status === status ? 'bg-primary/20 text-primary' : 'hover:bg-white/5'
                          }`}
                          data-testid={`filter-status-${status}`}
                        >
                          {status === 'all' ? 'All' : 
                           status === 'todo' ? 'To Do' :
                           status === 'in_progress' ? 'In Progress' :
                           status === 'waiting_on_customer' ? 'Waiting' :
                           status === 'review' ? 'Review' : 'Resolved'}
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  {/* Date Range Filter */}
                  <div>
                    <div className="text-[10px] text-muted-foreground uppercase font-medium mb-2 flex items-center gap-1">
                      <Calendar size={12} />
                      Created Date
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {['all', 'today', 'week', 'month'].map(range => (
                        <button
                          key={range}
                          onClick={() => setFilters(prev => ({ ...prev, dateRange: range }))}
                          className={`px-2 py-1 text-xs rounded transition-colors ${
                            filters.dateRange === range ? 'bg-primary/20 text-primary' : 'hover:bg-white/5'
                          }`}
                          data-testid={`filter-date-${range}`}
                        >
                          {range === 'all' ? 'All Time' : 
                           range === 'today' ? 'Today' :
                           range === 'week' ? 'This Week' : 'This Month'}
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  {/* Tag Filter */}
                  {availableTags.length > 0 && (
                    <div>
                      <div className="text-[10px] text-muted-foreground uppercase font-medium mb-2 flex items-center gap-1">
                        <Tag size={12} />
                        Tags
                      </div>
                      <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                        <button
                          onClick={() => setFilters(prev => ({ ...prev, tag: '' }))}
                          className={`px-2 py-1 text-xs rounded transition-colors ${
                            filters.tag === '' ? 'bg-primary/20 text-primary' : 'hover:bg-white/5'
                          }`}
                        >
                          All
                        </button>
                        {availableTags.map(tag => (
                          <button
                            key={tag}
                            onClick={() => setFilters(prev => ({ ...prev, tag }))}
                            className={`px-2 py-1 text-xs rounded transition-colors ${
                              filters.tag === tag ? 'bg-primary/20 text-primary' : 'hover:bg-white/5'
                            }`}
                            data-testid={`filter-tag-${tag}`}
                          >
                            #{tag}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Close button */}
                  <button
                    onClick={() => setShowFilterMenu(false)}
                    className="w-full mt-2 px-3 py-2 text-sm bg-secondary/50 rounded hover:bg-secondary/70 transition-colors"
                  >
                    Close
                  </button>
                </div>
              )}
            </div>

            {/* Refresh Button */}
            <button
              onClick={async () => {
                setIsRefreshing(true);
                await fetchTickets();
                await fetchAnalytics();
                setIsRefreshing(false);
              }}
              disabled={isRefreshing}
              className="h-9 px-3 flex items-center gap-2 rounded-lg bg-secondary/70 text-secondary-foreground text-sm border border-white/10 hover:bg-secondary/90 transition-interactive disabled:opacity-50"
              data-testid="refresh-button"
            >
              <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
            </button>

            <button
              onClick={() => setIsImportModalOpen(true)}
              className="h-9 px-3 flex items-center gap-2 rounded-lg bg-secondary/70 text-secondary-foreground text-sm border border-white/10 hover:bg-secondary/90 transition-interactive"
              data-testid="import-button"
            >
              <Upload size={16} />
            </button>

            <div className="relative">
              <button
                onClick={() => setShowExportMenu(!showExportMenu)}
                className="h-9 px-3 flex items-center gap-2 rounded-lg bg-secondary/70 text-secondary-foreground text-sm border border-white/10 hover:bg-secondary/90 transition-interactive"
                data-testid="export-button"
              >
                <Download size={16} />
              </button>

              {showExportMenu && (
                <div className="absolute right-0 top-12 glass rounded-lg border border-border/60 p-2 min-w-[120px] z-50">
                  <button
                    onClick={() => {
                      handleExport('json');
                      setShowExportMenu(false);
                    }}
                    className="w-full text-left px-3 py-2 text-sm rounded hover:bg-white/5 transition-interactive"
                    data-testid="export-json-button"
                  >
                    Export JSON
                  </button>
                  <button
                    onClick={() => {
                      handleExport('csv');
                      setShowExportMenu(false);
                    }}
                    className="w-full text-left px-3 py-2 text-sm rounded hover:bg-white/5 transition-interactive"
                    data-testid="export-csv-button"
                  >
                    Export CSV
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-hidden">
        <KanbanBoard
          tickets={displayTickets}
          users={users}
          onTicketClick={handleTicketClick}
          onDragEnd={handleDragEnd}
          onCreateTicket={() => setIsCreateModalOpen(true)}
        />
      </div>

      <TicketDrawer
        ticket={selectedTicket}
        users={users}
        currentUser={user}
        isOpen={isDrawerOpen}
        onClose={() => {
          setIsDrawerOpen(false);
          setSelectedTicket(null);
          // Reset URL to dashboard without ticket param
          window.history.pushState({}, '', '/dashboard');
        }}
        onUpdate={handleUpdateTicket}
        onDelete={handleDeleteTicket}
      />

      <CreateTicketModal
        isOpen={isCreateModalOpen}
        users={users}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreateTicket}
      />

      <ImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onImport={handleImport}
      />
    </div>
  );
};

export default DashboardContainer;
