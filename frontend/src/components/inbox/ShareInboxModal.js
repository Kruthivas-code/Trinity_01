import React, { useState, useEffect } from 'react';
import { X, Search, Check } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const ShareInboxModal = ({ isOpen, onClose, inbox, currentUserId, onShared }) => {
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sharing, setSharing] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setSearch('');
    setSelected([]);
    setLoading(true);
    fetch(`${BACKEND_URL}/api/users`, { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        const list = Array.isArray(data) ? data : (data.items || []);
        setUsers(list.filter(u => u.user_id !== currentUserId));
      })
      .catch(() => setUsers([]))
      .finally(() => setLoading(false));
  }, [isOpen, currentUserId]);

  if (!isOpen || !inbox) return null;

  const filtered = users.filter(u =>
    !search || u.name?.toLowerCase().includes(search.toLowerCase()) || u.email?.toLowerCase().includes(search.toLowerCase())
  );

  const toggle = (uid) => {
    setSelected(prev => prev.includes(uid) ? prev.filter(id => id !== uid) : [...prev, uid]);
  };

  const handleShare = async () => {
    if (selected.length === 0) return;
    setSharing(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/inboxes/${inbox.inbox_id}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ user_ids: selected }),
      });
      if (res.ok) {
        const data = await res.json();
        if (onShared) onShared(data);
        onClose();
      }
    } catch (e) {
      console.error('Failed to share inbox:', e);
    } finally {
      setSharing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" data-testid="share-inbox-modal">
      <div className="bg-background border border-border rounded-xl shadow-xl w-full max-w-md animate-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div>
            <h3 className="text-base font-semibold">Share Inbox</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Share &ldquo;{inbox.name}&rdquo; with team members
            </p>
          </div>
          <button onClick={onClose} className="h-8 w-8 flex items-center justify-center rounded-md hover:bg-muted" data-testid="share-inbox-close">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-4">
          <div className="relative mb-3">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              data-testid="share-inbox-search"
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search by name or email..."
              className="w-full h-9 rounded-md border border-border bg-background pl-8 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>

          <div className="max-h-56 overflow-y-auto border border-border rounded-lg">
            {loading ? (
              <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">Loading users...</div>
            ) : filtered.length === 0 ? (
              <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">No users found</div>
            ) : (
              filtered.map(u => {
                const isSelected = selected.includes(u.user_id);
                return (
                  <button
                    key={u.user_id}
                    onClick={() => toggle(u.user_id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/50 transition-colors border-b border-border/40 last:border-b-0 ${isSelected ? 'bg-muted/30' : ''}`}
                    data-testid={`share-user-${u.user_id}`}
                  >
                    <div className={`h-5 w-5 rounded-md border flex items-center justify-center shrink-0 transition-colors ${isSelected ? 'bg-foreground border-foreground' : 'border-border'}`}>
                      {isSelected && <Check className="h-3 w-3 text-background" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{u.name}</p>
                      <p className="text-xs text-muted-foreground truncate">{u.email}</p>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {selected.length > 0 && (
            <p className="text-xs text-muted-foreground mt-2">{selected.length} user{selected.length > 1 ? 's' : ''} selected</p>
          )}
        </div>

        <div className="flex justify-end gap-2 px-5 py-4 border-t border-border">
          <button
            onClick={onClose}
            className="h-9 px-4 rounded-md border border-border text-sm hover:bg-muted"
            data-testid="share-inbox-cancel"
          >
            Cancel
          </button>
          <button
            onClick={handleShare}
            disabled={selected.length === 0 || sharing}
            className="h-9 px-4 rounded-md bg-foreground text-background text-sm font-medium hover:bg-foreground/90 disabled:opacity-40"
            data-testid="share-inbox-submit"
          >
            {sharing ? 'Sharing...' : `Share with ${selected.length || ''} user${selected.length !== 1 ? 's' : ''}`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ShareInboxModal;
