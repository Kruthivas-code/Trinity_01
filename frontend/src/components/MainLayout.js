import React, { useState } from 'react';
import Sidebar from './Sidebar';
import DashboardContainer from './DashboardContainer';
import AllTicketsPage from './AllTicketsPage';
import OpenTicketsPage from './OpenTicketsPage';
import WaitingTicketsPage from './WaitingTicketsPage';
import ClosedTicketsPage from './ClosedTicketsPage';
import TicketDrawer from './TicketDrawer';

const MainLayout = ({ user, view }) => {
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const handleTicketClick = (ticket) => {
    setSelectedTicket(ticket);
    setIsDrawerOpen(true);
  };

  const handleCloseDrawer = () => {
    setIsDrawerOpen(false);
    setSelectedTicket(null);
  };

  return (
    <div className="min-h-screen flex bg-background">
      <div className="gradient-overlay" />
      
      <Sidebar user={user} />
      
      <main className="flex-1 relative z-10">
        {view === 'dashboard' && (
          <DashboardContainer 
            user={user} 
            onTicketClickFromExternal={handleTicketClick}
          />
        )}
        {view === 'all-tickets' && (
          <AllTicketsPage 
            user={user} 
            onTicketClick={handleTicketClick}
          />
        )}
        {view === 'open-tickets' && (
          <OpenTicketsPage 
            user={user} 
            onTicketClick={handleTicketClick}
          />
        )}
        {view === 'waiting-tickets' && (
          <WaitingTicketsPage 
            user={user} 
            onTicketClick={handleTicketClick}
          />
        )}
        {view === 'closed-tickets' && (
          <ClosedTicketsPage 
            user={user} 
            onTicketClick={handleTicketClick}
          />
        )}
      </main>

      {/* Shared Ticket Drawer */}
      {(view !== 'dashboard') && (
        <TicketDrawer
          ticket={selectedTicket}
          users={[]}
          isOpen={isDrawerOpen}
          onClose={handleCloseDrawer}
          onUpdate={() => {}} 
          onDelete={() => {}}
        />
      )}
    </div>
  );
};

export default MainLayout;
