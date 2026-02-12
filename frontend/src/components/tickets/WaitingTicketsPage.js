import React from 'react';
import TicketsListView from './TicketsListView';

const WaitingTicketsPage = ({ user, onTicketClick, refreshKey }) => {
  return (
    <TicketsListView
      title="Waiting on Customer"
      subtitle="Tickets awaiting customer response"
      filterStatuses={['waiting']}
      user={user}
      onTicketClick={onTicketClick}
      refreshKey={refreshKey}
    />
  );
};

export default WaitingTicketsPage;
