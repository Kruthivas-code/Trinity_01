import React, { useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import TicketsListView from './TicketsListView';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AllTicketsPage = ({ user, onTicketClick, refreshKey, onInboxCreated }) => {
  const [searchParams] = useSearchParams();
  const levelFilter = searchParams.get('level');

  const title = levelFilter 
    ? `${levelFilter} Tickets` 
    : 'All Open Tickets';
  
  const subtitle = levelFilter
    ? `${levelFilter} escalation level tickets`
    : 'All unresolved tickets across the team';

  const handleSaveInbox = useCallback(async ({ name, color, filter_tree }) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/inboxes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name, color, filter_tree }),
      });
      if (response.ok) {
        const inbox = await response.json();
        if (onInboxCreated) onInboxCreated(inbox);
      }
    } catch (e) {
      console.error('Failed to save inbox:', e);
    }
  }, [onInboxCreated]);

  return (
    <TicketsListView
      key={`tickets-${levelFilter || 'all'}`}
      title={title}
      subtitle={subtitle}
      filterStatuses={['todo', 'waiting']}
      escalationLevel={levelFilter}
      user={user}
      onTicketClick={onTicketClick}
      refreshKey={refreshKey}
      showFilterBuilder={true}
      onSaveInbox={handleSaveInbox}
      excludeZeus={true}
    />
  );
};

export default AllTicketsPage;
