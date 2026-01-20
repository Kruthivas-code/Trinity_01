import React from 'react';
import TicketsListView from './TicketsListView';

const WaitingTicketsPage = ({ user, onTicketClick }) => {
  return (
    <TicketsListView
      title="Waiting on Customer"
      subtitle="Tickets awaiting customer response"
      filterStatuses={['waiting']}
      user={user}
      onTicketClick={onTicketClick}
    />
  );
};

export default WaitingTicketsPage;
