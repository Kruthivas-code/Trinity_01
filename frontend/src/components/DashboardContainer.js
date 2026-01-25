import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { Download, Upload, AtSign, User, RefreshCw, Filter } from 'lucide-react';
import KanbanBoard from './KanbanBoard';
import TicketDrawer from './TicketDrawer';
import CreateTicketModal from './CreateTicketModal';
import ImportModal from './ImportModal';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const DashboardContainer = ({ user, onTicketClickFromExternal }) => {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [mentionedTickets, setMentionedTickets] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [viewMode, setViewMode] = useState('assigned'); // 'assigned' | 'mentioned' | 'all'
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [priorityFilter, setPriorityFilter] = useState('all'); // 'all' | 'urgent' | 'high' | 'medium' | 'low'

  const fetchTickets = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to fetch tickets');
      const data = await response.json();
      
      // Filter to show only tickets assigned to current user
      const myTickets = data.filter(t => t.assignee_id === user?.user_id || t.assignee_id === user?.id);
      setTickets(myTickets);
      
      // Also get mentioned tickets
      const mentioned = data.filter(t => 
        t.mentioned_users?.includes(user?.user_id) || 
        t.mentioned_users?.includes(user?.id)
      );
      setMentionedTickets(mentioned);
    } catch (error) {
      toast.error(error.message);
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
      toast.error(error.message);
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

  const handleTicketClick = (ticket) => {
    setSelectedTicket(ticket);
    setIsDrawerOpen(true);
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
      
      toast.success('Ticket created successfully');
      await fetchTickets();
      await fetchAnalytics();
      setIsCreateModalOpen(false);
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleUpdateTicket = async (ticketId, updates) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(updates)
      });

      if (!response.ok) throw new Error('Failed to update ticket');
      
      toast.success('Ticket updated successfully');
      await fetchTickets();
      await fetchAnalytics();
      setIsDrawerOpen(false);
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleDeleteTicket = async (ticketId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to delete ticket');
      
      toast.success('Ticket deleted successfully');
      await fetchTickets();
      await fetchAnalytics();
      setIsDrawerOpen(false);
    } catch (error) {
      toast.error(error.message);
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
    
    // Also update mentioned tickets if needed
    setMentionedTickets(prevTickets => {
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
      toast.error(error.message);
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
      
      toast.success(`Tickets exported as ${format.toUpperCase()}`);
    } catch (error) {
      toast.error(error.message);
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
      
      const data = await response.json();
      toast.success(data.message);
      await fetchTickets();
      await fetchAnalytics();
      setIsImportModalOpen(false);
    } catch (error) {
      toast.error(error.message);
    }
  };

  // Get tickets to display based on viewMode and priority filter
  const getFilteredTickets = () => {
    let baseTickets = viewMode === 'mentioned' ? mentionedTickets : 
                      viewMode === 'all' ? [...tickets, ...mentionedTickets.filter(t => !tickets.find(mt => mt.id === t.id))] :
                      tickets;
    
    // Apply priority filter
    if (priorityFilter !== 'all') {
      baseTickets = baseTickets.filter(t => t.priority === priorityFilter);
    }
    
    return baseTickets;
  };
  
  const displayTickets = getFilteredTickets();

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
          </div>

          <div className="flex items-center gap-2">
            {/* Priority Filter */}
            <div className="relative">
              <button
                onClick={() => setShowFilterMenu(!showFilterMenu)}
                className={`h-9 px-3 flex items-center gap-2 rounded-lg text-sm border transition-interactive ${
                  priorityFilter !== 'all' 
                    ? 'bg-primary/20 text-primary border-primary/30' 
                    : 'bg-secondary/70 text-secondary-foreground border-white/10 hover:bg-secondary/90'
                }`}
                data-testid="filter-button"
              >
                <Filter size={16} />
                <span className="hidden sm:inline">
                  {priorityFilter === 'all' ? 'Filter' : priorityFilter.charAt(0).toUpperCase() + priorityFilter.slice(1)}
                </span>
              </button>

              {showFilterMenu && (
                <div className="absolute right-0 top-12 glass rounded-lg border border-border/60 p-2 min-w-[140px] z-50">
                  <div className="text-[10px] text-muted-foreground uppercase font-medium px-3 py-1">Priority</div>
                  {['all', 'urgent', 'high', 'medium', 'low'].map(priority => (
                    <button
                      key={priority}
                      onClick={() => {
                        setPriorityFilter(priority);
                        setShowFilterMenu(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-sm rounded transition-colors flex items-center gap-2 ${
                        priorityFilter === priority ? 'bg-primary/20 text-primary' : 'hover:bg-white/5'
                      }`}
                      data-testid={`filter-${priority}`}
                    >
                      {priority === 'urgent' && <span className="w-2 h-2 rounded-full bg-red-400" />}
                      {priority === 'high' && <span className="w-2 h-2 rounded-full bg-orange-400" />}
                      {priority === 'medium' && <span className="w-2 h-2 rounded-full bg-amber-400" />}
                      {priority === 'low' && <span className="w-2 h-2 rounded-full bg-slate-400" />}
                      {priority === 'all' ? 'All Priorities' : priority.charAt(0).toUpperCase() + priority.slice(1)}
                    </button>
                  ))}
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
                toast.success('Dashboard refreshed');
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
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
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
