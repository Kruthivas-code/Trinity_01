import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import TicketsListView from './TicketsListView';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const CustomInboxPage = ({ user, onTicketClick, refreshKey, onInboxUpdated }) => {
  const { inboxId } = useParams();
  const [inbox, setInbox] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchInbox = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${BACKEND_URL}/api/inboxes/${inboxId}`, {
          credentials: 'include',
        });
        if (response.ok) {
          const data = await response.json();
          setInbox(data);
        }
      } catch (e) {
        console.error('Failed to fetch inbox:', e);
      } finally {
        setLoading(false);
      }
    };
    if (inboxId) fetchInbox();
  }, [inboxId]);

  const handleSaveInbox = useCallback(async ({ name, color, filter_tree }) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/inboxes/${inboxId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name, color, filter_tree }),
      });
      if (response.ok) {
        const updated = await response.json();
        setInbox(updated);
        if (onInboxUpdated) onInboxUpdated(updated);
      }
    } catch (e) {
      console.error('Failed to update inbox:', e);
    }
  }, [inboxId, onInboxUpdated]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-pulse text-foreground">Loading inbox...</div>
      </div>
    );
  }

  if (!inbox) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Inbox not found</p>
      </div>
    );
  }

  return (
    <TicketsListView
      key={`inbox-${inboxId}`}
      title={inbox.name}
      subtitle={inbox.shared_from ? `Shared by ${inbox.shared_from.shared_by_name}` : 'Custom inbox'}
      filterTree={inbox.filter_tree}
      user={user}
      onTicketClick={onTicketClick}
      refreshKey={refreshKey}
      showFilterBuilder={true}
      onSaveInbox={handleSaveInbox}
    />
  );
};

export default CustomInboxPage;
