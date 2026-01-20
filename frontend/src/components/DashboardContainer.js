import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import Header from './Header';
import KanbanBoard from './KanbanBoard';
import TicketDrawer from './TicketDrawer';
import CreateTicketModal from './CreateTicketModal';
import ImportModal from './ImportModal';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const DashboardContainer = ({ user }) => {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [analytics, setAnalytics] = useState(null);

  const fetchTickets = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets`, {
        credentials: 'include'
      });
      if (!response.ok) throw new Error('Failed to fetch tickets');
      const data = await response.json();
      setTickets(data);
    } catch (error) {
      toast.error(error.message);
    }
  };

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

  const handleLogout = async () => {
    try {
      await fetch(`${BACKEND_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
      navigate('/login');
    } catch (error) {
      // Navigate anyway
      navigate('/login');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="glass rounded-xl p-6">
          <div className="animate-pulse text-foreground">Loading dashboard...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="gradient-overlay" />
      <div className="content-wrapper relative z-10">
        <Header
          user={user}
          analytics={analytics}
          onLogout={handleLogout}
          onCreateTicket={() => setIsCreateModalOpen(true)}
          onExport={handleExport}
          onImport={() => setIsImportModalOpen(true)}
        />
        
        <KanbanBoard
          tickets={tickets}
          users={users}
          onTicketClick={handleTicketClick}
          onDragEnd={handleDragEnd}
          onCreateTicket={() => setIsCreateModalOpen(true)}
        />

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
    </div>
  );
};

export default DashboardContainer;
