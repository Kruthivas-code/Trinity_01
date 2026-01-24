import React, { useState, useEffect } from 'react';
import { 
  X, Save, Trash2, MessageSquare, Send, ChevronDown, ChevronRight,
  Loader2, StickyNote, Clock, User, Tag, Link2, Users, Star,
  MoreHorizontal, Mail, Calendar, AlertCircle, CheckCircle,
  Circle, ArrowUpRight, Building, Hash, Sparkles
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const STATUSES = [
  { value: 'todo', label: 'To Do', color: 'bg-slate-500' },
  { value: 'in_progress', label: 'In Progress', color: 'bg-blue-500' },
  { value: 'waiting', label: 'Waiting', color: 'bg-amber-500' },
  { value: 'review', label: 'Review', color: 'bg-purple-500' },
  { value: 'resolved', label: 'Resolved', color: 'bg-emerald-500' }
];

const PRIORITIES = [
  { value: 'low', label: 'Low', color: 'text-slate-400' },
  { value: 'medium', label: 'Medium', color: 'text-amber-400' },
  { value: 'high', label: 'High', color: 'text-orange-400' },
  { value: 'urgent', label: 'Urgent', color: 'text-red-400' }
];

const TicketDrawer = ({ ticket, users, isOpen, onClose, onUpdate, onDelete }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'todo',
    assignee_id: null,
    priority: 'medium'
  });
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  
  // Internal notes state
  const [notes, setNotes] = useState([]);
  const [newNote, setNewNote] = useState('');
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [addingNote, setAddingNote] = useState(false);
  
  // Collapsible sections
  const [sectionsExpanded, setSectionsExpanded] = useState({
    links: true,
    attributes: true,
    notes: true
  });

  useEffect(() => {
    if (ticket) {
      setFormData({
        title: ticket.title || '',
        description: ticket.description || '',
        status: ticket.status || 'todo',
        assignee_id: ticket.assignee_id || null,
        priority: ticket.priority || 'medium'
      });
      setShowDeleteConfirm(false);
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
    setShowDeleteConfirm(false);
    if (ticket) {
      onUpdate(ticket.id, formData);
    }
  };

  const handleDelete = () => {
    if (ticket) {
      onDelete(ticket.id);
    }
  };

  const toggleSection = (section) => {
    setSectionsExpanded(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const getStatusConfig = (status) => {
    return STATUSES.find(s => s.value === status) || STATUSES[0];
  };

  const getPriorityConfig = (priority) => {
    return PRIORITIES.find(p => p.value === priority) || PRIORITIES[1];
  };

  const getAssignee = () => {
    if (!formData.assignee_id) return null;
    return users.find(u => u.id === formData.assignee_id);
  };

  if (!isOpen || !ticket) return null;

  const statusConfig = getStatusConfig(formData.status);
  const priorityConfig = getPriorityConfig(formData.priority);
  const assignee = getAssignee();

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50"
        onClick={onClose}
        data-testid="drawer-backdrop"
      />

      {/* Two-Panel Drawer */}
      <div
        className="fixed right-0 top-0 bottom-0 w-full max-w-5xl z-[60] flex"
        data-testid="ticket-drawer"
      >
        {/* Left Panel - Conversation/Content */}
        <div className="flex-1 bg-[hsl(222,28%,7%)] border-l border-border/40 flex flex-col">
          {/* Header */}
          <div className="h-14 px-5 flex items-center justify-between border-b border-border/30 shrink-0">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Mail size={16} className="text-primary" />
                <span className="font-medium text-sm">Ticket</span>
              </div>
              <span className="text-xs text-muted-foreground font-mono">
                {ticket.ticket_id || `#${ticket.id?.slice(-8)}`}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <button className="h-8 w-8 flex items-center justify-center rounded-md hover:bg-white/5 transition-colors">
                <Star size={16} className="text-muted-foreground" />
              </button>
              <button className="h-8 w-8 flex items-center justify-center rounded-md hover:bg-white/5 transition-colors">
                <MoreHorizontal size={16} className="text-muted-foreground" />
              </button>
              <button
                onClick={onClose}
                className="h-8 w-8 flex items-center justify-center rounded-md hover:bg-white/5 transition-colors ml-2"
                data-testid="drawer-close-button"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            {/* Title & Description Section */}
            <div className="p-5 border-b border-border/20">
              <form onSubmit={handleSubmit}>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full text-lg font-medium bg-transparent border-0 focus:outline-none focus:ring-0 placeholder:text-muted-foreground/50 mb-3"
                  placeholder="Ticket title..."
                  data-testid="drawer-title-input"
                />
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full text-sm text-muted-foreground bg-transparent border-0 focus:outline-none focus:ring-0 resize-none min-h-[80px] placeholder:text-muted-foreground/40"
                  placeholder="Add a description..."
                  data-testid="drawer-description-input"
                />
              </form>
            </div>

            {/* Internal Notes Section */}
            <div className="p-5" data-testid="internal-notes-section">
              <button
                onClick={() => toggleSection('notes')}
                className="w-full flex items-center justify-between mb-4 group"
              >
                <div className="flex items-center gap-2">
                  <MessageSquare size={15} className="text-primary" />
                  <span className="text-sm font-medium">Internal Notes</span>
                  {notes.length > 0 && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-primary/20 text-primary">
                      {notes.length}
                    </span>
                  )}
                </div>
                {sectionsExpanded.notes ? (
                  <ChevronDown size={14} className="text-muted-foreground" />
                ) : (
                  <ChevronRight size={14} className="text-muted-foreground" />
                )}
              </button>

              {sectionsExpanded.notes && (
                <div className="space-y-3">
                  {/* Add Note Input */}
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
                      className="flex-1 h-9 px-3 text-sm rounded-lg bg-secondary/40 border border-border/30 placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/50 transition-all"
                      data-testid="note-input"
                    />
                    <button
                      onClick={handleAddNote}
                      disabled={addingNote || !newNote.trim()}
                      className="h-9 w-9 flex items-center justify-center rounded-lg bg-primary/20 text-primary hover:bg-primary/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      data-testid="add-note-button"
                    >
                      {addingNote ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                    </button>
                  </div>

                  {/* Notes List */}
                  {loadingNotes ? (
                    <div className="flex items-center justify-center py-6">
                      <Loader2 size={18} className="animate-spin text-muted-foreground" />
                    </div>
                  ) : notes.length > 0 ? (
                    <div className="space-y-2 max-h-72 overflow-y-auto">
                      {notes.map((note) => (
                        <div
                          key={note.message_id || note._id}
                          className="p-3 rounded-lg bg-secondary/20 border border-border/20"
                          data-testid={`note-${note.message_id}`}
                        >
                          <p className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed">
                            {note.content}
                          </p>
                          <div className="flex items-center gap-3 mt-2.5 text-xs text-muted-foreground">
                            <div className="flex items-center gap-1.5">
                              <div className="w-4 h-4 rounded-full bg-primary/30 flex items-center justify-center">
                                <User size={10} className="text-primary" />
                              </div>
                              <span>{note.author_name || 'Unknown'}</span>
                            </div>
                            <span className="text-muted-foreground/40">•</span>
                            <span>{formatNoteDate(note.created_at)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground/60 text-center py-4">
                      No internal notes yet
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Footer Actions */}
          <div className="h-14 px-5 flex items-center justify-between border-t border-border/30 shrink-0 bg-[hsl(222,28%,6%)]">
            {!showDeleteConfirm ? (
              <>
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="h-8 px-3 flex items-center gap-1.5 text-xs text-destructive hover:bg-destructive/10 rounded-md transition-colors"
                  data-testid="drawer-delete-button"
                >
                  <Trash2 size={14} />
                  <span>Delete</span>
                </button>
                <button
                  onClick={handleSubmit}
                  className="h-8 px-4 flex items-center gap-1.5 text-xs font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                  data-testid="drawer-save-button"
                >
                  <Save size={14} />
                  <span>Save Changes</span>
                </button>
              </>
            ) : (
              <div className="flex items-center gap-2 w-full justify-end">
                <span className="text-xs text-muted-foreground mr-2">Confirm delete?</span>
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="h-8 px-3 text-xs border border-border/40 rounded-md hover:bg-white/5 transition-colors"
                  data-testid="drawer-delete-cancel-button"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  className="h-8 px-3 text-xs font-medium bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 transition-colors"
                  data-testid="drawer-delete-confirm-button"
                >
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Details */}
        <div className="w-80 bg-[hsl(222,28%,8%)] border-l border-border/30 flex flex-col shrink-0">
          {/* Tabs */}
          <div className="h-14 px-4 flex items-center gap-4 border-b border-border/30 shrink-0">
            <button className="text-sm font-medium text-foreground pb-0.5 border-b-2 border-primary">
              Details
            </button>
            <button className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Activity
            </button>
          </div>

          {/* Details Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Assignee */}
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground font-medium">Assignee</label>
              <select
                value={formData.assignee_id || ''}
                onChange={(e) => setFormData({ ...formData, assignee_id: e.target.value || null })}
                className="w-full h-9 px-3 text-sm rounded-lg bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                data-testid="drawer-assignee-select"
              >
                <option value="">Unassigned</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>
                    {user.name}
                  </option>
                ))}
              </select>
              {assignee && (
                <div className="flex items-center gap-2 mt-1">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-primary/50 to-accent/50 flex items-center justify-center text-[10px] font-medium">
                    {assignee.name?.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-sm">{assignee.name}</span>
                </div>
              )}
            </div>

            {/* Status */}
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground font-medium">Status</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                className="w-full h-9 px-3 text-sm rounded-lg bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                data-testid="drawer-status-select"
              >
                {STATUSES.map(status => (
                  <option key={status.value} value={status.value}>
                    {status.label}
                  </option>
                ))}
              </select>
              <div className="flex items-center gap-2 mt-1">
                <div className={`w-2 h-2 rounded-full ${statusConfig.color}`} />
                <span className="text-sm">{statusConfig.label}</span>
              </div>
            </div>

            {/* Priority */}
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground font-medium">Priority</label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                className="w-full h-9 px-3 text-sm rounded-lg bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                data-testid="drawer-priority-select"
              >
                {PRIORITIES.map(priority => (
                  <option key={priority.value} value={priority.value}>
                    {priority.label}
                  </option>
                ))}
              </select>
              <div className="flex items-center gap-2 mt-1">
                <AlertCircle size={14} className={priorityConfig.color} />
                <span className={`text-sm ${priorityConfig.color}`}>{priorityConfig.label}</span>
              </div>
            </div>

            {/* Divider */}
            <div className="h-px bg-border/30 my-2" />

            {/* Links Section */}
            <div>
              <button
                onClick={() => toggleSection('links')}
                className="w-full flex items-center justify-between py-2"
              >
                <div className="flex items-center gap-2">
                  <Link2 size={14} className="text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground">Links</span>
                </div>
                {sectionsExpanded.links ? (
                  <ChevronDown size={12} className="text-muted-foreground" />
                ) : (
                  <ChevronRight size={12} className="text-muted-foreground" />
                )}
              </button>
              
              {sectionsExpanded.links && (
                <div className="space-y-1 pl-5 mt-1">
                  <div className="flex items-center justify-between py-1.5 text-sm text-muted-foreground hover:text-foreground cursor-pointer transition-colors">
                    <span>Related tickets</span>
                    <span className="text-primary text-xs">+ Add</span>
                  </div>
                  <div className="flex items-center justify-between py-1.5 text-sm text-muted-foreground hover:text-foreground cursor-pointer transition-colors">
                    <span>External links</span>
                    <span className="text-primary text-xs">+ Add</span>
                  </div>
                </div>
              )}
            </div>

            {/* Divider */}
            <div className="h-px bg-border/30 my-2" />

            {/* Ticket Attributes Section */}
            <div>
              <button
                onClick={() => toggleSection('attributes')}
                className="w-full flex items-center justify-between py-2"
              >
                <div className="flex items-center gap-2">
                  <Sparkles size={14} className="text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground">Ticket attributes</span>
                </div>
                {sectionsExpanded.attributes ? (
                  <ChevronDown size={12} className="text-muted-foreground" />
                ) : (
                  <ChevronRight size={12} className="text-muted-foreground" />
                )}
              </button>
              
              {sectionsExpanded.attributes && (
                <div className="space-y-3 pl-1 mt-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">ID</span>
                    <span className="text-xs font-mono text-foreground/80">
                      {ticket.ticket_id || ticket.id?.slice(-12)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Source</span>
                    <span className="text-xs capitalize text-foreground/80">
                      {ticket.source || 'manual'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Domain</span>
                    <span className="text-xs text-foreground/80">
                      {ticket.domain || '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Created</span>
                    <span className="text-xs text-foreground/80">
                      {new Date(ticket.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Updated</span>
                    <span className="text-xs text-foreground/80">
                      {new Date(ticket.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  {ticket.tags && ticket.tags.length > 0 && (
                    <div className="flex items-start justify-between">
                      <span className="text-xs text-muted-foreground">Tags</span>
                      <div className="flex flex-wrap gap-1 justify-end max-w-[140px]">
                        {ticket.tags.map((tag, i) => (
                          <span
                            key={i}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-primary/20 text-primary"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">CX Score</span>
                    <span className="text-xs text-muted-foreground/60">—</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default TicketDrawer;
