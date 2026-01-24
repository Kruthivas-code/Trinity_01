import React, { useState, useEffect, useRef } from 'react';
import { 
  X, Save, Trash2, Send, ChevronDown, ChevronRight,
  Loader2, Clock, User, Link2, Star, MoreHorizontal, 
  Mail, AlertCircle, Sparkles, MessageSquare, PenLine,
  Command
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const STATUSES = [
  { value: 'todo', label: 'To Do', color: 'bg-slate-400' },
  { value: 'in_progress', label: 'In Progress', color: 'bg-blue-400' },
  { value: 'waiting', label: 'Waiting', color: 'bg-amber-400' },
  { value: 'review', label: 'Review', color: 'bg-purple-400' },
  { value: 'resolved', label: 'Resolved', color: 'bg-emerald-400' }
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
  
  // Notes and reply state
  const [notes, setNotes] = useState([]);
  const [inputText, setInputText] = useState('');
  const [inputMode, setInputMode] = useState('note'); // 'note' or 'reply'
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  // Collapsible sections
  const [sectionsExpanded, setSectionsExpanded] = useState({
    links: true,
    attributes: true
  });
  
  // Refs
  const inputRef = useRef(null);
  const contentRef = useRef(null);

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
      setInputText('');
      fetchNotes(ticket.id);
    }
  }, [ticket]);

  // Keyboard shortcut for switching modes
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
      // N for note, R for reply when not focused on input
      if (document.activeElement !== inputRef.current) {
        if (e.key === 'n' || e.key === 'N') {
          setInputMode('note');
          inputRef.current?.focus();
        }
        if (e.key === 'r' || e.key === 'R') {
          setInputMode('reply');
          inputRef.current?.focus();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

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

  const handleSubmitInput = async (e) => {
    e?.preventDefault();
    if (!inputText.trim() || !ticket) return;
    
    setSubmitting(true);
    try {
      if (inputMode === 'note') {
        const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/notes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ content: inputText.trim() })
        });
        if (!response.ok) throw new Error('Failed to add note');
        toast.success('Note added');
        fetchNotes(ticket.id);
      } else {
        // Reply mode - for now just add as a note with different type
        const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/notes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ content: inputText.trim(), type: 'reply' })
        });
        if (!response.ok) throw new Error('Failed to send reply');
        toast.success('Reply sent');
        fetchNotes(ticket.id);
      }
      setInputText('');
    } catch (error) {
      toast.error(inputMode === 'note' ? 'Failed to add note' : 'Failed to send reply');
    } finally {
      setSubmitting(false);
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

  const handleSave = () => {
    if (ticket) {
      onUpdate(ticket.id, formData);
      toast.success('Changes saved');
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

  const getStatusConfig = (status) => STATUSES.find(s => s.value === status) || STATUSES[0];
  const getPriorityConfig = (priority) => PRIORITIES.find(p => p.value === priority) || PRIORITIES[1];
  const getAssignee = () => formData.assignee_id ? users.find(u => u.id === formData.assignee_id) : null;

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
        className="fixed right-0 top-0 bottom-0 w-full max-w-5xl z-[60] flex shadow-2xl"
        data-testid="ticket-drawer"
      >
        {/* Left Panel - Content (~60%) */}
        <div className="flex-1 bg-[hsl(222,28%,7%)] border-l border-border/40 flex flex-col min-w-0">
          {/* Header */}
          <div className="h-12 px-4 flex items-center justify-between border-b border-border/30 shrink-0">
            <div className="flex items-center gap-2">
              <Mail size={15} className="text-primary" />
              <span className="text-sm font-medium">Ticket</span>
              <span className="text-[11px] text-muted-foreground font-mono bg-secondary/40 px-1.5 py-0.5 rounded">
                {ticket.ticket_id || `#${ticket.id?.slice(-8)}`}
              </span>
            </div>
            <div className="flex items-center gap-0.5">
              <button 
                className="h-7 w-7 flex items-center justify-center rounded hover:bg-white/5 transition-colors"
                title="Star"
              >
                <Star size={14} className="text-muted-foreground" />
              </button>
              <button 
                className="h-7 w-7 flex items-center justify-center rounded hover:bg-white/5 transition-colors"
                title="More options"
              >
                <MoreHorizontal size={14} className="text-muted-foreground" />
              </button>
              <button
                onClick={onClose}
                className="h-7 w-7 flex items-center justify-center rounded hover:bg-white/5 transition-colors ml-1"
                data-testid="drawer-close-button"
                title="Close"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Main Content Area - Scrollable */}
          <div ref={contentRef} className="flex-1 overflow-y-auto min-h-0">
            {/* Title */}
            <div className="px-5 pt-5 pb-3">
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full text-xl font-semibold bg-transparent border-0 focus:outline-none focus:ring-0 placeholder:text-muted-foreground/40"
                placeholder="Ticket title..."
                data-testid="drawer-title-input"
              />
            </div>

            {/* Description / Ticket Body */}
            <div className="px-5 pb-5">
              <div className="bg-secondary/20 rounded-lg border border-border/20 p-4 min-h-[200px]">
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full h-full min-h-[180px] text-sm text-foreground/90 leading-relaxed bg-transparent border-0 focus:outline-none focus:ring-0 resize-none placeholder:text-muted-foreground/40"
                  placeholder="Ticket description or customer message..."
                  data-testid="drawer-description-input"
                />
              </div>
            </div>

            {/* Activity / Notes Section */}
            <div className="px-5 pb-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Activity
                </h3>
                {notes.length > 0 && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/20 text-primary">
                    {notes.length}
                  </span>
                )}
              </div>

              {loadingNotes ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 size={18} className="animate-spin text-muted-foreground" />
                </div>
              ) : notes.length > 0 ? (
                <div className="space-y-3">
                  {notes.map((note) => (
                    <div
                      key={note.message_id || note._id}
                      className="flex gap-3"
                      data-testid={`note-${note.message_id}`}
                    >
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary/40 to-accent/40 flex items-center justify-center text-[10px] font-medium shrink-0 mt-0.5">
                        {note.author_name?.charAt(0).toUpperCase() || 'U'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-medium">{note.author_name || 'Unknown'}</span>
                          <span className="text-[11px] text-muted-foreground">{formatNoteDate(note.created_at)}</span>
                          {note.type === 'internal_note' && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-400/20 text-amber-400">Note</span>
                          )}
                        </div>
                        <p className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap">
                          {note.content}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground/50 text-center py-6">
                  No activity yet
                </p>
              )}
            </div>
          </div>

          {/* Input Area - Fixed at bottom */}
          <div className="shrink-0 border-t border-border/30 bg-[hsl(222,28%,6%)]">
            {/* Mode Toggle */}
            <div className="px-4 pt-3 pb-2 flex items-center gap-1">
              <button
                onClick={() => setInputMode('reply')}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
                  inputMode === 'reply' 
                    ? 'bg-primary/20 text-primary' 
                    : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
                }`}
                data-testid="mode-reply"
              >
                <Mail size={13} />
                <span>Reply</span>
                <span className="text-[10px] opacity-60 ml-1">R</span>
              </button>
              <button
                onClick={() => setInputMode('note')}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
                  inputMode === 'note' 
                    ? 'bg-amber-400/20 text-amber-400' 
                    : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
                }`}
                data-testid="mode-note"
              >
                <PenLine size={13} />
                <span>Note</span>
                <span className="text-[10px] opacity-60 ml-1">N</span>
              </button>
            </div>

            {/* Input Box */}
            <div className="px-4 pb-3">
              <div className="relative">
                <textarea
                  ref={inputRef}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                      e.preventDefault();
                      handleSubmitInput();
                    }
                  }}
                  placeholder={inputMode === 'note' ? 'Add an internal note...' : 'Type your reply...'}
                  className="w-full min-h-[80px] max-h-[150px] px-3 py-2.5 text-sm rounded-lg bg-secondary/30 border border-border/40 placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50 resize-none transition-all"
                  data-testid="input-textarea"
                />
                <div className="absolute bottom-2 right-2 flex items-center gap-2">
                  <span className="text-[10px] text-muted-foreground/50 flex items-center gap-1">
                    <Command size={10} />K for shortcuts
                  </span>
                  <button
                    onClick={handleSubmitInput}
                    disabled={submitting || !inputText.trim()}
                    className={`h-7 w-7 flex items-center justify-center rounded transition-colors ${
                      inputMode === 'note'
                        ? 'bg-amber-400/20 text-amber-400 hover:bg-amber-400/30'
                        : 'bg-primary/20 text-primary hover:bg-primary/30'
                    } disabled:opacity-40 disabled:cursor-not-allowed`}
                    data-testid="submit-input"
                  >
                    {submitting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel - Details (~320px) */}
        <div className="w-80 bg-[hsl(222,28%,8%)] border-l border-border/30 flex flex-col shrink-0">
          {/* Tabs */}
          <div className="h-12 px-4 flex items-center gap-4 border-b border-border/30 shrink-0">
            <button className="text-sm font-medium text-foreground relative pb-0.5">
              Details
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full" />
            </button>
            <button className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Activity
            </button>
          </div>

          {/* Details Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-5">
            {/* Assignee */}
            <div>
              <label className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider mb-2 block">
                Assignee
              </label>
              <select
                value={formData.assignee_id || ''}
                onChange={(e) => setFormData({ ...formData, assignee_id: e.target.value || null })}
                className="w-full h-9 px-3 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                data-testid="drawer-assignee-select"
              >
                <option value="">Unassigned</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>{user.name}</option>
                ))}
              </select>
              {assignee && (
                <div className="flex items-center gap-2 mt-2">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-primary/50 to-accent/50 flex items-center justify-center text-[10px] font-medium">
                    {assignee.name?.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-sm">{assignee.name}</span>
                </div>
              )}
            </div>

            {/* Status */}
            <div>
              <label className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider mb-2 block">
                Status
              </label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                className="w-full h-9 px-3 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                data-testid="drawer-status-select"
              >
                {STATUSES.map(status => (
                  <option key={status.value} value={status.value}>{status.label}</option>
                ))}
              </select>
              <div className="flex items-center gap-2 mt-2">
                <div className={`w-2.5 h-2.5 rounded-full ${statusConfig.color}`} />
                <span className="text-sm">{statusConfig.label}</span>
              </div>
            </div>

            {/* Priority */}
            <div>
              <label className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider mb-2 block">
                Priority
              </label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                className="w-full h-9 px-3 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                data-testid="drawer-priority-select"
              >
                {PRIORITIES.map(priority => (
                  <option key={priority.value} value={priority.value}>{priority.label}</option>
                ))}
              </select>
              <div className="flex items-center gap-2 mt-2">
                <AlertCircle size={14} className={priorityConfig.color} />
                <span className={`text-sm ${priorityConfig.color}`}>{priorityConfig.label}</span>
              </div>
            </div>

            {/* Divider */}
            <div className="h-px bg-border/30" />

            {/* Links Section */}
            <div>
              <button
                onClick={() => toggleSection('links')}
                className="w-full flex items-center justify-between py-1 group"
              >
                <div className="flex items-center gap-2">
                  <Link2 size={13} className="text-muted-foreground" />
                  <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Links</span>
                </div>
                {sectionsExpanded.links ? (
                  <ChevronDown size={13} className="text-muted-foreground" />
                ) : (
                  <ChevronRight size={13} className="text-muted-foreground" />
                )}
              </button>
              
              {sectionsExpanded.links && (
                <div className="mt-2 space-y-1">
                  <div className="flex items-center justify-between py-1.5 pl-5 text-sm text-muted-foreground hover:text-foreground cursor-pointer transition-colors">
                    <span>Related tickets</span>
                    <span className="text-primary text-xs">+ Add</span>
                  </div>
                  <div className="flex items-center justify-between py-1.5 pl-5 text-sm text-muted-foreground hover:text-foreground cursor-pointer transition-colors">
                    <span>External links</span>
                    <span className="text-primary text-xs">+ Add</span>
                  </div>
                </div>
              )}
            </div>

            {/* Divider */}
            <div className="h-px bg-border/30" />

            {/* Ticket Attributes */}
            <div>
              <button
                onClick={() => toggleSection('attributes')}
                className="w-full flex items-center justify-between py-1 group"
              >
                <div className="flex items-center gap-2">
                  <Sparkles size={13} className="text-muted-foreground" />
                  <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Ticket attributes</span>
                </div>
                {sectionsExpanded.attributes ? (
                  <ChevronDown size={13} className="text-muted-foreground" />
                ) : (
                  <ChevronRight size={13} className="text-muted-foreground" />
                )}
              </button>
              
              {sectionsExpanded.attributes && (
                <div className="mt-2 space-y-2.5 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">ID</span>
                    <span className="font-mono text-foreground/80 text-xs">
                      {ticket.ticket_id || ticket.id?.slice(-12)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Source</span>
                    <span className="capitalize text-foreground/80">{ticket.source || 'manual'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Domain</span>
                    <span className="text-foreground/80">{ticket.domain || '—'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Created</span>
                    <span className="text-foreground/80">{new Date(ticket.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Updated</span>
                    <span className="text-foreground/80">{new Date(ticket.updated_at).toLocaleDateString()}</span>
                  </div>
                  {ticket.tags && ticket.tags.length > 0 && (
                    <div className="flex items-start justify-between">
                      <span className="text-muted-foreground">Tags</span>
                      <div className="flex flex-wrap gap-1 justify-end max-w-[140px]">
                        {ticket.tags.map((tag, i) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-primary/20 text-primary">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">CX Score</span>
                    <span className="text-muted-foreground/50">—</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer Actions */}
          <div className="shrink-0 px-4 py-3 border-t border-border/30 bg-[hsl(222,28%,6%)]">
            {!showDeleteConfirm ? (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="h-8 px-3 flex items-center gap-1.5 text-xs text-destructive hover:bg-destructive/10 rounded-md transition-colors"
                  data-testid="drawer-delete-button"
                >
                  <Trash2 size={13} />
                  <span>Delete</span>
                </button>
                <button
                  onClick={handleSave}
                  className="flex-1 h-8 px-3 flex items-center justify-center gap-1.5 text-xs font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                  data-testid="drawer-save-button"
                >
                  <Save size={13} />
                  <span>Save Changes</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 h-8 px-3 text-xs border border-border/40 rounded-md hover:bg-white/5 transition-colors"
                  data-testid="drawer-delete-cancel-button"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  className="flex-1 h-8 px-3 text-xs font-medium bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 transition-colors"
                  data-testid="drawer-delete-confirm-button"
                >
                  Confirm Delete
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

export default TicketDrawer;
