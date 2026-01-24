import React, { useState, useEffect } from 'react';
import { X, Trash2, Save, MessageSquare, Send, ChevronDown, ChevronUp, Loader2, StickyNote, Clock, User } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const STATUSES = [
  { value: 'todo', label: 'To Do' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'waiting', label: 'Waiting on Customer' },
  { value: 'review', label: 'Review' },
  { value: 'resolved', label: 'Resolved' }
];

const PRIORITIES = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' }
];

const TicketDrawer = ({ ticket, users, isOpen, onClose, onUpdate, onDelete, currentUser }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'backlog',
    assignee_id: null,
    priority: 'medium'
  });
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  
  // Internal notes state
  const [notes, setNotes] = useState([]);
  const [newNote, setNewNote] = useState('');
  const [notesExpanded, setNotesExpanded] = useState(true);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [addingNote, setAddingNote] = useState(false);

  useEffect(() => {
    if (ticket) {
      setFormData({
        title: ticket.title || '',
        description: ticket.description || '',
        status: ticket.status || 'backlog',
        assignee_id: ticket.assignee_id || null,
        priority: ticket.priority || 'medium'
      });
      setShowDeleteConfirm(false); // Reset delete confirmation when opening drawer
      fetchNotes(ticket.id);
    }
  }, [ticket]);

  const fetchNotes = async (ticketId) => {
    setLoadingNotes(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}/notes`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setNotes(data);
      }
    } catch (error) {
      console.error('Failed to fetch notes:', error);
    } finally {
      setLoadingNotes(false);
    }
  };

  const handleAddNote = async (e) => {
    e.preventDefault();
    if (!newNote.trim() || !ticket) return;
    
    setAddingNote(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ content: newNote.trim() })
      });
      
      if (!response.ok) throw new Error('Failed to add note');
      
      toast.success('Note added');
      setNewNote('');
      fetchNotes(ticket.id);
    } catch (error) {
      toast.error('Failed to add note');
    } finally {
      setAddingNote(false);
    }
  };

  const formatNoteDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setShowDeleteConfirm(false); // Reset after save
    if (ticket) {
      onUpdate(ticket.id, formData);
    }
  };

  const handleDelete = () => {
    if (ticket) {
      onDelete(ticket.id);
    }
  };

  const handleDeleteClick = () => {
    console.log('Delete button clicked, current showDeleteConfirm:', showDeleteConfirm);
    setShowDeleteConfirm(prev => {
      console.log('Setting showDeleteConfirm from', prev, 'to true');
      return true;
    });
  };

  const handleCancelDelete = () => {
    console.log('Cancel delete clicked');
    setShowDeleteConfirm(false);
  };

  const handleConfirmDelete = () => {
    console.log('Confirm delete clicked');
    handleDelete();
  };

  if (!isOpen || !ticket) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 pointer-events-auto"
        onClick={onClose}
        data-testid="drawer-backdrop"
        style={{ pointerEvents: 'auto' }}
      />

      {/* Drawer */}
      <div
        className="fixed right-0 top-0 bottom-0 w-full max-w-md glass-elevated border-l border-border/60 z-[60] overflow-y-auto pointer-events-auto"
        data-testid="ticket-drawer"
        style={{ pointerEvents: 'auto' }}
      >
        <form onSubmit={handleSubmit} className="h-full flex flex-col">
          {/* Header */}
          <div className="px-6 py-4 border-b border-border/40 flex items-center justify-between sticky top-0 bg-transparent backdrop-blur">
            <h2 className="text-lg font-semibold" data-testid="drawer-title">
              Edit Ticket
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-white/5 transition-interactive"
              data-testid="drawer-close-button"
            >
              <X size={18} />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 px-6 py-6 space-y-5">
            {/* Title */}
            <div>
              <label className="block text-sm font-medium mb-2" htmlFor="drawer-title-input">
                Title
              </label>
              <input
                id="drawer-title-input"
                type="text"
                className="w-full h-10 px-4 rounded-lg bg-secondary/70 border border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                required
                data-testid="drawer-title-input"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium mb-2" htmlFor="drawer-description-input">
                Description
              </label>
              <textarea
                id="drawer-description-input"
                className="w-full min-h-[120px] px-4 py-3 rounded-lg bg-secondary/70 border border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive resize-none"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Add a description..."
                data-testid="drawer-description-input"
              />
            </div>

            {/* Status */}
            <div>
              <label className="block text-sm font-medium mb-2" htmlFor="drawer-status-select">
                Status
              </label>
              <select
                id="drawer-status-select"
                className="w-full h-10 px-4 rounded-lg bg-secondary/70 border border-white/10 text-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                data-testid="drawer-status-select"
              >
                {STATUSES.map(status => (
                  <option key={status.value} value={status.value}>
                    {status.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Priority */}
            <div>
              <label className="block text-sm font-medium mb-2" htmlFor="drawer-priority-select">
                Priority
              </label>
              <select
                id="drawer-priority-select"
                className="w-full h-10 px-4 rounded-lg bg-secondary/70 border border-white/10 text-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                data-testid="drawer-priority-select"
              >
                {PRIORITIES.map(priority => (
                  <option key={priority.value} value={priority.value}>
                    {priority.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Assignee */}
            <div>
              <label className="block text-sm font-medium mb-2" htmlFor="drawer-assignee-select">
                Assignee
              </label>
              <select
                id="drawer-assignee-select"
                className="w-full h-10 px-4 rounded-lg bg-secondary/70 border border-white/10 text-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                value={formData.assignee_id || ''}
                onChange={(e) => setFormData({ ...formData, assignee_id: e.target.value || null })}
                data-testid="drawer-assignee-select"
              >
                <option value="">Unassigned</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>
                    {user.name} ({user.email})
                  </option>
                ))}
              </select>
            </div>

            {/* Metadata */}
            <div className="pt-4 border-t border-border/40">
              <div className="space-y-2 text-xs text-muted-foreground">
                <div className="flex justify-between">
                  <span>Created:</span>
                  <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Updated:</span>
                  <span>{new Date(ticket.updated_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>ID:</span>
                  <span className="font-mono">{ticket.ticket_id || `#${ticket.id?.slice(-8)}`}</span>
                </div>
              </div>
            </div>

            {/* Internal Notes Section */}
            <div className="pt-4 border-t border-border/40" data-testid="internal-notes-section">
              <button
                type="button"
                onClick={() => setNotesExpanded(!notesExpanded)}
                className="w-full flex items-center justify-between py-2 text-sm font-medium hover:text-primary transition-interactive"
              >
                <div className="flex items-center gap-2">
                  <StickyNote size={16} className="text-amber-400" />
                  <span>Internal Notes</span>
                  {notes.length > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full text-xs bg-amber-400/20 text-amber-400">
                      {notes.length}
                    </span>
                  )}
                </div>
                {notesExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
              
              {notesExpanded && (
                <div className="mt-3 space-y-3">
                  {/* Add Note Form */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newNote}
                      onChange={(e) => setNewNote(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleAddNote(e);
                        }
                      }}
                      placeholder="Add internal note..."
                      className="flex-1 h-9 px-3 rounded-lg bg-secondary/70 border border-white/10 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-amber-400/50 transition-interactive"
                      data-testid="note-input"
                    />
                    <button
                      type="button"
                      onClick={handleAddNote}
                      disabled={addingNote || !newNote.trim()}
                      className="h-9 w-9 flex items-center justify-center rounded-lg bg-amber-400/20 text-amber-400 hover:bg-amber-400/30 disabled:opacity-50 disabled:cursor-not-allowed transition-interactive"
                      data-testid="add-note-button"
                    >
                      {addingNote ? <Loader2 size={16} className="animate-spin" /> : <Send size={14} />}
                    </button>
                  </div>

                  {/* Notes List */}
                  {loadingNotes ? (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 size={20} className="animate-spin text-muted-foreground" />
                    </div>
                  ) : notes.length > 0 ? (
                    <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                      {notes.map((note) => (
                        <div
                          key={note.message_id || note._id}
                          className="p-3 rounded-lg bg-amber-400/5 border border-amber-400/10"
                          data-testid={`note-${note.message_id}`}
                        >
                          <p className="text-sm text-foreground whitespace-pre-wrap">{note.content}</p>
                          <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                            <div className="flex items-center gap-1">
                              <User size={12} />
                              <span>{note.author_name || 'Unknown'}</span>
                            </div>
                            <span>•</span>
                            <div className="flex items-center gap-1">
                              <Clock size={12} />
                              <span>{formatNoteDate(note.created_at)}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-3">
                      No internal notes yet
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Footer - Save Button */}
          <div className="px-6 py-4 border-t border-border/40">
            <button
              type="submit"
              className="w-full h-10 px-4 flex items-center justify-center gap-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-cyan-400/90 transition-interactive"
              data-testid="drawer-save-button"
            >
              <Save size={16} />
              Save Changes
            </button>
          </div>
        </form>

        {/* Delete Section - Outside Form */}
        <div className="px-6 py-4 border-t border-border/40">
          {!showDeleteConfirm ? (
            <button
              type="button"
              onClick={handleDeleteClick}
              className="w-full h-10 px-4 flex items-center justify-center gap-2 rounded-lg bg-destructive/20 text-destructive hover:bg-destructive/30 transition-interactive"
              data-testid="drawer-delete-button"
            >
              <Trash2 size={16} />
              <span className="ml-1">Delete Ticket</span>
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleCancelDelete}
                className="flex-1 h-10 px-4 flex items-center justify-center gap-2 rounded-lg bg-secondary/70 text-secondary-foreground border border-white/10 hover:bg-secondary/90 transition-interactive"
                data-testid="drawer-delete-cancel-button"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                className="flex-1 h-10 px-4 flex items-center justify-center gap-2 rounded-lg bg-destructive text-destructive-foreground font-medium transition-interactive"
                data-testid="drawer-delete-confirm-button"
              >
                Confirm Delete
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default TicketDrawer;
