import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { Plus, Download, Upload, AtSign, User, Bell } from 'lucide-react';
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

      if (!response.ok) throw new Error('Failed to reorder tickets');
      
      await fetchTickets();
      await fetchAnalytics();
    } catch (error) {
      toast.error(error.message);
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
            <h2 className="text-lg md:text-xl font-semibold">My Tickets</h2>
            {analytics && (
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-1 rounded-md glass" data-testid="badge-mine">
                  {analytics.my_tickets} tickets
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="h-9 px-3 flex items-center gap-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-cyan-400/90 transition-interactive"
              data-testid="create-ticket-button"
            >
              <Plus size={16} />
              <span className="hidden sm:inline">New</span>
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
          tickets={tickets}
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
