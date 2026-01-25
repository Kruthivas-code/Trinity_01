import React, { useState, useEffect, useRef } from 'react';
import { 
  X, Save, Trash2, Send, ChevronDown, ChevronRight,
  Loader2, Star, MoreHorizontal, Mail, AlertCircle, 
  Sparkles, PenLine, Command, Link2, Settings, Users,
  Clock, ArrowUpCircle, UserCheck
} from 'lucide-react';
import RichTextEditor from './RichTextEditor';

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

const ESCALATION_LEVELS = [
  { value: 'L1', label: 'L1 - Basic Support', color: 'bg-blue-500' },
  { value: 'L2', label: 'L2 - Advanced Support', color: 'bg-amber-500' },
  { value: 'L3', label: 'L3 - Specialist', color: 'bg-red-500' }
];

// Strip HTML for plain text display
const stripHtml = (html) => {
  if (!html) return '';
  // Remove style tags and their content
  let text = html.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
  // Remove script tags
  text = text.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
  // Remove HTML tags
  text = text.replace(/<[^>]*>/g, ' ');
  // Remove CSS properties that might be in text
  text = text.replace(/[\w-]+\s*:\s*[^;]+;/g, ' ');
  // Decode common HTML entities
  text = text.replace(/&nbsp;/g, ' ')
             .replace(/&amp;/g, '&')
             .replace(/&lt;/g, '<')
             .replace(/&gt;/g, '>')
             .replace(/&quot;/g, '"')
             .replace(/&#39;/g, "'")
             .replace(/&#\d+;/g, ' ');
  // Remove multiple spaces and trim
  return text.replace(/\s+/g, ' ').trim();
};

// Email-style message component
const EmailMessage = ({ type, sender, senderEmail, subject, content, timestamp, isFirst }) => {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  const isNote = type === 'internal_note';
  
  // Render HTML content safely
  const renderContent = (html) => {
    if (!html) return <span className="text-muted-foreground/50 italic">No content</span>;
    
    // Check if content is HTML or plain text
    const hasHtml = /<[^>]+>/.test(html);
    if (hasHtml) {
      return (
        <div 
          className="prose prose-sm dark:prose-invert max-w-none
            [&_a]:text-primary [&_a]:underline
            [&_blockquote]:border-l-2 [&_blockquote]:border-primary/30 [&_blockquote]:pl-3 [&_blockquote]:italic
            [&_pre]:bg-secondary/50 [&_pre]:rounded [&_pre]:p-2 [&_pre]:text-xs [&_pre]:overflow-x-auto
            [&_code]:bg-secondary/50 [&_code]:rounded [&_code]:px-1 [&_code]:text-xs
            [&_ul]:list-disc [&_ul]:pl-4 [&_ul]:my-1
            [&_ol]:list-decimal [&_ol]:pl-4 [&_ol]:my-1
            [&_p]:my-1 [&_br]:my-0.5
            [&_img]:max-w-full [&_img]:rounded"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      );
    }
    return <p className="whitespace-pre-wrap">{html}</p>;
  };
  
  return (
    <div className={`rounded-lg ${isNote ? 'bg-amber-500/5 border-l-2 border-l-amber-400' : 'bg-secondary/20'} p-4`}>
      {/* Email Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium shrink-0 ${
            isNote 
              ? 'bg-amber-400/20 text-amber-400' 
              : 'bg-gradient-to-br from-primary/40 to-accent/40 text-white'
          }`}>
            {sender?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-sm">{sender || 'Unknown'}</span>
              {isNote && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-400/20 text-amber-400 font-medium">
                  Internal Note
                </span>
              )}
            </div>
            {senderEmail && (
              <p className="text-xs text-muted-foreground">{senderEmail}</p>
            )}
            {subject && isFirst && (
              <p className="text-xs text-muted-foreground mt-0.5">Subject: {subject}</p>
            )}
          </div>
        </div>
        <span className="text-[11px] text-muted-foreground shrink-0">
          {formatDate(timestamp)}
        </span>
      </div>
      
      {/* Email Body */}
      <div className="pl-11 text-sm text-foreground/90 leading-relaxed">
        {renderContent(content)}
      </div>
    </div>
  );
};

const TicketDrawer = ({ ticket, users, isOpen, onClose, onUpdate, onDelete }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'todo',
    assignee_id: null,
    priority: 'medium'
  });
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  
  // Notes and conversation state
  const [notes, setNotes] = useState([]);
  const [inputText, setInputText] = useState('');
  const [inputMode, setInputMode] = useState('note');
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  // Related tickets (from same customer)
  const [relatedTickets, setRelatedTickets] = useState([]);
  const [loadingRelated, setLoadingRelated] = useState(false);
  const [relatedExpanded, setRelatedExpanded] = useState(false);
  
  // Custom fields
  const [customFields, setCustomFields] = useState([]);
  const [customFieldValues, setCustomFieldValues] = useState({});
  
  // Assignment options (team members + other teams)
  const [assignmentOptions, setAssignmentOptions] = useState(null);
  const [showAssignDropdown, setShowAssignDropdown] = useState(false);
  const [escalating, setEscalating] = useState(false);
  
  // Collapsible sections
  const [sectionsExpanded, setSectionsExpanded] = useState({
    links: false,
    attributes: true,
    customFields: true,
    escalation: true
  });
  
  // Refs
  const conversationRef = useRef(null);

  useEffect(() => {
    if (ticket) {
      setFormData({
        title: ticket.title || '',
        description: ticket.description || '',
        status: ticket.status || 'todo',
        assignee_id: ticket.assignee_id || null,
        priority: ticket.priority || 'medium',
        escalation_level: ticket.escalation_level || 'L1',
        team_id: ticket.team_id || null
      });
      setShowDeleteConfirm(false);
      setInputText('');
      setCustomFieldValues(ticket.custom_fields || {});
      fetchNotes(ticket.id);
      fetchRelatedTickets(ticket.id);
      fetchCustomFields();
      fetchAssignmentOptions(ticket.id);
    }
  }, [ticket]);

  const fetchCustomFields = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/custom-fields?entity_type=ticket`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setCustomFields(data);
      }
    } catch (error) {
      console.error('Failed to fetch custom fields:', error);
    }
  };

  const fetchAssignmentOptions = async (ticketId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}/assignment-options`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setAssignmentOptions(data);
      }
    } catch (error) {
      console.error('Failed to fetch assignment options:', error);
    }
  };

  const handleEscalate = async (newLevel) => {
    if (!ticket || escalating) return;
    
    setEscalating(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/escalate`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ 
          escalation_level: newLevel,
          reason: `Escalated to ${newLevel}`
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        // Update form data with new escalation level and team
        setFormData(prev => ({
          ...prev,
          escalation_level: newLevel,
          team_id: data.assignment?.team_id || prev.team_id,
          assignee_id: data.assignment?.assignee_id || null
        }));
        // Refresh assignment options
        fetchAssignmentOptions(ticket.id);
        // Trigger parent refresh
        if (onUpdate) {
          onUpdate(ticket.id, { 
            escalation_level: newLevel,
            team_id: data.assignment?.team_id,
            assignee_id: data.assignment?.assignee_id
          });
        }
      }
    } catch (error) {
      console.error('Failed to escalate ticket:', error);
    } finally {
      setEscalating(false);
    }
  };

  const handleAssignToTeam = async (teamId) => {
    // When assigning to another team, find the team's escalation level and escalate
    const team = assignmentOptions?.other_teams?.find(t => t.team_id === teamId);
    if (team && team.escalation_level) {
      await handleEscalate(team.escalation_level);
    }
    setShowAssignDropdown(false);
  };

  const fetchRelatedTickets = async (ticketId) => {
    setLoadingRelated(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}/related`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setRelatedTickets(data);
      }
    } catch (error) {
      console.error('Failed to fetch related tickets:', error);
    } finally {
      setLoadingRelated(false);
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;
      // N for note, R for reply when not typing
      const activeElement = document.activeElement;
      const isTyping = activeElement?.isContentEditable || 
                       activeElement?.tagName === 'INPUT' || 
                       activeElement?.tagName === 'TEXTAREA';
      if (!isTyping) {
        if (e.key === 'n' || e.key === 'N') {
          setInputMode('note');
        }
        if (e.key === 'r' || e.key === 'R') {
          setInputMode('reply');
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

  const handleSubmitInput = async () => {
    // Strip HTML to check if there's actual content
    const plainText = stripHtml(inputText);
    if (!plainText.trim() || !ticket) return;
    
    setSubmitting(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ 
          content: inputText.trim(), 
          type: inputMode === 'reply' ? 'reply' : 'internal_note' 
        })
      });
      if (response.ok) {
        setInputText('');
        fetchNotes(ticket.id);
        // Scroll to bottom after adding
        setTimeout(() => {
          if (conversationRef.current) {
            conversationRef.current.scrollTop = conversationRef.current.scrollHeight;
          }
        }, 100);
      }
    } catch (error) {
      console.error('Failed to send:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSave = () => {
    if (ticket) {
      onUpdate(ticket.id, {
        ...formData,
        custom_fields: customFieldValues
      });
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

  // Build conversation thread: original ticket + notes/replies
  const conversationThread = [
    {
      type: 'original',
      sender: ticket.customer_name || ticket.created_by_name || 'Customer',
      senderEmail: ticket.customer_email || null,
      subject: ticket.title,
      content: ticket.description || '',
      timestamp: ticket.created_at
    },
    ...notes.map(note => ({
      type: note.type || 'internal_note',
      sender: note.author_name || 'Unknown',
      senderEmail: null,
      subject: null,
      content: note.content,
      timestamp: note.created_at
    }))
  ].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

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
        {/* Left Panel - Conversation */}
        <div className="flex-1 bg-card border-l border-border/40 flex flex-col min-w-0">
          {/* Header */}
          <div className="h-12 px-4 flex items-center justify-between border-b border-border/30 shrink-0 bg-background/50">
            <div className="flex items-center gap-2 min-w-0">
              <Mail size={15} className="text-primary shrink-0" />
              <span className="text-sm font-medium truncate">{ticket.title}</span>
              <span className="text-[11px] text-muted-foreground font-mono bg-secondary/40 px-1.5 py-0.5 rounded shrink-0">
                {ticket.ticket_id || `#${ticket.id?.slice(-8)}`}
              </span>
            </div>
            <div className="flex items-center gap-0.5 shrink-0">
              <button className="h-7 w-7 flex items-center justify-center rounded hover:bg-secondary/50 transition-colors" title="Star">
                <Star size={14} className="text-muted-foreground" />
              </button>
              <button className="h-7 w-7 flex items-center justify-center rounded hover:bg-secondary/50 transition-colors" title="More">
                <MoreHorizontal size={14} className="text-muted-foreground" />
              </button>
              <button
                onClick={onClose}
                className="h-7 w-7 flex items-center justify-center rounded hover:bg-secondary/50 transition-colors ml-1"
                data-testid="drawer-close-button"
                title="Close"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Conversation Thread - Scrollable */}
          <div ref={conversationRef} className="flex-1 overflow-y-auto p-4 space-y-3">
            {/* Recent Conversations from Same Customer */}
            {(relatedTickets.length > 0 || loadingRelated) && (
              <div className="mb-4">
                <button
                  onClick={() => setRelatedExpanded(!relatedExpanded)}
                  className="w-full flex items-center justify-between py-2 px-3 rounded-lg bg-secondary/20 border border-border/30 hover:bg-secondary/30 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Mail size={14} className="text-primary" />
                    <span className="text-xs font-medium">Recent Conversations</span>
                    {relatedTickets.length > 0 && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/20 text-primary">
                        {relatedTickets.length}
                      </span>
                    )}
                  </div>
                  {relatedExpanded ? (
                    <ChevronDown size={14} className="text-muted-foreground" />
                  ) : (
                    <ChevronRight size={14} className="text-muted-foreground" />
                  )}
                </button>
                
                {relatedExpanded && (
                  <div className="mt-2 space-y-1.5">
                    {loadingRelated ? (
                      <div className="flex items-center justify-center py-4">
                        <Loader2 size={16} className="animate-spin text-muted-foreground" />
                      </div>
                    ) : (
                      relatedTickets.map(related => (
                        <div
                          key={related.id || related.ticket_id}
                          className="flex items-center justify-between p-2.5 rounded-lg bg-secondary/10 border border-border/20 hover:bg-secondary/20 cursor-pointer transition-colors"
                          onClick={() => {
                            // Could navigate to the ticket or load it in the drawer
                            window.open(`/all-tickets?ticket=${related.ticket_id || related.id}`, '_blank');
                          }}
                        >
                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-medium truncate">{related.title}</p>
                            <p className="text-[10px] text-muted-foreground truncate">
                              {stripHtml(related.description)?.slice(0, 60)}...
                            </p>
                          </div>
                          <div className="text-right shrink-0 ml-2">
                            <p className="text-[10px] font-mono text-muted-foreground">
                              {related.ticket_id || `#${related.id?.slice(-6)}`}
                            </p>
                            <p className="text-[10px] text-muted-foreground">
                              {new Date(related.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            )}
            
            {/* Current Conversation */}
            {loadingNotes && conversationThread.length === 1 ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 size={24} className="animate-spin text-muted-foreground" />
              </div>
            ) : (
              conversationThread.map((msg, idx) => (
                <EmailMessage
                  key={idx}
                  type={msg.type}
                  sender={msg.sender}
                  senderEmail={msg.senderEmail}
                  subject={msg.subject}
                  content={msg.content}
                  timestamp={msg.timestamp}
                  isFirst={idx === 0}
                />
              ))
            )}
          </div>

          {/* Input Area - Fixed at bottom */}
          <div className="shrink-0 border-t border-border/30 bg-background p-3">
            {/* Mode Toggle */}
            <div className="flex items-center gap-1 mb-2">
              <button
                onClick={() => setInputMode('reply')}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
                  inputMode === 'reply' 
                    ? 'bg-primary/20 text-primary' 
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                }`}
                data-testid="mode-reply"
              >
                <Mail size={13} />
                <span>Reply</span>
                <span className="text-[10px] opacity-60 ml-0.5">R</span>
              </button>
              <button
                onClick={() => setInputMode('note')}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
                  inputMode === 'note' 
                    ? 'bg-amber-400/20 text-amber-400' 
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                }`}
                data-testid="mode-note"
              >
                <PenLine size={13} />
                <span>Note</span>
                <span className="text-[10px] opacity-60 ml-0.5">N</span>
              </button>
              
              <div className="flex-1" />
              
              <span className="text-[10px] text-muted-foreground/50 flex items-center gap-1">
                <Command size={10} />⌘+Enter to send
              </span>
              
              <button
                onClick={handleSubmitInput}
                disabled={submitting || !stripHtml(inputText).trim()}
                className={`h-7 px-3 flex items-center gap-1.5 rounded text-xs font-medium transition-colors ${
                  inputMode === 'note'
                    ? 'bg-amber-400/20 text-amber-400 hover:bg-amber-400/30'
                    : 'bg-primary/20 text-primary hover:bg-primary/30'
                } disabled:opacity-40 disabled:cursor-not-allowed`}
                data-testid="submit-input"
              >
                {submitting ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
                <span>Send</span>
              </button>
            </div>

            {/* Rich Text Editor */}
            <RichTextEditor
              value={inputText}
              onChange={setInputText}
              placeholder={inputMode === 'note' ? 'Add an internal note...' : 'Type your reply...'}
              mode={inputMode}
              onSubmit={handleSubmitInput}
              disabled={submitting}
            />
          </div>
        </div>

        {/* Right Panel - Details (~320px) */}
        <div className="w-72 bg-card border-l border-border/30 flex flex-col shrink-0">
          {/* Tabs */}
          <div className="h-12 px-4 flex items-center gap-4 border-b border-border/30 shrink-0">
            <button className="text-sm font-medium text-foreground relative pb-0.5">
              Details
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full" />
            </button>
          </div>

          {/* Details Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Escalation Level */}
            <div>
              <label className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <ArrowUpCircle size={11} />
                Escalation Level
              </label>
              <div className="flex gap-1">
                {ESCALATION_LEVELS.map(level => (
                  <button
                    key={level.value}
                    onClick={() => handleEscalate(level.value)}
                    disabled={escalating || formData.escalation_level === level.value}
                    className={`flex-1 h-8 px-2 text-[11px] font-medium rounded-md transition-colors ${
                      formData.escalation_level === level.value
                        ? `${level.color} text-white`
                        : 'bg-secondary/30 text-muted-foreground hover:bg-secondary/50'
                    } ${escalating ? 'opacity-50 cursor-not-allowed' : ''}`}
                    data-testid={`escalation-${level.value}`}
                  >
                    {escalating && formData.escalation_level !== level.value ? (
                      <Loader2 size={12} className="animate-spin mx-auto" />
                    ) : (
                      level.value
                    )}
                  </button>
                ))}
              </div>
              {assignmentOptions?.current_team && (
                <div className="flex items-center gap-1.5 mt-1.5 text-[10px] text-muted-foreground">
                  <Users size={10} />
                  <span>Team: {assignmentOptions.current_team.name}</span>
                </div>
              )}
            </div>

            {/* Assignee - Enhanced with team members and other teams */}
            <div className="relative">
              <label className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <UserCheck size={11} />
                Assignee
              </label>
              
              {/* Custom dropdown */}
              <button
                onClick={() => setShowAssignDropdown(!showAssignDropdown)}
                className="w-full h-8 px-2 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50 text-left flex items-center justify-between"
                data-testid="drawer-assignee-dropdown"
              >
                <span className={formData.assignee_id ? '' : 'text-muted-foreground'}>
                  {assignee ? assignee.name : 'Unassigned'}
                </span>
                <ChevronDown size={14} className="text-muted-foreground" />
              </button>

              {/* Dropdown menu */}
              {showAssignDropdown && (
                <div className="absolute z-50 w-full mt-1 bg-popover border border-border rounded-lg shadow-lg max-h-64 overflow-y-auto">
                  {/* Unassign option */}
                  <button
                    onClick={() => {
                      setFormData({ ...formData, assignee_id: null });
                      setShowAssignDropdown(false);
                    }}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-secondary/50 text-muted-foreground"
                  >
                    Unassigned
                  </button>
                  
                  {/* Team Members Section */}
                  {assignmentOptions?.team_members?.length > 0 && (
                    <>
                      <div className="px-3 py-1.5 text-[10px] font-medium uppercase text-muted-foreground bg-secondary/30 flex items-center gap-1.5">
                        <Users size={10} />
                        Team Members
                        {assignmentOptions.current_team && (
                          <span className="ml-auto opacity-60">({assignmentOptions.current_team.name})</span>
                        )}
                      </div>
                      {assignmentOptions.team_members.map(member => (
                        <button
                          key={member.user_id}
                          onClick={() => {
                            setFormData({ ...formData, assignee_id: member.user_id });
                            setShowAssignDropdown(false);
                          }}
                          className={`w-full px-3 py-2 text-left text-sm hover:bg-secondary/50 flex items-center justify-between ${
                            formData.assignee_id === member.user_id ? 'bg-primary/10 text-primary' : ''
                          }`}
                        >
                          <span className="flex items-center gap-2">
                            <div className="w-5 h-5 rounded-full bg-gradient-to-br from-primary/50 to-accent/50 flex items-center justify-center text-[9px] font-medium">
                              {member.name?.charAt(0).toUpperCase()}
                            </div>
                            {member.name}
                          </span>
                          {member.is_on_shift ? (
                            <span className="flex items-center gap-1 text-[10px] text-emerald-500">
                              <Clock size={10} />
                              On Shift
                            </span>
                          ) : (
                            <span className="text-[10px] text-muted-foreground/50">Off Shift</span>
                          )}
                        </button>
                      ))}
                    </>
                  )}
                  
                  {/* Other Teams Section */}
                  {assignmentOptions?.other_teams?.length > 0 && (
                    <>
                      <div className="px-3 py-1.5 text-[10px] font-medium uppercase text-muted-foreground bg-secondary/30 flex items-center gap-1.5">
                        <ArrowUpCircle size={10} />
                        Escalate to Team
                      </div>
                      {assignmentOptions.other_teams.map(team => (
                        <button
                          key={team.team_id}
                          onClick={() => handleAssignToTeam(team.team_id)}
                          className="w-full px-3 py-2 text-left text-sm hover:bg-secondary/50 flex items-center justify-between"
                        >
                          <span className="flex items-center gap-2">
                            <span className={`w-2 h-2 rounded-full ${
                              team.escalation_level === 'L1' ? 'bg-blue-500' :
                              team.escalation_level === 'L2' ? 'bg-amber-500' : 'bg-red-500'
                            }`} />
                            {team.name}
                            <span className="text-[10px] text-muted-foreground">({team.escalation_level})</span>
                          </span>
                          <span className="text-[10px] text-muted-foreground">
                            {team.on_shift_count} on shift
                          </span>
                        </button>
                      ))}
                    </>
                  )}
                  
                  {/* Fallback to all users if no assignment options */}
                  {!assignmentOptions && users.length > 0 && (
                    <>
                      <div className="px-3 py-1.5 text-[10px] font-medium uppercase text-muted-foreground bg-secondary/30">
                        All Users
                      </div>
                      {users.map(user => (
                        <button
                          key={user.id}
                          onClick={() => {
                            setFormData({ ...formData, assignee_id: user.id });
                            setShowAssignDropdown(false);
                          }}
                          className={`w-full px-3 py-2 text-left text-sm hover:bg-secondary/50 ${
                            formData.assignee_id === user.id ? 'bg-primary/10 text-primary' : ''
                          }`}
                        >
                          {user.name}
                        </button>
                      ))}
                    </>
                  )}
                </div>
              )}

              {assignee && (
                <div className="flex items-center gap-2 mt-1.5">
                  <div className="w-5 h-5 rounded-full bg-gradient-to-br from-primary/50 to-accent/50 flex items-center justify-center text-[9px] font-medium">
                    {assignee.name?.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-xs">{assignee.name}</span>
                </div>
              )}
            </div>

            {/* Status - Only show if assigned */}
            {formData.assignee_id && (
              <div>
                <label className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider mb-1.5 block">
                  Status
                </label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  className="w-full h-8 px-2 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                  data-testid="drawer-status-select"
                >
                  {STATUSES.map(status => (
                    <option key={status.value} value={status.value}>{status.label}</option>
                  ))}
                </select>
                <div className="flex items-center gap-1.5 mt-1.5">
                  <div className={`w-2 h-2 rounded-full ${statusConfig.color}`} />
                  <span className="text-xs">{statusConfig.label}</span>
                </div>
              </div>
            )}

            {/* Priority */}
            <div>
              <label className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider mb-1.5 block">
                Priority
              </label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                className="w-full h-8 px-2 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                data-testid="drawer-priority-select"
              >
                {PRIORITIES.map(priority => (
                  <option key={priority.value} value={priority.value}>{priority.label}</option>
                ))}
              </select>
              <div className="flex items-center gap-1.5 mt-1.5">
                <AlertCircle size={12} className={priorityConfig.color} />
                <span className={`text-xs ${priorityConfig.color}`}>{priorityConfig.label}</span>
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
                  <Link2 size={12} className="text-muted-foreground" />
                  <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Links</span>
                </div>
                {sectionsExpanded.links ? (
                  <ChevronDown size={12} className="text-muted-foreground" />
                ) : (
                  <ChevronRight size={12} className="text-muted-foreground" />
                )}
              </button>
              
              {sectionsExpanded.links && (
                <div className="mt-1.5 space-y-1">
                  <div className="flex items-center justify-between py-1 pl-4 text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-colors">
                    <span>Related tickets</span>
                    <span className="text-primary text-[10px]">+ Add</span>
                  </div>
                  <div className="flex items-center justify-between py-1 pl-4 text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-colors">
                    <span>External links</span>
                    <span className="text-primary text-[10px]">+ Add</span>
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
                  <Sparkles size={12} className="text-muted-foreground" />
                  <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Attributes</span>
                </div>
                {sectionsExpanded.attributes ? (
                  <ChevronDown size={12} className="text-muted-foreground" />
                ) : (
                  <ChevronRight size={12} className="text-muted-foreground" />
                )}
              </button>
              
              {sectionsExpanded.attributes && (
                <div className="mt-1.5 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">ID</span>
                    <span className="font-mono text-foreground/80 text-[10px]">
                      {ticket.ticket_id || ticket.id?.slice(-12)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Source</span>
                    <span className="capitalize text-foreground/80">{ticket.source || 'manual'}</span>
                  </div>
                  {ticket.customer_email && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Customer</span>
                      <span className="text-foreground/80 text-[10px] truncate max-w-[120px]">{ticket.customer_email}</span>
                    </div>
                  )}
                  {ticket.domain && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Domain</span>
                      <span className="text-foreground/80">{ticket.domain}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Created</span>
                    <span className="text-foreground/80 text-[10px]">
                      {new Date(ticket.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {ticket.tags && ticket.tags.length > 0 && (
                    <div className="flex items-start justify-between">
                      <span className="text-muted-foreground">Tags</span>
                      <div className="flex flex-wrap gap-1 justify-end max-w-[100px]">
                        {ticket.tags.map((tag, i) => (
                          <span key={i} className="text-[9px] px-1 py-0.5 rounded bg-primary/20 text-primary">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Custom Fields Section */}
            {customFields.length > 0 && (
              <>
                {/* Divider */}
                <div className="h-px bg-border/30" />

                <div>
                  <button
                    onClick={() => toggleSection('customFields')}
                    className="w-full flex items-center justify-between py-1 group"
                  >
                    <div className="flex items-center gap-2">
                      <Settings size={12} className="text-muted-foreground" />
                      <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Custom Fields</span>
                    </div>
                    {sectionsExpanded.customFields ? (
                      <ChevronDown size={12} className="text-muted-foreground" />
                    ) : (
                      <ChevronRight size={12} className="text-muted-foreground" />
                    )}
                  </button>
                  
                  {sectionsExpanded.customFields && (
                    <div className="mt-2 space-y-3">
                      {customFields.map(field => (
                        <div key={field.field_id}>
                          <label className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider mb-1.5 block">
                            {field.name}
                            {field.required && <span className="text-destructive ml-0.5">*</span>}
                          </label>
                          {field.field_type === 'text' && (
                            <input
                              type="text"
                              value={customFieldValues[field.field_id] || ''}
                              onChange={(e) => setCustomFieldValues(prev => ({ 
                                ...prev, 
                                [field.field_id]: e.target.value 
                              }))}
                              className="w-full h-8 px-2 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                              placeholder={field.description || `Enter ${field.name.toLowerCase()}`}
                              data-testid={`custom-field-${field.field_id}`}
                            />
                          )}
                          {field.field_type === 'number' && (
                            <input
                              type="number"
                              value={customFieldValues[field.field_id] || ''}
                              onChange={(e) => setCustomFieldValues(prev => ({ 
                                ...prev, 
                                [field.field_id]: e.target.value 
                              }))}
                              className="w-full h-8 px-2 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                              placeholder={field.description || `Enter ${field.name.toLowerCase()}`}
                              data-testid={`custom-field-${field.field_id}`}
                            />
                          )}
                          {field.field_type === 'select' && (
                            <select
                              value={customFieldValues[field.field_id] || ''}
                              onChange={(e) => setCustomFieldValues(prev => ({ 
                                ...prev, 
                                [field.field_id]: e.target.value 
                              }))}
                              className="w-full h-8 px-2 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                              data-testid={`custom-field-${field.field_id}`}
                            >
                              <option value="">Select {field.name.toLowerCase()}</option>
                              {field.options?.map((opt, idx) => (
                                <option key={idx} value={opt}>{opt}</option>
                              ))}
                            </select>
                          )}
                          {field.field_type === 'date' && (
                            <input
                              type="date"
                              value={customFieldValues[field.field_id] || ''}
                              onChange={(e) => setCustomFieldValues(prev => ({ 
                                ...prev, 
                                [field.field_id]: e.target.value 
                              }))}
                              className="w-full h-8 px-2 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                              data-testid={`custom-field-${field.field_id}`}
                            />
                          )}
                          {field.field_type === 'boolean' && (
                            <label className="flex items-center gap-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={customFieldValues[field.field_id] || false}
                                onChange={(e) => setCustomFieldValues(prev => ({ 
                                  ...prev, 
                                  [field.field_id]: e.target.checked 
                                }))}
                                className="w-4 h-4 rounded border-border text-primary focus:ring-primary/50"
                                data-testid={`custom-field-${field.field_id}`}
                              />
                              <span className="text-xs text-foreground/80">
                                {field.description || 'Yes'}
                              </span>
                            </label>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Footer Actions */}
          <div className="shrink-0 px-3 py-2.5 border-t border-border/30 bg-background">
            {!showDeleteConfirm ? (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="h-7 px-2 flex items-center gap-1 text-[11px] text-destructive hover:bg-destructive/10 rounded transition-colors"
                  data-testid="drawer-delete-button"
                >
                  <Trash2 size={12} />
                  <span>Delete</span>
                </button>
                <button
                  onClick={handleSave}
                  className="flex-1 h-7 px-2 flex items-center justify-center gap-1 text-[11px] font-medium bg-primary text-primary-foreground rounded hover:bg-primary/90 transition-colors"
                  data-testid="drawer-save-button"
                >
                  <Save size={12} />
                  <span>Save</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 h-7 px-2 text-[11px] border border-border/40 rounded hover:bg-secondary/50 transition-colors"
                  data-testid="drawer-delete-cancel-button"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  className="flex-1 h-7 px-2 text-[11px] font-medium bg-destructive text-destructive-foreground rounded hover:bg-destructive/90 transition-colors"
                  data-testid="drawer-delete-confirm-button"
                >
                  Delete
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
