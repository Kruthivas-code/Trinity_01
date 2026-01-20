import React from 'react';
import TicketsListView from './TicketsListView';

const AllTicketsPage = ({ user, onTicketClick }) => {
  return (
    <TicketsListView
      title="All Open Tickets"
      subtitle="All unresolved tickets across the team"
      filterStatuses={['todo', 'in_progress', 'waiting', 'review']}
      user={user}
      onTicketClick={onTicketClick}
    />
  );
};

export default AllTicketsPage;
