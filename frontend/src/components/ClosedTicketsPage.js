import React from 'react';
import TicketsListView from './TicketsListView';

const ClosedTicketsPage = ({ user, onTicketClick }) => {
  return (
    <TicketsListView
      title="Closed Tickets"
      subtitle="Resolved and completed tickets"
      filterStatuses={['resolved', 'closed']}
      user={user}
      onTicketClick={onTicketClick}
    />
  );
};

export default ClosedTicketsPage;
