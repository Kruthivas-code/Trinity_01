import React, { useContext, useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import GlobalHeader from './GlobalHeader';
import CreateTicketModal from '../tickets/CreateTicketModal';
import { CommandPaletteContext } from '../App';

/**
 * PageLayout - Wrapper that adds Sidebar and GlobalHeader to standalone pages
 * Used for pages that don't use MainLayout (Profile, Settings, Teams, Admin, Search)
 */
const PageLayout = ({ user, children }) => {
  const { openCommandPalette } = useContext(CommandPaletteContext);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Listen for create ticket events from GlobalHeader/CommandPalette
  useEffect(() => {
    const handleCreateTicket = () => setIsCreateModalOpen(true);
    window.addEventListener('trinity:create-ticket', handleCreateTicket);
    return () => window.removeEventListener('trinity:create-ticket', handleCreateTicket);
  }, []);

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
          {children}
        </main>
      </div>

      {/* Create Ticket Modal */}
      <CreateTicketModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreated={() => setIsCreateModalOpen(false)}
      />
    </div>
  );
};

export default PageLayout;
