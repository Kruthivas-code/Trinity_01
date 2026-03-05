import React from 'react';
import TicketsListView from './TicketsListView';

const ClosedTicketsPage = ({ user, onTicketClick, refreshKey }) => {
  return (
    <TicketsListView
      title="Closed Tickets"
      subtitle="Resolved and completed tickets"
      filterStatuses={['closed']}
      user={user}
      onTicketClick={onTicketClick}
      refreshKey={refreshKey}
    />
  );
};

export default ClosedTicketsPage;
