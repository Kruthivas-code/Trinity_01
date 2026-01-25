import React, { useState, useEffect, useRef } from 'react';
import DOMPurify from 'dompurify';
import { 
  X, Save, Trash2, Send, ChevronDown, ChevronRight,
  Loader2, Star, MoreHorizontal, Mail, AlertCircle, 
  Sparkles, PenLine, Command, Link2, Settings, Users,
  Clock, ArrowUpCircle, UserCheck, AtSign, Copy, Printer,
  BellOff, Merge, ExternalLink, Split, Link, FileText, 
  Tag, Bookmark, Download, UserPlus, Scissors
} from 'lucide-react';
import RichTextEditor from './RichTextEditor';
import MentionInput, { renderTextWithMentions } from './MentionInput';

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
const EmailMessage = ({ type, sender, senderEmail, subject, content, timestamp, isFirst, isAgentMessage }) => {
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
  const isReply = type === 'reply';
  const isCustomerMessage = type === 'original' || type === 'customer_reply';
  const isAgent = isAgentMessage || isReply || isNote;
  
  // Render HTML content safely, with mention support for notes
  const renderContent = (html) => {
    if (!html) return <span className="text-muted-foreground/50 italic">No content</span>;
    
    // For internal notes, render mentions
    if (isNote) {
      // Check for mention format: @[Name](id)
      const hasMentions = /@\[([^\]]+)\]\(([^)]+)\)/.test(html);
      if (hasMentions) {
        return (
          <p className="whitespace-pre-wrap">
            {renderTextWithMentions(html)}
          </p>
        );
      }
    }
    
    // Check if content is HTML or plain text
    const hasHtml = /<[^>]+>/.test(html);
    if (hasHtml) {
      // Sanitize HTML to prevent XSS attacks
      const sanitizedHtml = DOMPurify.sanitize(html, {
        ALLOWED_TAGS: ['p', 'br', 'b', 'i', 'u', 'strong', 'em', 'a', 'ul', 'ol', 'li', 
                       'blockquote', 'pre', 'code', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                       'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'span', 'div'],
        ALLOWED_ATTR: ['href', 'src', 'alt', 'class', 'style', 'target', 'rel'],
        ALLOW_DATA_ATTR: false
      });
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
          dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
        />
      );
    }
    return <p className="whitespace-pre-wrap">{html}</p>;
  };

  // Determine styling based on message type
  const getMessageStyles = () => {
    if (isNote) {
      // Internal note - centered with amber accent
      return {
        container: 'bg-amber-500/10 border border-amber-400/30 rounded-lg',
        alignment: 'mx-auto max-w-[90%]',
        avatar: 'bg-amber-400/20 text-amber-400',
        badge: 'bg-amber-400/20 text-amber-400'
      };
    }
    if (isAgent || isReply) {
      // Agent reply - right aligned with primary/teal accent
      return {
        container: 'bg-primary/10 border border-primary/20 rounded-lg rounded-tr-sm',
        alignment: 'ml-auto max-w-[85%]',
        avatar: 'bg-primary/30 text-primary',
        badge: 'bg-primary/20 text-primary'
      };
    }
    // Customer message - left aligned with neutral styling
    return {
      container: 'bg-secondary/30 border border-border/40 rounded-lg rounded-tl-sm',
      alignment: 'mr-auto max-w-[85%]',
      avatar: 'bg-slate-500/30 text-slate-300',
      badge: null
    };
  };

  const styles = getMessageStyles();
  
  return (
    <div className={`${styles.alignment}`}>
      <div className={`${styles.container} p-4`}>
        {/* Message Header */}
        <div className={`flex items-start justify-between mb-3 ${isAgent && !isNote ? 'flex-row-reverse' : ''}`}>
          <div className={`flex items-start gap-3 ${isAgent && !isNote ? 'flex-row-reverse text-right' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium shrink-0 ${styles.avatar}`}>
              {sender?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="min-w-0">
              <div className={`flex items-center gap-2 flex-wrap ${isAgent && !isNote ? 'justify-end' : ''}`}>
                <span className="font-medium text-sm">{sender || 'Unknown'}</span>
                {isNote && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-400/20 text-amber-400 font-medium">
                    Internal Note
                  </span>
                )}
                {isReply && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/20 text-primary font-medium">
                    Agent Reply
                  </span>
                )}
                {isCustomerMessage && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-500/20 text-slate-400 font-medium">
                    Customer
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
        
        {/* Message Body */}
        <div className={`text-sm text-foreground/90 leading-relaxed ${isNote ? 'pl-11' : isAgent ? 'pr-11' : 'pl-11'}`}>
          {renderContent(content)}
        </div>
      </div>
    </div>
  );
};

