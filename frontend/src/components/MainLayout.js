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
import CustomInboxPage from './CustomInboxPage';
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

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      const activeElement = document.activeElement;
      const isTyping = activeElement?.isContentEditable || 
                       activeElement?.tagName === 'INPUT' || 
                       activeElement?.tagName === 'TEXTAREA' ||
                       activeElement?.tagName === 'SELECT';
      
      // Escape - close create modal
      if (e.key === 'Escape' && isCreateModalOpen) {
        e.preventDefault();
        setIsCreateModalOpen(false);
        return;
      }
      
      // Only if not typing and drawer is not open
      if (!isTyping && !isDrawerOpen) {
        // Cmd/Ctrl + K for command palette
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
          e.preventDefault();
          openCommandPalette();
          return;
        }
        
        // N for new ticket
        if (e.key === 'n' || e.key === 'N') {
          e.preventDefault();
          setIsCreateModalOpen(true);
          return;
        }
        
        // / for search (opens command palette)
        if (e.key === '/') {
          e.preventDefault();
          openCommandPalette();
          return;
        }
        
        // G + key for go to navigation
        // We'll use simple shortcuts instead
        // 1 for Dashboard, 2 for All Tickets, etc.
        if (e.key === '1') {
          e.preventDefault();
          navigate('/dashboard');
        }
        if (e.key === '2') {
          e.preventDefault();
          navigate('/all-tickets');
        }
        if (e.key === '3') {
          e.preventDefault();
          navigate('/starred-tickets');
        }
        if (e.key === '4') {
          e.preventDefault();
          navigate('/open-tickets');
        }
        if (e.key === '5') {
          e.preventDefault();
          navigate('/closed-tickets');
        }
      }
      
      // Cmd/Ctrl + N for new ticket (works from anywhere except drawer)
      if ((e.metaKey || e.ctrlKey) && (e.key === 'n' || e.key === 'N') && !isDrawerOpen) {
        e.preventDefault();
        setIsCreateModalOpen(true);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isDrawerOpen, isCreateModalOpen, openCommandPalette, navigate]);

  const handleTicketClick = (ticket) => {
    setSelectedTicket(ticket);
    setIsDrawerOpen(true);
  };

  const handleCloseDrawer = () => {
    setIsDrawerOpen(false);
    setSelectedTicket(null);
    // Navigate back to the appropriate view when closing from direct ticket URL
    if (view === 'ticket') {
      navigate('/all-tickets', { replace: true });
    }
  };

  const handleUpdateTicket = async (ticketId, updatedData) => {
    try {
      // Handle merge completion - just refresh without making an update API call
      if (updatedData._merged) {
        handleCloseDrawer();
        setRefreshKey(prev => prev + 1); // Trigger list refresh
        return;
      }
      
      // Handle split completion - refresh without making an update API call
      if (updatedData._split) {
        setRefreshKey(prev => prev + 1); // Trigger list refresh to show new ticket
        // Optionally refresh the current ticket data
        if (selectedTicket) {
          const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}`, {
            credentials: 'include'
          });
          if (response.ok) {
            const refreshedTicket = await response.json();
            setSelectedTicket(refreshedTicket);
          }
        }
        return;
      }
      
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
      <Sidebar user={user} />
      
      <div className="flex-1 flex flex-col relative min-w-0">
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
              refreshKey={refreshKey}
              user={user} 
              onTicketClick={handleTicketClick}
            />
          )}
          {view === 'open-tickets' && (
            <OpenTicketsPage 
              key={refreshKey}
              refreshKey={refreshKey}
              user={user} 
              onTicketClick={handleTicketClick}
            />
          )}
          {view === 'waiting-tickets' && (
            <WaitingTicketsPage 
              key={refreshKey}
              refreshKey={refreshKey}
              user={user} 
              onTicketClick={handleTicketClick}
            />
          )}
          {view === 'closed-tickets' && (
            <ClosedTicketsPage 
              key={refreshKey}
              refreshKey={refreshKey}
              user={user} 
              onTicketClick={handleTicketClick}
            />
          )}
          {view === 'starred-tickets' && (
            <StarredTicketsPage 
              key={refreshKey}
              refreshKey={refreshKey}
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
