import React from 'react';
import { useSearchParams } from 'react-router-dom';
import TicketsListView from './TicketsListView';

const AllTicketsPage = ({ user, onTicketClick, refreshKey }) => {
  const [searchParams] = useSearchParams();
  const levelFilter = searchParams.get('level');

  const title = levelFilter 
    ? `${levelFilter} Tickets` 
    : 'All Open Tickets';
  
  const subtitle = levelFilter
    ? `${levelFilter} escalation level tickets`
    : 'All unresolved tickets across the team';

  return (
    <TicketsListView
      title={title}
      subtitle={subtitle}
      filterStatuses={['todo', 'in_progress', 'waiting', 'review']}
      escalationLevel={levelFilter}
      user={user}
      onTicketClick={onTicketClick}
      refreshKey={refreshKey}
    />
  );
};

export default AllTicketsPage;
