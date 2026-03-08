import React from 'react';
import TicketsListView from './TicketsListView';

const AIAssignedTicketsPage = ({ user, onTicketClick, refreshKey }) => {
  return (
    <TicketsListView
      title="Assigned to AI"
      subtitle="Tickets currently handled by Zeus (AI agent)"
      filterStatuses={['todo', 'waiting']}
      customParams={{ atlas_assigned_to_zeus: 'true' }}
      user={user}
      onTicketClick={onTicketClick}
      refreshKey={refreshKey}
    />
  );
};

export default AIAssignedTicketsPage;
