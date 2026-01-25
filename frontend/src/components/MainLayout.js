import React, { useState, useEffect, useContext } from 'react';
import Sidebar from './Sidebar';
import GlobalHeader from './GlobalHeader';
import DashboardContainer from './DashboardContainer';
import AllTicketsPage from './AllTicketsPage';
import OpenTicketsPage from './OpenTicketsPage';
import WaitingTicketsPage from './WaitingTicketsPage';
import ClosedTicketsPage from './ClosedTicketsPage';
import TicketDrawer from './TicketDrawer';
import CreateTicketModal from './CreateTicketModal';
import { CommandPaletteContext } from '../App';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const MainLayout = ({ user, view }) => {
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [users, setUsers] = useState([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const { openCommandPalette } = useContext(CommandPaletteContext);

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
  };

  const handleCloseDrawer = () => {
    setIsDrawerOpen(false);
    setSelectedTicket(null);
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
        </main>
      </div>

      {/* Shared Ticket Drawer */}
      {(view !== 'dashboard') && (
        <TicketDrawer
          ticket={selectedTicket}
          users={users}
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
