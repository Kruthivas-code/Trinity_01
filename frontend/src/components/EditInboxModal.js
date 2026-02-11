import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

const COLORS = [
  '#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4',
  '#3b82f6', '#8b5cf6', '#ec4899', '#6b7280', '#1e293b',
];

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const EditInboxModal = ({ isOpen, onClose, inbox, onUpdated }) => {
  const [name, setName] = useState('');
  const [color, setColor] = useState('#3b82f6');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen && inbox) {
      setName(inbox.name || '');
      setColor(inbox.color || '#3b82f6');
    }
  }, [isOpen, inbox]);

  if (!isOpen || !inbox) return null;

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/inboxes/${inbox.inbox_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name: name.trim(), color }),
      });
      if (res.ok) {
        const updated = await res.json();
        if (onUpdated) onUpdated(updated);
        onClose();
      }
    } catch (e) {
      console.error('Failed to update inbox:', e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" data-testid="edit-inbox-modal">
      <div className="bg-background border border-border rounded-xl shadow-xl w-full max-w-md p-6 animate-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold">Edit Inbox</h3>
          <button onClick={onClose} className="h-8 w-8 flex items-center justify-center rounded-md hover:bg-muted" data-testid="edit-inbox-close">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1.5 block">Inbox Name</label>
            <input
              data-testid="edit-inbox-name"
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Inbox name..."
              className="w-full h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              autoFocus
              onKeyDown={e => e.key === 'Enter' && handleSave()}
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-1.5 block">Color</label>
            <div className="flex gap-2">
              {COLORS.map(c => (
                <button
                  key={c}
                  onClick={() => setColor(c)}
                  className={`h-7 w-7 rounded-full border-2 transition-transform ${color === c ? 'border-foreground scale-110' : 'border-transparent'}`}
                  style={{ backgroundColor: c }}
                  data-testid={`edit-inbox-color-${c}`}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="h-9 px-4 rounded-md border border-border text-sm hover:bg-muted" data-testid="edit-inbox-cancel">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim() || saving}
            className="h-9 px-4 rounded-md bg-foreground text-background text-sm font-medium hover:bg-foreground/90 disabled:opacity-40"
            data-testid="edit-inbox-submit"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EditInboxModal;
