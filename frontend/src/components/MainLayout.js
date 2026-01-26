import React, { useState, useEffect, useContext, useCallback } from 'react';
import { useSearchParams, useParams, useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import GlobalHeader from './GlobalHeader';
import DashboardContainer from './DashboardContainer';
import AllTicketsPage from './AllTicketsPage';
import OpenTicketsPage from './OpenTicketsPage';
import WaitingTicketsPage from './WaitingTicketsPage';
import ClosedTicketsPage from './ClosedTicketsPage';
import StarredTicketsPage from './StarredTicketsPage';
import TicketDrawer from './TicketDrawer';
import CreateTicketModal from './CreateTicketModal';
import { CommandPaletteContext } from '../App';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const MainLayout = ({ user, view }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { ticketId: urlTicketId } = useParams(); // Get ticketId from URL path
  const navigate = useNavigate();
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [users, setUsers] = useState([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const { openCommandPalette } = useContext(CommandPaletteContext);

  // Open ticket by ID (fetch from API)
  const openTicketById = useCallback(async (ticketId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}`, {
        credentials: 'include'
      });
      if (response.ok) {
        const ticket = await response.json();
        setSelectedTicket(ticket);
        setIsDrawerOpen(true);
        // Update URL to unique ticket URL (without full page reload)
        if (window.location.pathname !== `/ticket/${ticketId}`) {
          window.history.pushState({}, '', `/ticket/${ticketId}`);
        }
      }
    } catch (error) {
      console.error('Failed to fetch ticket:', error);
    }
  }, []);

  // Handle URL path for opening a ticket (e.g., /ticket/TKT-000001)
  useEffect(() => {
    if (urlTicketId) {
      openTicketById(urlTicketId);
    }
  }, [urlTicketId, openTicketById]);

  // Handle URL query param for opening a ticket (legacy support)
  useEffect(() => {
    const ticketId = searchParams.get('ticket');
    if (ticketId) {
      openTicketById(ticketId);
      // Clear the param from URL to prevent re-opening on refresh
      // (optional - comment out if you want ticket links to be shareable)
    }
  }, [searchParams, openTicketById]);

  // Listen for open ticket events from search
  useEffect(() => {
    const handleOpenTicket = (e) => {
      const { ticketId } = e.detail || {};
      if (ticketId) {
        openTicketById(ticketId);
      }
    };
    window.addEventListener('trinity:open-ticket', handleOpenTicket);
    return () => window.removeEventListener('trinity:open-ticket', handleOpenTicket);
  }, [openTicketById]);

  // Listen for create ticket events from GlobalHeader/CommandPalette
  useEffect(() => {
    const handleCreateTicket = () => setIsCreateModalOpen(true);
    window.addEventListener('trinity:create-ticket', handleCreateTicket);
    return () => window.removeEventListener('trinity:create-ticket', handleCreateTicket);
  }, []);

  // Fetch users on mount
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/users`, {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          setUsers(data);
        }
      } catch (error) {
        console.error('Failed to fetch users:', error);
      }
    };
    fetchUsers();
  }, []);

  const handleTicketClick = (ticket) => {
    setSelectedTicket(ticket);
    setIsDrawerOpen(true);
    // Update URL to unique ticket URL
    window.history.pushState({}, '', `/ticket/${ticket.ticket_id}`);
  };

  const handleCloseDrawer = () => {
    setIsDrawerOpen(false);
    setSelectedTicket(null);
    // Navigate back to the appropriate view when closing
    if (view === 'ticket' || window.location.pathname.startsWith('/ticket/')) {
      // Navigate to all-tickets when closing from unique ticket URL
      navigate('/all-tickets');
    } else {
      // Just update URL back to current view
      window.history.pushState({}, '', `/${view === 'dashboard' ? 'dashboard' : view}`);
    }
  };

  const handleUpdateTicket = async (ticketId, updatedData) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(updatedData)
      });
      
      if (!response.ok) throw new Error('Failed to update ticket');
      
      const updated = await response.json();
      setSelectedTicket(updated);
      setRefreshKey(prev => prev + 1); // Trigger list refresh
      // Success
    } catch (error) {
      // Error
    }
  };

  const handleDeleteTicket = async (ticketId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (!response.ok) throw new Error('Failed to delete ticket');
      
      handleCloseDrawer();
      setRefreshKey(prev => prev + 1); // Trigger list refresh
      // Success
    } catch (error) {
      // Error
    }
  };

  return (
    <div className="min-h-screen flex bg-background overflow-hidden">
      <div className="gradient-overlay" />
      
      <Sidebar user={user} />
      
      <div className="flex-1 flex flex-col relative z-10 min-w-0">
        <GlobalHeader 
          user={user} 
          onCreateTicket={() => setIsCreateModalOpen(true)}
          onOpenCommandPalette={openCommandPalette}
        />
        
        <main className="flex-1 overflow-auto">
          {view === 'dashboard' && (
            <DashboardContainer 
              user={user} 
              onTicketClickFromExternal={handleTicketClick}
            />
          )}
          {view === 'all-tickets' && (
            <AllTicketsPage 
              key={refreshKey}
              user={user} 
              onTicketClick={handleTicketClick}
            />
          )}
          {view === 'open-tickets' && (
            <OpenTicketsPage 
              key={refreshKey}
              user={user} 
              onTicketClick={handleTicketClick}
            />
          )}
          {view === 'waiting-tickets' && (
            <WaitingTicketsPage 
              key={refreshKey}
              user={user} 
              onTicketClick={handleTicketClick}
            />
          )}
          {view === 'closed-tickets' && (
            <ClosedTicketsPage 
              key={refreshKey}
              user={user} 
              onTicketClick={handleTicketClick}
            />
          )}
          {view === 'starred-tickets' && (
            <StarredTicketsPage 
              key={refreshKey}
              user={user} 
              onTicketClick={handleTicketClick}
            />
          )}
        </main>
      </div>

      {/* Shared Ticket Drawer */}
      {(view !== 'dashboard') && (
        <TicketDrawer
          ticket={selectedTicket}
          users={users}
          currentUser={user}
          isOpen={isDrawerOpen}
          onClose={handleCloseDrawer}
          onUpdate={handleUpdateTicket}
          onDelete={handleDeleteTicket}
        />
      )}

      {/* Create Ticket Modal */}
      <CreateTicketModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreated={() => {
          setRefreshKey(prev => prev + 1);
          setIsCreateModalOpen(false);
        }}
      />
    </div>
  );
};

export default MainLayout;