const TicketDrawer = ({ ticket, users, currentUser, isOpen, onClose, onUpdate, onDelete }) => {
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
  const [inputMentions, setInputMentions] = useState([]);
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
  
  // Star and More menu state
  const [isStarred, setIsStarred] = useState(false);
  const [showMoreMenu, setShowMoreMenu] = useState(false);
  const [snoozed, setSnoozed] = useState(false);
  
  // Modal states for new features
  const [showMergeModal, setShowMergeModal] = useState(false);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [showSplitModal, setShowSplitModal] = useState(false);
  const [showFeatureRequestModal, setShowFeatureRequestModal] = useState(false);
  const [splitMessageIndex, setSplitMessageIndex] = useState(null);
  
  // Linked tickets
  const [linkedTickets, setLinkedTickets] = useState([]);
  
  // Tags state
  const [ticketTags, setTicketTags] = useState([]);
  const [tagInput, setTagInput] = useState('');
  const [showTagDropdown, setShowTagDropdown] = useState(false);
  const [availableTags, setAvailableTags] = useState([]);
  const [loadingTags, setLoadingTags] = useState(false);
  
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
      setIsStarred(ticket.is_starred || false);
      setSnoozed(ticket.snoozed || false);
      setShowMoreMenu(false);
      setLinkedTickets(ticket.linked_tickets || []);
      fetchNotes(ticket.id);
      fetchRelatedTickets(ticket.id);
      fetchCustomFields();
      fetchAssignmentOptions(ticket.id);
    }
  }, [ticket]);

  // Handle assignment change - persist to backend
  const handleAssign = async (userId) => {
    setFormData({ ...formData, assignee_id: userId });
    setShowAssignDropdown(false);
    
    if (onUpdate && ticket) {
      await onUpdate(ticket.id, { assignee_id: userId });
    }
  };

  // Assign to current user
  const handleAssignToMe = async () => {
    const myUserId = currentUser?.user_id || currentUser?.id;
    if (myUserId) {
      await handleAssign(myUserId);
    }
  };

  // Handle star toggle
  const handleToggleStar = async () => {
    if (!ticket) return;
    const newStarred = !isStarred;
    setIsStarred(newStarred);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ is_starred: newStarred })
      });
      
      if (response.ok) {
        // Silent operation
      } else {
        setIsStarred(!newStarred); // Revert on error
      }
    } catch (error) {
      setIsStarred(!newStarred);
      console.error('Operation failed');
    }
  };

  // Handle copy ticket URL
  const handleCopyLink = () => {
    const url = `${window.location.origin}/all-tickets?ticket=${ticket.ticket_id || ticket.id}`;
    navigator.clipboard.writeText(url);
    // Silent operation
    setShowMoreMenu(false);
  };

  // Handle snooze toggle
  const handleToggleSnooze = async () => {
    if (!ticket) return;
    const newSnoozed = !snoozed;
    setSnoozed(newSnoozed);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ snoozed: newSnoozed })
      });
      
      if (response.ok) {
        // Silent operation
      } else {
        setSnoozed(!newSnoozed);
      }
    } catch (error) {
      setSnoozed(!newSnoozed);
      console.error('Operation failed');
    }
    setShowMoreMenu(false);
  };

  // Handle print ticket
  const handlePrint = () => {
    window.print();
    setShowMoreMenu(false);
  };

  // Handle open in new tab
  const handleOpenInNewTab = () => {
    const url = `${window.location.origin}/all-tickets?ticket=${ticket.ticket_id || ticket.id}`;
    window.open(url, '_blank');
    setShowMoreMenu(false);
  };

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
          type: inputMode === 'reply' ? 'reply' : 'internal_note',
          mentions: inputMentions
        })
      });
      if (response.ok) {
        setInputText('');
        setInputMentions([]);
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
      timestamp: ticket.created_at,
      isAgentMessage: false // Customer's original message
    },
    ...notes.map(note => ({
      type: note.type || 'internal_note',
      sender: note.author_name || 'Unknown',
      senderEmail: null,
      subject: null,
      content: note.content,
      timestamp: note.created_at,
      isAgentMessage: true // All notes/replies are from agents
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
              {snoozed && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-400/20 text-amber-400 font-medium">
                  Snoozed
                </span>
              )}
            </div>
            <div className="flex items-center gap-0.5 shrink-0">
              <button 
                onClick={handleToggleStar}
                className="h-7 w-7 flex items-center justify-center rounded hover:bg-secondary/50 transition-colors" 
                title={isStarred ? "Unstar ticket" : "Star ticket"}
                data-testid="drawer-star-button"
              >
                <Star 
                  size={14} 
                  className={isStarred ? "text-amber-400 fill-amber-400" : "text-muted-foreground"} 
                />
              </button>
              <div className="relative">
                <button 
                  onClick={() => setShowMoreMenu(!showMoreMenu)}
                  className="h-7 w-7 flex items-center justify-center rounded hover:bg-secondary/50 transition-colors" 
                  title="More options"
                  data-testid="drawer-more-button"
                >
                  <MoreHorizontal size={14} className="text-muted-foreground" />
                </button>
                
                {/* More options dropdown */}
                {showMoreMenu && (
                  <div className="absolute right-0 top-8 w-48 bg-popover border border-border rounded-lg shadow-xl z-50 py-1">
                    <button
                      onClick={handleCopyLink}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                      data-testid="more-copy-link"
                    >
                      <Copy size={14} className="text-muted-foreground" />
                      Copy link
                    </button>
                    <button
                      onClick={handleOpenInNewTab}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                      data-testid="more-open-new-tab"
                    >
                      <ExternalLink size={14} className="text-muted-foreground" />
                      Open in new tab
                    </button>
                    <button
                      onClick={handlePrint}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                      data-testid="more-print"
                    >
                      <Printer size={14} className="text-muted-foreground" />
                      Print ticket
                    </button>
                    <button
                      onClick={async () => {
                        // Export as PDF (using print dialog)
                        window.print();
                        setShowMoreMenu(false);
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                      data-testid="more-export-pdf"
                    >
                      <Download size={14} className="text-muted-foreground" />
                      Export as PDF
                    </button>
                    
                    <div className="h-px bg-border my-1" />
                    
                    <button
                      onClick={handleToggleSnooze}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                      data-testid="more-snooze"
                    >
                      <BellOff size={14} className={snoozed ? "text-amber-400" : "text-muted-foreground"} />
                      {snoozed ? 'Unsnooze ticket' : 'Snooze ticket'}
                    </button>
                    
                    <button
                      onClick={handleAssignToMe}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                      data-testid="more-assign-me"
                    >
                      <UserPlus size={14} className="text-muted-foreground" />
                      Assign to me
                    </button>
                    
                    <div className="h-px bg-border my-1" />
                    
                    <button
                      onClick={() => {
                        setShowMergeModal(true);
                        setShowMoreMenu(false);
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                      data-testid="more-merge"
                    >
                      <Merge size={14} className="text-muted-foreground" />
                      Merge with ticket...
                    </button>
                    
                    <button
                      onClick={() => {
                        setShowLinkModal(true);
                        setShowMoreMenu(false);
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                      data-testid="more-link"
                    >
                      <Link size={14} className="text-muted-foreground" />
                      Link to ticket...
                    </button>
                    
                    <button
                      onClick={() => {
                        setSplitMessageIndex(null);
                        setShowSplitModal(true);
                        setShowMoreMenu(false);
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                      data-testid="more-split"
                    >
                      <Scissors size={14} className="text-muted-foreground" />
                      Split ticket...
                    </button>
                    
                    <div className="h-px bg-border my-1" />
                    
                    <button
                      onClick={() => {
                        setShowFeatureRequestModal(true);
                        setShowMoreMenu(false);
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                      data-testid="more-feature-request"
                    >
                      <Bookmark size={14} className="text-muted-foreground" />
                      Link to Feature Request...
                    </button>
                    
                    <div className="h-px bg-border my-1" />
                    
                    <button
                      onClick={() => {
                        setShowDeleteConfirm(true);
                        setShowMoreMenu(false);
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-red-500/10 transition-colors text-left text-red-400"
                      data-testid="more-delete"
                    >
                      <Trash2 size={14} />
                      Delete ticket...
                    </button>
                  </div>
                )}
              </div>
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
                  isAgentMessage={msg.isAgentMessage}
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

            {/* Rich Text Editor for Reply / MentionInput for Notes */}
            {inputMode === 'note' ? (
              <MentionInput
                value={inputText}
                onChange={(text, mentions) => {
                  setInputText(text);
                  setInputMentions(mentions);
                }}
                onSubmit={handleSubmitInput}
                placeholder="Add an internal note... Use @ to mention someone"
                disabled={submitting}
                rows={4}
              />
            ) : (
              <RichTextEditor
                value={inputText}
                onChange={setInputText}
                placeholder="Type your reply..."
                mode={inputMode}
                onSubmit={handleSubmitInput}
                disabled={submitting}
              />
            )}
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
                      {/* Assign to me - quick action */}
                      {currentUser && !assignmentOptions.team_members.find(m => m.user_id === (currentUser.user_id || currentUser.id)) && (
                        <button
                          onClick={handleAssignToMe}
                          className="w-full px-3 py-2 text-left text-sm hover:bg-primary/10 flex items-center gap-2 text-primary border-b border-border/30"
                        >
                          <UserPlus size={14} />
                          <span>Assign to me</span>
                        </button>
                      )}
                      {assignmentOptions.team_members.map(member => (
                        <button
                          key={member.user_id}
                          onClick={() => handleAssign(member.user_id)}
                          className={`w-full px-3 py-2 text-left text-sm hover:bg-secondary/50 flex items-center justify-between ${
                            formData.assignee_id === member.user_id ? 'bg-primary/10 text-primary' : ''
                          }`}
                        >
                          <span className="flex items-center gap-2">
                            <div className="w-5 h-5 rounded-full bg-gradient-to-br from-primary/50 to-accent/50 flex items-center justify-center text-[9px] font-medium">
                              {member.name?.charAt(0).toUpperCase()}
                            </div>
                            {member.name}
                            {member.user_id === (currentUser?.user_id || currentUser?.id) && (
                              <span className="text-[10px] text-primary">(me)</span>
                            )}
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
                      {/* Assign to me - quick action */}
                      <button
                        onClick={handleAssignToMe}
                        className="w-full px-3 py-2 text-left text-sm hover:bg-primary/10 flex items-center gap-2 text-primary border-b border-border/30"
                      >
                        <UserPlus size={14} />
                        <span>Assign to me</span>
                      </button>
                      {users.map(user => (
                        <button
                          key={user.id || user.user_id}
                          onClick={() => handleAssign(user.id || user.user_id)}
                          className={`w-full px-3 py-2 text-left text-sm hover:bg-secondary/50 flex items-center gap-2 ${
                            formData.assignee_id === (user.id || user.user_id) ? 'bg-primary/10 text-primary' : ''
                          }`}
                        >
                          <div className="w-5 h-5 rounded-full bg-gradient-to-br from-primary/50 to-accent/50 flex items-center justify-center text-[9px] font-medium">
                            {user.name?.charAt(0).toUpperCase()}
                          </div>
                          {user.name}
                          {(user.id || user.user_id) === (currentUser?.user_id || currentUser?.id) && (
                            <span className="text-[10px] text-primary">(me)</span>
                          )}
                        </button>
                      ))}
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Status - Only show if assigned */}
            {formData.assignee_id && (
              <div>
                <label className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <div className={`w-2 h-2 rounded-full ${statusConfig.color}`} />
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
              </div>
            )}

            {/* Priority */}
            <div>
              <label className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <AlertCircle size={11} className={priorityConfig.color} />
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
      
      {/* Merge Ticket Modal */}
      {showMergeModal && (
        <MergeTicketModal
          ticket={ticket}
          onClose={() => setShowMergeModal(false)}
          onMerge={async (targetTicketId) => {
            try {
              const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/merge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ target_ticket_id: targetTicketId })
              });
              if (response.ok) {
                setShowMergeModal(false);
                onClose();
              }
            } catch (error) {
              console.error('Merge failed:', error);
            }
          }}
        />
      )}
      
      {/* Link Ticket Modal */}
      {showLinkModal && (
        <LinkTicketModal
          ticket={ticket}
          linkedTickets={linkedTickets}
          onClose={() => setShowLinkModal(false)}
          onLink={async (targetTicketId, linkType) => {
            try {
              const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/link`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ target_ticket_id: targetTicketId, link_type: linkType })
              });
              if (response.ok) {
                const data = await response.json();
                setLinkedTickets(data.linked_tickets || []);
                setShowLinkModal(false);
              }
            } catch (error) {
              console.error('Link failed:', error);
            }
          }}
          onUnlink={async (targetTicketId) => {
            try {
              const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/unlink/${targetTicketId}`, {
                method: 'DELETE',
                credentials: 'include'
              });
              if (response.ok) {
                setLinkedTickets(linkedTickets.filter(t => t.ticket_id !== targetTicketId));
              }
            } catch (error) {
              console.error('Unlink failed:', error);
            }
          }}
        />
      )}
      
      {/* Split Ticket Modal */}
      {showSplitModal && (
        <SplitTicketModal
          ticket={ticket}
          notes={notes}
          splitMessageIndex={splitMessageIndex}
          onClose={() => setShowSplitModal(false)}
          onSplit={async (splitIndex, newTicketTitle) => {
            try {
              const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/split`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ split_at_index: splitIndex, new_ticket_title: newTicketTitle })
              });
              if (response.ok) {
                setShowSplitModal(false);
                // Refresh the current ticket
                onUpdate && onUpdate(ticket.id, {});
              }
            } catch (error) {
              console.error('Split failed:', error);
            }
          }}
        />
      )}
      
      {/* Feature Request Modal */}
      {showFeatureRequestModal && (
        <FeatureRequestModal
          ticket={ticket}
          onClose={() => setShowFeatureRequestModal(false)}
          onLink={async (featureRequestId) => {
            try {
              const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/feature-request`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ feature_request_id: featureRequestId })
              });
              if (response.ok) {
                setShowFeatureRequestModal(false);
              }
            } catch (error) {
              console.error('Link to feature request failed:', error);
            }
          }}
        />
      )}
    </>
  );
};

// Merge Ticket Modal Component
const MergeTicketModal = ({ ticket, onClose, onMerge }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState(null);

  const searchTickets = async (query) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/search?q=${encodeURIComponent(query)}&types=tickets`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setSearchResults((data.tickets || []).filter(t => t.ticket_id !== ticket.ticket_id).slice(0, 10));
      }
    } catch (error) {
      console.error('Search failed:', error);
    }
    setLoading(false);
  };

  useEffect(() => {
    const timer = setTimeout(() => searchTickets(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg glass rounded-xl border border-border/60 shadow-2xl">
        <div className="p-4 border-b border-border/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Merge size={18} className="text-primary" />
              <h3 className="text-base font-semibold">Merge Ticket</h3>
            </div>
            <button onClick={onClose} className="h-8 w-8 flex items-center justify-center rounded hover:bg-secondary/50">
              <X size={18} />
            </button>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Merge <span className="text-foreground font-medium">{ticket.ticket_id}</span> into another ticket. All messages will be moved.
          </p>
        </div>
        
        <div className="p-4 space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Search for target ticket</label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by ticket ID, title, or content..."
              className="w-full h-10 px-3 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              autoFocus
            />
          </div>
          
          <div className="max-h-64 overflow-y-auto space-y-1">
            {loading && (
              <div className="flex items-center justify-center py-4">
                <Loader2 size={20} className="animate-spin text-muted-foreground" />
              </div>
            )}
            {!loading && searchResults.map(result => (
              <button
                key={result.ticket_id}
                onClick={() => setSelectedTicket(result)}
                className={`w-full p-3 rounded-lg text-left transition-colors ${
                  selectedTicket?.ticket_id === result.ticket_id 
                    ? 'bg-primary/20 border border-primary/40' 
                    : 'bg-secondary/30 hover:bg-secondary/50 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-muted-foreground">{result.ticket_id}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                    result.status === 'resolved' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-500/20 text-blue-400'
                  }`}>{result.status}</span>
                </div>
                <p className="text-sm font-medium truncate mt-1">{result.title}</p>
              </button>
            ))}
            {!loading && searchQuery && searchResults.length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-4">No tickets found</p>
            )}
          </div>
        </div>
        
        <div className="p-4 border-t border-border/40 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="h-9 px-4 text-sm rounded-lg border border-border/40 hover:bg-secondary/50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => selectedTicket && onMerge(selectedTicket.ticket_id)}
            disabled={!selectedTicket}
            className="h-9 px-4 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Merge into {selectedTicket?.ticket_id || '...'}
          </button>
        </div>
      </div>
    </div>
  );
};

// Link Ticket Modal Component
const LinkTicketModal = ({ ticket, linkedTickets, onClose, onLink, onUnlink }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [linkType, setLinkType] = useState('related'); // related, blocks, blocked_by, duplicates

  const linkTypes = [
    { value: 'related', label: 'Related to' },
    { value: 'blocks', label: 'Blocks' },
    { value: 'blocked_by', label: 'Blocked by' },
    { value: 'duplicates', label: 'Duplicates' },
  ];

  const searchTickets = async (query) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/search?q=${encodeURIComponent(query)}&types=tickets`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        const existingLinks = linkedTickets.map(t => t.ticket_id);
        setSearchResults((data.tickets || []).filter(t => 
          t.ticket_id !== ticket.ticket_id && !existingLinks.includes(t.ticket_id)
        ).slice(0, 10));
      }
    } catch (error) {
      console.error('Search failed:', error);
    }
    setLoading(false);
  };

  useEffect(() => {
    const timer = setTimeout(() => searchTickets(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg glass rounded-xl border border-border/60 shadow-2xl">
        <div className="p-4 border-b border-border/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Link size={18} className="text-primary" />
              <h3 className="text-base font-semibold">Link Tickets</h3>
            </div>
            <button onClick={onClose} className="h-8 w-8 flex items-center justify-center rounded hover:bg-secondary/50">
              <X size={18} />
            </button>
          </div>
        </div>
        
        <div className="p-4 space-y-4">
          {/* Existing links */}
          {linkedTickets.length > 0 && (
            <div>
              <label className="text-sm font-medium mb-2 block">Linked Tickets</label>
              <div className="space-y-1">
                {linkedTickets.map(link => (
                  <div key={link.ticket_id} className="flex items-center justify-between p-2 rounded-lg bg-secondary/30">
                    <div>
                      <span className="text-xs text-muted-foreground">{link.link_type}</span>
                      <p className="text-sm font-medium">{link.ticket_id} - {link.title}</p>
                    </div>
                    <button 
                      onClick={() => onUnlink(link.ticket_id)}
                      className="h-7 w-7 flex items-center justify-center rounded hover:bg-red-500/20 text-red-400"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Link type selector */}
          <div>
            <label className="text-sm font-medium mb-2 block">Link Type</label>
            <div className="flex flex-wrap gap-1">
              {linkTypes.map(type => (
                <button
                  key={type.value}
                  onClick={() => setLinkType(type.value)}
                  className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
                    linkType === type.value ? 'bg-primary/20 text-primary' : 'bg-secondary/50 hover:bg-secondary/70'
                  }`}
                >
                  {type.label}
                </button>
              ))}
            </div>
          </div>
          
          {/* Search */}
          <div>
            <label className="text-sm font-medium mb-2 block">Search ticket to link</label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by ticket ID or title..."
              className="w-full h-10 px-3 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          
          <div className="max-h-48 overflow-y-auto space-y-1">
            {loading && (
              <div className="flex items-center justify-center py-4">
                <Loader2 size={20} className="animate-spin text-muted-foreground" />
              </div>
            )}
            {!loading && searchResults.map(result => (
              <button
                key={result.ticket_id}
                onClick={() => onLink(result.ticket_id, linkType)}
                className="w-full p-2 rounded-lg text-left bg-secondary/30 hover:bg-secondary/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-muted-foreground">{result.ticket_id}</span>
                </div>
                <p className="text-sm truncate">{result.title}</p>
              </button>
            ))}
          </div>
        </div>
        
        <div className="p-4 border-t border-border/40 flex justify-end">
          <button
            onClick={onClose}
            className="h-9 px-4 text-sm rounded-lg border border-border/40 hover:bg-secondary/50 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};

// Split Ticket Modal Component
const SplitTicketModal = ({ ticket, notes, splitMessageIndex, onClose, onSplit }) => {
  const [selectedIndex, setSelectedIndex] = useState(splitMessageIndex);
  const [newTitle, setNewTitle] = useState('');

  const messages = [
    { type: 'original', content: ticket.description, index: 0 },
    ...notes.map((n, i) => ({ ...n, index: i + 1 }))
  ];

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-2xl glass rounded-xl border border-border/60 shadow-2xl max-h-[80vh] flex flex-col">
        <div className="p-4 border-b border-border/40 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Scissors size={18} className="text-primary" />
              <h3 className="text-base font-semibold">Split Ticket</h3>
            </div>
            <button onClick={onClose} className="h-8 w-8 flex items-center justify-center rounded hover:bg-secondary/50">
              <X size={18} />
            </button>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Select where to split. Messages after this point will move to a new ticket.
          </p>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {messages.map((msg, idx) => (
            <div key={idx} className="relative">
              {idx > 0 && (
                <button
                  onClick={() => setSelectedIndex(idx)}
                  className={`absolute -top-2 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium transition-colors ${
                    selectedIndex === idx 
                      ? 'bg-red-500 text-white' 
                      : 'bg-secondary/50 text-muted-foreground hover:bg-red-500/20 hover:text-red-400'
                  }`}
                >
                  <Scissors size={10} />
                  Split here
                </button>
              )}
              <div className={`p-3 rounded-lg border ${
                selectedIndex !== null && idx >= selectedIndex 
                  ? 'bg-amber-500/10 border-amber-500/30' 
                  : 'bg-secondary/30 border-border/30'
              }`}>
                <div className="text-[10px] text-muted-foreground mb-1">
                  {msg.type === 'original' ? 'Original Message' : msg.type === 'internal_note' ? 'Internal Note' : 'Reply'}
                </div>
                <p className="text-sm line-clamp-2">{msg.content || msg.text}</p>
              </div>
            </div>
          ))}
        </div>
        
        {selectedIndex !== null && (
          <div className="p-4 border-t border-border/40 space-y-3 shrink-0">
            <div className="flex items-center gap-2 text-sm text-amber-400">
              <AlertCircle size={14} />
              <span>{messages.length - selectedIndex} message(s) will move to the new ticket</span>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">New ticket title</label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder={`Split from ${ticket.ticket_id}`}
                className="w-full h-10 px-3 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>
        )}
        
        <div className="p-4 border-t border-border/40 flex justify-end gap-2 shrink-0">
          <button
            onClick={onClose}
            className="h-9 px-4 text-sm rounded-lg border border-border/40 hover:bg-secondary/50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onSplit(selectedIndex, newTitle || `Split from ${ticket.ticket_id}`)}
            disabled={selectedIndex === null}
            className="h-9 px-4 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Split Ticket
          </button>
        </div>
      </div>
    </div>
  );
};

// Feature Request Modal Component
const FeatureRequestModal = ({ ticket, onClose, onLink }) => {
  const [featureRequests, setFeatureRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateNew, setShowCreateNew] = useState(false);
  const [newFeatureTitle, setNewFeatureTitle] = useState('');
  const [newFeatureDescription, setNewFeatureDescription] = useState('');

  useEffect(() => {
    fetchFeatureRequests();
  }, []);

  const fetchFeatureRequests = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/feature-requests`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setFeatureRequests(data);
      }
    } catch (error) {
      console.error('Failed to fetch feature requests:', error);
    }
    setLoading(false);
  };

  const createAndLink = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/feature-requests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ 
          title: newFeatureTitle, 
          description: newFeatureDescription,
          linked_ticket_id: ticket.id
        })
      });
      if (response.ok) {
        const data = await response.json();
        onLink(data.feature_request_id);
      }
    } catch (error) {
      console.error('Failed to create feature request:', error);
    }
  };

  const filteredRequests = featureRequests.filter(fr => 
    fr.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    fr.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg glass rounded-xl border border-border/60 shadow-2xl">
        <div className="p-4 border-b border-border/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bookmark size={18} className="text-primary" />
              <h3 className="text-base font-semibold">Link to Feature Request</h3>
            </div>
            <button onClick={onClose} className="h-8 w-8 flex items-center justify-center rounded hover:bg-secondary/50">
              <X size={18} />
            </button>
          </div>
        </div>
        
        <div className="p-4 space-y-4">
          {!showCreateNew ? (
            <>
              <div>
                <label className="text-sm font-medium mb-2 block">Search existing feature requests</label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search..."
                  className="w-full h-10 px-3 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              
              <div className="max-h-64 overflow-y-auto space-y-1">
                {loading && (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 size={20} className="animate-spin text-muted-foreground" />
                  </div>
                )}
                {!loading && filteredRequests.map(fr => (
                  <button
                    key={fr.feature_request_id}
                    onClick={() => onLink(fr.feature_request_id)}
                    className="w-full p-3 rounded-lg text-left bg-secondary/30 hover:bg-secondary/50 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                        fr.status === 'planned' ? 'bg-blue-500/20 text-blue-400' :
                        fr.status === 'in_progress' ? 'bg-amber-500/20 text-amber-400' :
                        fr.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' :
                        'bg-secondary text-muted-foreground'
                      }`}>{fr.status}</span>
                      <span className="text-xs text-muted-foreground">{fr.mentions_count || 0} mentions</span>
                    </div>
                    <p className="text-sm font-medium mt-1">{fr.title}</p>
                  </button>
                ))}
                {!loading && filteredRequests.length === 0 && (
                  <p className="text-center text-sm text-muted-foreground py-4">No feature requests found</p>
                )}
              </div>
              
              <button
                onClick={() => setShowCreateNew(true)}
                className="w-full h-10 flex items-center justify-center gap-2 rounded-lg border border-dashed border-border/60 text-sm text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors"
              >
                <FileText size={16} />
                Create new feature request
              </button>
            </>
          ) : (
            <>
              <div>
                <label className="text-sm font-medium mb-2 block">Title</label>
                <input
                  type="text"
                  value={newFeatureTitle}
                  onChange={(e) => setNewFeatureTitle(e.target.value)}
                  placeholder="Feature request title..."
                  className="w-full h-10 px-3 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  autoFocus
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Description</label>
                <textarea
                  value={newFeatureDescription}
                  onChange={(e) => setNewFeatureDescription(e.target.value)}
                  placeholder="Describe the feature request..."
                  rows={4}
                  className="w-full px-3 py-2 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                />
              </div>
            </>
          )}
        </div>
        
        <div className="p-4 border-t border-border/40 flex justify-end gap-2">
          {showCreateNew ? (
            <>
              <button
                onClick={() => setShowCreateNew(false)}
                className="h-9 px-4 text-sm rounded-lg border border-border/40 hover:bg-secondary/50 transition-colors"
              >
                Back
              </button>
              <button
                onClick={createAndLink}
                disabled={!newFeatureTitle.trim()}
                className="h-9 px-4 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Create & Link
              </button>
            </>
          ) : (
            <button
              onClick={onClose}
              className="h-9 px-4 text-sm rounded-lg border border-border/40 hover:bg-secondary/50 transition-colors"
            >
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default TicketDrawer;
