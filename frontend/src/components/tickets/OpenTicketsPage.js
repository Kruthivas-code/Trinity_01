import React from 'react';
import TicketsListView from './TicketsListView';

const OpenTicketsPage = ({ user, onTicketClick, refreshKey }) => {
  return (
    <TicketsListView
      title="Open Tickets"
      subtitle="Active tickets being worked on"
      filterStatuses={['todo', 'in_progress', 'review']}
      user={user}
      onTicketClick={onTicketClick}
      refreshKey={refreshKey}
      excludeZeus={true}
    />
  );
};

export default OpenTicketsPage;
