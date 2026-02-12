import React, { useState, useEffect } from 'react';

import Header from '../layout/Header';
import KanbanBoard from '../tickets/KanbanBoard';
import TicketDrawer from '../tickets/TicketDrawer';
import CreateTicketModal from '../tickets/CreateTicketModal';
import ImportModal from '../common/ImportModal';
import { useRealtime } from '../contexts/RealtimeContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const Dashboard = ({ user, token, onLogout }) => {
  const [tickets, setTickets] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  
  const { onTicketUpdate } = useRealtime();

  // Subscribe to real-time ticket updates
  useEffect(() => {
    const unsubscribe = onTicketUpdate((data) => {
      if (data.ticket) {
        // New ticket created - add to list
        setTickets(prev => {
          const exists = prev.some(t => t.ticket_id === data.ticket.ticket_id);
          if (!exists) {
            return [data.ticket, ...prev];
          }
          // Update existing ticket
          return prev.map(t => t.ticket_id === data.ticket.ticket_id ? { ...t, ...data.ticket } : t);
        });
      } else if (data.ticket_id && data.deleted) {
        // Ticket deleted - remove from list
        setTickets(prev => prev.filter(t => t.ticket_id !== data.ticket_id));
      }
    });
    
    return unsubscribe;
  }, [onTicketUpdate]);

  const fetchTickets = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Failed to fetch tickets');
      const data = await response.json();
      setTickets(data.tickets || data);
    } catch (error) {
      console.error('Operation failed');
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/users`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Failed to fetch users');
      const data = await response.json();
      setUsers(data);
    } catch (error) {
      console.error('Operation failed');
    }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/analytics/summary`, {
        headers: { 'Authorization': `Bearer ${token}` }
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
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(ticketData)
      });

      if (!response.ok) throw new Error('Failed to create ticket');
      
      // Success
      await fetchTickets();
      await fetchAnalytics();
      setIsCreateModalOpen(false);
    } catch (error) {
      console.error('Operation failed');
    }
  };

  const handleUpdateTicket = async (ticketId, updates) => {
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
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updates)
      });

      if (!response.ok) throw new Error('Failed to update ticket');
      
      // Success
      await fetchTickets();
      await fetchAnalytics();
      setIsDrawerOpen(false);
    } catch (error) {
      console.error('Operation failed');
    }
  };

  const handleDeleteTicket = async (ticketId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) throw new Error('Failed to delete ticket');
      
      // Success
      await fetchTickets();
      await fetchAnalytics();
      setIsDrawerOpen(false);
    } catch (error) {
      console.error('Operation failed');
    }
  };

  const handleDragEnd = async (ticketId, newStatus, newOrder) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/reorder`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
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
      console.error('Operation failed');
      await fetchTickets(); // Refresh to revert optimistic update
    }
  };

  const handleExport = async (format) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/export?format=${format}`, {
        headers: { 'Authorization': `Bearer ${token}` }
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
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to import tickets');
      }
      
      const data = await response.json();
      // Success
      await fetchTickets();
      await fetchAnalytics();
      setIsImportModalOpen(false);
    } catch (error) {
      console.error('Operation failed');
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
          onLogout={onLogout}
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

export default Dashboard;
