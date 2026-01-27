import React, { useState, useEffect, useRef } from 'react';
import DOMPurify from 'dompurify';
import { 
  X, Save, Trash2, Send, ChevronDown, ChevronRight,
  Loader2, Star, MoreHorizontal, Mail, AlertCircle, 
  Sparkles, PenLine, Command, Link2, Settings, Users,
  Clock, ArrowUpCircle, UserCheck, AtSign, Copy, Printer,
  BellOff, Merge, ExternalLink, Split, Link, FileText, 
  Tag, Bookmark, Download, UserPlus, Scissors, MessageSquareHeart,
  GitMerge, Filter, Unlink
} from 'lucide-react';
import RichTextEditor from './RichTextEditor';
import MentionInput, { renderTextWithMentions } from './MentionInput';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Merge color palette for visual distinction of merged ticket sources
const MERGE_COLORS = [
  { bg: 'bg-cyan-500/10', border: 'border-l-cyan-500', text: 'text-cyan-400', label: 'Cyan' },
  { bg: 'bg-amber-500/10', border: 'border-l-amber-500', text: 'text-amber-400', label: 'Amber' },
  { bg: 'bg-violet-500/10', border: 'border-l-violet-500', text: 'text-violet-400', label: 'Violet' },
  { bg: 'bg-emerald-500/10', border: 'border-l-emerald-500', text: 'text-emerald-400', label: 'Emerald' },
  { bg: 'bg-rose-500/10', border: 'border-l-rose-500', text: 'text-rose-400', label: 'Rose' },
];

const getMergeColor = (colorIndex) => {
  return MERGE_COLORS[colorIndex % MERGE_COLORS.length];
};

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

// Email-style message component with merge support
const EmailMessage = ({ type, sender, senderEmail, subject, content, timestamp, isFirst, isAgentMessage, originalTicketId, mergeColorIndex, isMergeDivider, mergedTicketTitle, currentTicketId }) => {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  // Handle merge divider - clean, minimal separator
  if (isMergeDivider || type === 'merge_divider') {
    const mergeColor = getMergeColor(mergeColorIndex || 0);
    return (
      <div className="my-3 flex items-center gap-3" data-testid="merge-divider">
        <div className="flex-1 h-px bg-border/50" />
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <GitMerge size={11} className={mergeColor.text} />
          <span className={mergeColor.text}>{originalTicketId}</span>
          {mergedTicketTitle && (
            <span className="text-muted-foreground/60 truncate max-w-[180px]">· {mergedTicketTitle}</span>
          )}
        </div>
        <div className="flex-1 h-px bg-border/50" />
      </div>
    );
  }

  // Handle system messages (assignments, status changes, etc.) - minimal one-line display
  if (type === 'system') {
    return (
      <div className="flex items-center justify-center py-1">
        <span className="text-[11px] text-muted-foreground/60">
          {content} • {formatDate(timestamp)}
        </span>
      </div>
    );
  }

  const isNote = type === 'internal_note';
  const isReply = type === 'reply';
  const isCustomerMessage = type === 'original' || type === 'customer_reply';
  const isAgent = isAgentMessage || isReply || isNote;
  
  // Check if this message is from a merged ticket (different from current)
  const isFromMergedTicket = originalTicketId && originalTicketId !== currentTicketId;
  const mergeColor = isFromMergedTicket ? getMergeColor(mergeColorIndex || 0) : null;
  
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
  
  // Subtle left accent for merged messages (thin line, not thick border)
  const mergeAccent = isFromMergedTicket ? `border-l-2 ${mergeColor.border}` : '';
  
  return (
    <div className={`${styles.alignment}`} data-testid="message-item">
      <div className={`${styles.container} ${mergeAccent} p-3`}>
        {/* Message Header - Compact */}
        <div className={`flex items-center justify-between mb-2 ${isAgent && !isNote ? 'flex-row-reverse' : ''}`}>
          <div className={`flex items-center gap-2 ${isAgent && !isNote ? 'flex-row-reverse' : ''}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium shrink-0 ${styles.avatar}`}>
              {sender?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-medium text-sm">{sender || 'Unknown'}</span>
              {isNote && (
                <span className="text-[10px] px-1 py-0.5 rounded bg-amber-400/20 text-amber-400">Note</span>
              )}
              {isReply && (
                <span className="text-[10px] px-1 py-0.5 rounded bg-primary/20 text-primary">Reply</span>
              )}
            </div>
          </div>
          <div className={`flex items-center gap-1.5 text-[10px] text-muted-foreground shrink-0 ${isAgent && !isNote ? 'flex-row-reverse' : ''}`}>
            {isFromMergedTicket && (
              <span className={`font-mono ${mergeColor.text}`}>{originalTicketId}</span>
            )}
            <span>{formatDate(timestamp)}</span>
          </div>
        </div>
        
        {/* Subject line for first message */}
        {subject && isFirst && (
          <p className="text-xs text-muted-foreground mb-2 pl-8">Re: {subject}</p>
        )}
        
        {/* Message Body */}
        <div className="text-sm text-foreground/90 leading-relaxed pl-8">
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
  
  // CSAT state
  const [csatData, setCsatData] = useState(null);
  const [sendingCsat, setSendingCsat] = useState(false);
  
  // Linked Feature Requests state
  const [linkedFeatureRequests, setLinkedFeatureRequests] = useState([]);
  
  // Merge-related state
  const [mergedTickets, setMergedTickets] = useState([]);
  const [mergeSuggestions, setMergeSuggestions] = useState([]);
  const [dismissedMergeSuggestions, setDismissedMergeSuggestions] = useState([]);
  const [messageSourceFilter, setMessageSourceFilter] = useState('all'); // 'all' or specific ticket_id
  const [showMergedPanel, setShowMergedPanel] = useState(false);
  
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
      setTicketTags(ticket.tags || []);
      setTagInput('');
      setShowTagDropdown(false);
      // Merged tickets data
      setMergedTickets(ticket.merged_tickets || []);
      setMessageSourceFilter('all');
      setDismissedMergeSuggestions([]);
      fetchNotes(ticket.id);
      fetchRelatedTickets(ticket.id);
      fetchCustomFields();
      fetchAssignmentOptions(ticket.id);
      fetchAvailableTags();
      fetchCsatData(ticket.id);
      fetchLinkedFeatureRequests(ticket.id);
      fetchMergeSuggestions(ticket.id);
    }
  }, [ticket]);

  // Fetch merge suggestions for auto-merge
  const fetchMergeSuggestions = async (ticketId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}/merge-suggestions`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setMergeSuggestions(data.suggestions || []);
      }
    } catch (error) {
      console.error('Failed to fetch merge suggestions:', error);
    }
  };

  // Unmerge a ticket
  const handleUnmerge = async (sourceTicketId) => {
    if (!ticket) return;
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/unmerge/${sourceTicketId}`, {
        method: 'POST',
        credentials: 'include'
      });
      if (response.ok) {
        // Update local state
        setMergedTickets(prev => prev.filter(m => m.ticket_id !== sourceTicketId));
        // Refresh messages
        fetchNotes(ticket.id);
        // Notify parent
        if (onUpdate) {
          onUpdate(ticket.id, { merged_tickets: mergedTickets.filter(m => m.ticket_id !== sourceTicketId) });
        }
      }
    } catch (error) {
      console.error('Failed to unmerge ticket:', error);
    }
  };

  // Fetch linked feature requests for ticket
  const fetchLinkedFeatureRequests = async (ticketId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}/feature-requests`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setLinkedFeatureRequests(data || []);
      }
    } catch (error) {
      console.error('Failed to fetch linked feature requests:', error);
      setLinkedFeatureRequests([]);
    }
  };

  // Unlink feature request from ticket
  const handleUnlinkFeatureRequest = async (featureRequestId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/feature-request/${featureRequestId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      if (response.ok) {
        setLinkedFeatureRequests(prev => prev.filter(fr => fr.feature_request_id !== featureRequestId));
      }
    } catch (error) {
      console.error('Failed to unlink feature request:', error);
    }
  };

  // Fetch CSAT data for ticket
  const fetchCsatData = async (ticketId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/csat/ticket/${ticketId}`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setCsatData(data);
      }
    } catch (error) {
      console.error('Failed to fetch CSAT data:', error);
    }
  };

  // Send CSAT survey
  const handleSendCsat = async () => {
    if (!ticket || sendingCsat) return;
    
    setSendingCsat(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/csat/send/${ticket.id}`, {
        method: 'POST',
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setCsatData({
          has_response: false,
          survey_sent: true,
          sent_at: new Date().toISOString(),
          expires_at: data.expires_at
        });
      }
    } catch (error) {
      console.error('Failed to send CSAT:', error);
    } finally {
      setSendingCsat(false);
    }
  };

  // Fetch all available tags from existing tickets
  const fetchAvailableTags = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets`, {
        credentials: 'include'
      });
      if (response.ok) {
        const tickets = await response.json();
        const allTags = new Set();
        tickets.forEach(t => (t.tags || []).forEach(tag => allTags.add(tag)));
        setAvailableTags(Array.from(allTags).sort());
      }
    } catch (error) {
      console.error('Failed to fetch tags:', error);
    }
  };

  // Add tag to ticket
  const handleAddTag = async (tag) => {
    if (!tag.trim() || !ticket) return;
    const normalizedTag = tag.trim().toLowerCase().replace(/\s+/g, '-');
    
    if (ticketTags.includes(normalizedTag)) {
      setTagInput('');
      setShowTagDropdown(false);
      return;
    }
    
    setLoadingTags(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify([normalizedTag])
      });
      
      if (response.ok) {
        const data = await response.json();
        setTicketTags(data.tags || [...ticketTags, normalizedTag]);
        // Add to available tags if it's new
        if (!availableTags.includes(normalizedTag)) {
          setAvailableTags(prev => [...prev, normalizedTag].sort());
        }
      }
    } catch (error) {
      console.error('Failed to add tag:', error);
    } finally {
      setLoadingTags(false);
      setTagInput('');
      setShowTagDropdown(false);
    }
  };

  // Remove tag from ticket
  const handleRemoveTag = async (tag) => {
    if (!ticket) return;
    
    setLoadingTags(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/tags/${encodeURIComponent(tag)}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setTicketTags(data.tags || ticketTags.filter(t => t !== tag));
      }
    } catch (error) {
      console.error('Failed to remove tag:', error);
    } finally {
      setLoadingTags(false);
    }
  };

  // Filter available tags based on input
  const filteredTags = availableTags.filter(tag => 
    tag.toLowerCase().includes(tagInput.toLowerCase()) && 
    !ticketTags.includes(tag)
  );

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
      
      const activeElement = document.activeElement;
      const isTyping = activeElement?.isContentEditable || 
                       activeElement?.tagName === 'INPUT' || 
                       activeElement?.tagName === 'TEXTAREA' ||
                       activeElement?.tagName === 'SELECT';
      
      // Escape - close drawer/modals (works even when typing)
      if (e.key === 'Escape') {
        e.preventDefault();
        // Close modals first if any are open
        if (showMergeModal) {
          setShowMergeModal(false);
          return;
        }
        if (showLinkModal) {
          setShowLinkModal(false);
          return;
        }
        if (showSplitModal) {
          setShowSplitModal(false);
          return;
        }
        if (showFeatureRequestModal) {
          setShowFeatureRequestModal(false);
          return;
        }
        if (showMoreMenu) {
          setShowMoreMenu(false);
          return;
        }
        if (showAssignDropdown) {
          setShowAssignDropdown(false);
          return;
        }
        if (showTagDropdown) {
          setShowTagDropdown(false);
          return;
        }
        // Close the drawer
        onClose();
        return;
      }
      
      // Shortcuts that only work when not typing
      if (!isTyping) {
        // N for note mode
        if (e.key === 'n' || e.key === 'N') {
          e.preventDefault();
          setInputMode('note');
        }
        // R for reply mode
        if (e.key === 'r' || e.key === 'R') {
          e.preventDefault();
          setInputMode('reply');
        }
        // S for star/unstar
        if (e.key === 's' || e.key === 'S') {
          e.preventDefault();
          handleToggleStar();
        }
        // A for assign to me
        if (e.key === 'a' || e.key === 'A') {
          e.preventDefault();
          handleAssignToMe();
        }
        // M for merge
        if (e.key === 'm' || e.key === 'M') {
          e.preventDefault();
          setShowMergeModal(true);
        }
        // L for link
        if (e.key === 'l' || e.key === 'L') {
          e.preventDefault();
          setShowLinkModal(true);
        }
        // C for copy link
        if (e.key === 'c' || e.key === 'C') {
          e.preventDefault();
          handleCopyLink();
        }
        // D for delete (with confirmation)
        if (e.key === 'd' || e.key === 'D') {
          e.preventDefault();
          setShowDeleteConfirm(true);
        }
        // Arrow keys for navigation (future: prev/next ticket)
        // 1-5 for priority
        if (e.key >= '1' && e.key <= '4') {
          e.preventDefault();
          const priorities = ['low', 'medium', 'high', 'urgent'];
          const newPriority = priorities[parseInt(e.key) - 1];
          setFormData(prev => ({ ...prev, priority: newPriority }));
        }
      }
      
      // Cmd/Ctrl + Enter to send (works when typing)
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        handleSubmitInput();
      }
      
      // Cmd/Ctrl + S to save (works when typing)
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        handleSaveChanges();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, showMergeModal, showLinkModal, showSplitModal, showFeatureRequestModal, showMoreMenu, showAssignDropdown, showTagDropdown, onClose, inputText]);

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
      isAgentMessage: false, // Customer's original message
      original_ticket_id: null, // Original ticket message, not merged
      merge_color_index: null
    },
    ...notes.map(note => ({
      type: note.type || 'internal_note',
      sender: note.author_name || 'Unknown',
      senderEmail: null,
      subject: null,
      content: note.content || note.text,
      timestamp: note.created_at,
      isAgentMessage: note.type !== 'customer_reply',
      original_ticket_id: note.original_ticket_id || null,
      merge_color_index: note.merge_color_index,
      merged_ticket_title: note.merged_ticket_title
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
            
            {/* Auto-merge Suggestions Banner */}
            {mergeSuggestions.length > 0 && mergeSuggestions.filter(s => !dismissedMergeSuggestions.includes(s.ticket_id)).length > 0 && (
              <div className="mb-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
                <div className="flex items-start gap-2">
                  <GitMerge size={16} className="text-amber-400 mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-amber-400 mb-1">Possible duplicate detected</p>
                    <p className="text-[11px] text-muted-foreground mb-2">
                      Same customer email within 2 hours
                    </p>
                    {mergeSuggestions.filter(s => !dismissedMergeSuggestions.includes(s.ticket_id)).map(suggestion => (
                      <div key={suggestion.ticket_id} className="flex items-center gap-2 py-1.5 border-t border-amber-500/20 first:border-t-0">
                        <div className="flex-1 min-w-0">
                          <p className="text-xs truncate">{suggestion.title}</p>
                          <p className="text-[10px] text-muted-foreground">{suggestion.ticket_id}</p>
                        </div>
                        <button
                          onClick={() => {
                            setShowMergeModal(true);
                          }}
                          className="text-[10px] px-2 py-1 rounded bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 transition-colors"
                        >
                          Merge
                        </button>
                        <button
                          onClick={() => setDismissedMergeSuggestions(prev => [...prev, suggestion.ticket_id])}
                          className="text-[10px] px-2 py-1 rounded text-muted-foreground hover:bg-secondary/50 transition-colors"
                        >
                          Dismiss
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
            
            {/* Merged Tickets Info - Compact inline display */}
            {mergedTickets.length > 0 && (
              <div className="mb-3 p-2 rounded-lg bg-secondary/20 border border-border/30">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <GitMerge size={12} className="text-muted-foreground" />
                    <span className="text-[11px] text-muted-foreground">
                      Contains {mergedTickets.length} merged {mergedTickets.length === 1 ? 'ticket' : 'tickets'}
                    </span>
                    <div className="flex items-center gap-1">
                      {mergedTickets.slice(0, 3).map((m, idx) => {
                        const color = getMergeColor(m.color_index || idx);
                        return (
                          <span key={m.ticket_id} className={`text-[10px] font-mono ${color.text}`}>
                            {m.ticket_id}
                          </span>
                        );
                      })}
                      {mergedTickets.length > 3 && (
                        <span className="text-[10px] text-muted-foreground">+{mergedTickets.length - 3}</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => setShowMergedPanel(!showMergedPanel)}
                    className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showMergedPanel ? 'Hide' : 'Details'}
                  </button>
                </div>
                
                {showMergedPanel && (
                  <div className="mt-2 pt-2 border-t border-border/30 space-y-1.5">
                    {mergedTickets.map((merged, idx) => {
                      const color = getMergeColor(merged.color_index || idx);
                      return (
                        <div key={merged.ticket_id} className="flex items-center justify-between py-1">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className={`text-[10px] font-mono ${color.text}`}>{merged.ticket_id}</span>
                            <span className="text-[11px] truncate">{merged.original_title}</span>
                          </div>
                          <button
                            onClick={() => handleUnmerge(merged.ticket_id)}
                            className="text-[10px] text-muted-foreground hover:text-foreground transition-colors shrink-0"
                            title="Unmerge"
                          >
                            <Unlink size={11} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
            
            {/* Message Source Filter (when merged tickets exist) */}
            {mergedTickets.length > 0 && (
              <div className="mb-3 flex items-center gap-2">
                <Filter size={11} className="text-muted-foreground" />
                <select
                  value={messageSourceFilter}
                  onChange={(e) => setMessageSourceFilter(e.target.value)}
                  className="text-xs bg-secondary/30 border border-border/40 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary"
                  data-testid="message-source-filter"
                >
                  <option value="all">All messages</option>
                  <option value={ticket?.ticket_id}>{ticket?.ticket_id} (Original)</option>
                  {mergedTickets.map((merged, idx) => (
                    <option key={merged.ticket_id} value={merged.ticket_id}>
                      {merged.ticket_id} ({merged.original_title?.slice(0, 20)}...)
                    </option>
                  ))}
                </select>
              </div>
            )}
            
            {/* Current Conversation */}
            {loadingNotes && conversationThread.length === 1 ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 size={24} className="animate-spin text-muted-foreground" />
              </div>
            ) : (
              conversationThread
                .filter(msg => messageSourceFilter === 'all' || 
                  msg.original_ticket_id === messageSourceFilter || 
                  (!msg.original_ticket_id && messageSourceFilter === ticket?.ticket_id))
                .map((msg, idx) => (
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
                  originalTicketId={msg.original_ticket_id}
                  mergeColorIndex={msg.merge_color_index}
                  isMergeDivider={msg.type === 'merge_divider'}
                  mergedTicketTitle={msg.merged_ticket_title}
                  currentTicketId={ticket?.ticket_id}
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
                  
                  {/* Always show Assign to me at the top */}
                  {currentUser && (
                    <button
                      onClick={handleAssignToMe}
                      className={`w-full px-3 py-2 text-left text-sm hover:bg-primary/10 flex items-center gap-2 border-b border-border/30 ${
                        formData.assignee_id === (currentUser.user_id || currentUser.id) ? 'bg-primary/10 text-primary' : 'text-primary'
                      }`}
                      data-testid="assign-to-me-button"
                    >
                      <UserPlus size={14} />
                      <span>Assign to me</span>
                      {formData.assignee_id === (currentUser.user_id || currentUser.id) && (
                        <span className="ml-auto text-[10px]">✓</span>
                      )}
                    </button>
                  )}
                  
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
                      {assignmentOptions.team_members
                        .filter(m => m.user_id !== (currentUser?.user_id || currentUser?.id))
                        .map(member => (
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
                  
                  {/* Show all users section when no team members or as additional option */}
                  {users.length > 0 && (
                    <>
                      <div className="px-3 py-1.5 text-[10px] font-medium uppercase text-muted-foreground bg-secondary/30">
                        {assignmentOptions?.team_members?.length > 0 ? 'Other Users' : 'All Users'}
                      </div>
                      {users
                        .filter(user => {
                          const userId = user.id || user.user_id;
                          // Don't show current user (already shown at top)
                          if (userId === (currentUser?.user_id || currentUser?.id)) return false;
                          // Don't show team members (already shown above)
                          if (assignmentOptions?.team_members?.some(m => m.user_id === userId)) return false;
                          return true;
                        })
                        .map(user => (
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
                  {linkedFeatureRequests.length > 0 && (
                    <span className="text-[9px] bg-primary/20 text-primary px-1.5 py-0.5 rounded-full">
                      {linkedFeatureRequests.length} FR
                    </span>
                  )}
                </div>
                {sectionsExpanded.links ? (
                  <ChevronDown size={12} className="text-muted-foreground" />
                ) : (
                  <ChevronRight size={12} className="text-muted-foreground" />
                )}
              </button>
              
              {sectionsExpanded.links && (
                <div className="mt-1.5 space-y-2">
                  {/* Linked Feature Requests */}
                  {linkedFeatureRequests.length > 0 && (
                    <div className="space-y-1.5">
                      <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider pl-1">
                        Feature Requests ({linkedFeatureRequests.length})
                      </div>
                      {linkedFeatureRequests.map(fr => (
                        <div 
                          key={fr.feature_request_id}
                          className="flex items-center gap-2 p-2 bg-secondary/30 rounded-md group"
                        >
                          <Bookmark size={12} className={`shrink-0 ${
                            fr.request_type === 'bug_fix' ? 'text-red-400' :
                            fr.request_type === 'enhancement' ? 'text-emerald-400' :
                            'text-blue-400'
                          }`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
                                fr.request_type === 'bug_fix' ? 'bg-red-500/20 text-red-400' :
                                fr.request_type === 'enhancement' ? 'bg-emerald-500/20 text-emerald-400' :
                                'bg-blue-500/20 text-blue-400'
                              }`}>
                                {fr.request_type === 'bug_fix' ? 'Bug Fix' : 
                                 fr.request_type === 'enhancement' ? 'Enhancement' : 'Feature'}
                              </span>
                              <span className={`text-[9px] px-1.5 py-0.5 rounded ${
                                fr.priority === 'critical' ? 'bg-red-500/20 text-red-400' :
                                fr.priority === 'high' ? 'bg-orange-500/20 text-orange-400' :
                                fr.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                                'bg-gray-500/20 text-gray-400'
                              }`}>
                                {fr.priority}
                              </span>
                            </div>
                            <div className="text-xs text-foreground truncate mt-0.5" title={fr.title}>
                              {fr.title}
                            </div>
                            <div className="text-[10px] text-muted-foreground font-mono">
                              {fr.feature_request_id}
                            </div>
                          </div>
                          <button
                            onClick={() => handleUnlinkFeatureRequest(fr.feature_request_id)}
                            className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 rounded transition-all"
                            title="Unlink feature request"
                          >
                            <X size={12} className="text-red-400" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {/* Add Feature Request Link */}
                  <button
                    onClick={() => setShowFeatureRequestModal(true)}
                    className="w-full flex items-center justify-between py-1 pl-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
                  >
                    <span className="flex items-center gap-1.5">
                      <Bookmark size={11} />
                      Link Feature Request
                    </span>
                    <span className="text-primary text-[10px]">+ Add</span>
                  </button>
                  
                  <div className="h-px bg-border/20" />
                  
                  <div className="flex items-center justify-between py-1 pl-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-colors">
                    <span>Related tickets</span>
                    <span className="text-primary text-[10px]">+ Add</span>
                  </div>
                  <div className="flex items-center justify-between py-1 pl-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-colors">
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
                </div>
              )}
            </div>

            {/* Divider */}
            <div className="h-px bg-border/30" />

            {/* Tags Section - Interactive */}
            <div>
              <div className="flex items-center justify-between py-1">
                <div className="flex items-center gap-2">
                  <Tag size={12} className="text-muted-foreground" />
                  <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Tags</span>
                </div>
                {loadingTags && <Loader2 size={12} className="animate-spin text-muted-foreground" />}
              </div>
              
              {/* Current Tags */}
              <div className="mt-2 flex flex-wrap gap-1.5">
                {ticketTags.map((tag, i) => (
                  <span 
                    key={i} 
                    className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-full bg-primary/20 text-primary group"
                  >
                    #{tag}
                    <button
                      onClick={() => handleRemoveTag(tag)}
                      className="opacity-0 group-hover:opacity-100 hover:text-destructive transition-opacity"
                      title="Remove tag"
                      data-testid={`remove-tag-${tag}`}
                    >
                      <X size={10} />
                    </button>
                  </span>
                ))}
                {ticketTags.length === 0 && (
                  <span className="text-[10px] text-muted-foreground/50 italic">No tags</span>
                )}
              </div>
              
              {/* Add Tag Input */}
              <div className="mt-2 relative">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => {
                    setTagInput(e.target.value);
                    setShowTagDropdown(true);
                  }}
                  onFocus={() => setShowTagDropdown(true)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && tagInput.trim()) {
                      e.preventDefault();
                      handleAddTag(tagInput);
                    }
                    if (e.key === 'Escape') {
                      setShowTagDropdown(false);
                    }
                  }}
                  placeholder="Add tag..."
                  className="w-full h-7 px-2 text-xs rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50 placeholder:text-muted-foreground/50"
                  data-testid="tag-input"
                />
                
                {/* Tag Dropdown */}
                {showTagDropdown && (tagInput.trim() || filteredTags.length > 0) && (
                  <div className="absolute z-50 w-full mt-1 bg-popover border border-border rounded-lg shadow-lg max-h-40 overflow-y-auto">
                    {/* Create new tag option */}
                    {tagInput.trim() && !availableTags.includes(tagInput.trim().toLowerCase().replace(/\s+/g, '-')) && (
                      <button
                        onClick={() => handleAddTag(tagInput)}
                        className="w-full px-3 py-2 text-left text-xs hover:bg-primary/10 flex items-center gap-2 text-primary border-b border-border/30"
                        data-testid="create-new-tag"
                      >
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/20">+ Create</span>
                        <span>#{tagInput.trim().toLowerCase().replace(/\s+/g, '-')}</span>
                      </button>
                    )}
                    
                    {/* Existing tags */}
                    {filteredTags.length > 0 && (
                      <>
                        <div className="px-3 py-1.5 text-[10px] font-medium uppercase text-muted-foreground bg-secondary/30">
                          Existing Tags
                        </div>
                        {filteredTags.slice(0, 10).map(tag => (
                          <button
                            key={tag}
                            onClick={() => handleAddTag(tag)}
                            className="w-full px-3 py-2 text-left text-xs hover:bg-secondary/50 flex items-center gap-2"
                            data-testid={`add-tag-${tag}`}
                          >
                            <span className="text-primary">#{tag}</span>
                          </button>
                        ))}
                      </>
                    )}
                    
                    {/* No matches */}
                    {tagInput.trim() && filteredTags.length === 0 && availableTags.includes(tagInput.trim().toLowerCase().replace(/\s+/g, '-')) && (
                      <div className="px-3 py-2 text-xs text-muted-foreground">
                        Tag already added
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              {/* Click outside to close dropdown */}
              {showTagDropdown && (
                <div 
                  className="fixed inset-0 z-40" 
                  onClick={() => setShowTagDropdown(false)}
                />
              )}
            </div>

            {/* CSAT Section */}
            {ticket?.customer_email && (
              <>
                <div className="h-px bg-border/30" />
                <div>
                  <div className="flex items-center justify-between py-1">
                    <div className="flex items-center gap-2">
                      <MessageSquareHeart size={12} className="text-muted-foreground" />
                      <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Customer Satisfaction</span>
                    </div>
                  </div>
                  
                  <div className="mt-2">
                    {csatData?.has_response ? (
                      // Show CSAT score
                      <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-1">
                            {[1, 2, 3, 4, 5].map(star => (
                              <Star
                                key={star}
                                size={16}
                                className={star <= csatData.rating 
                                  ? 'fill-yellow-400 text-yellow-400' 
                                  : 'fill-transparent text-gray-400'
                                }
                              />
                            ))}
                          </div>
                          <span className={`text-xs font-medium ${
                            csatData.rating >= 4 ? 'text-emerald-400' : 
                            csatData.rating >= 3 ? 'text-amber-400' : 'text-red-400'
                          }`}>
                            {csatData.rating}/5
                          </span>
                        </div>
                        {csatData.feedback && (
                          <p className="text-xs text-muted-foreground mt-2 italic">
                            "{csatData.feedback}"
                          </p>
                        )}
                        <p className="text-[10px] text-muted-foreground/60 mt-2">
                          by {csatData.customer_name} · {new Date(csatData.submitted_at).toLocaleDateString()}
                        </p>
                      </div>
                    ) : csatData?.survey_sent ? (
                      // Survey sent but not responded
                      <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                        <div className="flex items-center gap-2 text-amber-400">
                          <Mail size={14} />
                          <span className="text-xs font-medium">Survey sent</span>
                        </div>
                        <p className="text-[10px] text-muted-foreground mt-1">
                          Awaiting response · Expires {new Date(csatData.expires_at).toLocaleDateString()}
                        </p>
                      </div>
                    ) : formData.status === 'resolved' ? (
                      // Can send survey (ticket resolved)
                      <button
                        onClick={handleSendCsat}
                        disabled={sendingCsat}
                        className="w-full py-2 px-3 rounded-lg bg-primary/20 hover:bg-primary/30 border border-primary/30 text-primary text-xs font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                        data-testid="send-csat-button"
                      >
                        {sendingCsat ? (
                          <>
                            <Loader2 size={14} className="animate-spin" />
                            Sending...
                          </>
                        ) : (
                          <>
                            <Send size={14} />
                            Send CSAT Survey
                          </>
                        )}
                      </button>
                    ) : (
                      // Ticket not resolved yet
                      <p className="text-[10px] text-muted-foreground/60 italic">
                        Resolve ticket to send CSAT survey
                      </p>
                    )}
                  </div>
                </div>
              </>
            )}

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
                // Use onDelete to remove the merged (source) ticket from parent's list
                // This triggers a refresh that will exclude the now-merged ticket
                if (onDelete) {
                  await onDelete(ticket.id);
                } else {
                  onClose();
                }
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
                // Refresh linked feature requests
                fetchLinkedFeatureRequests(ticket.id);
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

// Merge Ticket Modal Component with Enhanced Preview
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
        // Filter out current ticket and merged tickets
        setSearchResults((data.tickets || []).filter(t => 
          t.ticket_id !== ticket.ticket_id && t.status !== 'merged'
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
              <GitMerge size={18} className="text-primary" />
              <h3 className="text-base font-semibold">Merge Tickets</h3>
            </div>
            <button onClick={onClose} className="h-8 w-8 flex items-center justify-center rounded hover:bg-secondary/50">
              <X size={18} />
            </button>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Merge <span className="text-foreground font-medium">{ticket.ticket_id}</span> into another ticket.
          </p>
        </div>
        
        <div className="p-4 space-y-4">
          {/* Merge Preview */}
          {selectedTicket && (
            <div className="p-3 rounded-lg bg-cyan-500/10 border border-cyan-500/30 mb-4">
              <div className="flex items-center gap-2 mb-2">
                <GitMerge size={14} className="text-cyan-400" />
                <span className="text-xs font-medium text-cyan-400">Merge Preview</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 p-2 rounded bg-secondary/30 text-center">
                  <p className="text-[10px] text-muted-foreground">Source</p>
                  <p className="text-xs font-mono">{ticket.ticket_id}</p>
                  <p className="text-[10px] truncate max-w-[120px]">{ticket.title}</p>
                </div>
                <div className="text-muted-foreground">→</div>
                <div className="flex-1 p-2 rounded bg-secondary/30 text-center">
                  <p className="text-[10px] text-muted-foreground">Target</p>
                  <p className="text-xs font-mono">{selectedTicket.ticket_id}</p>
                  <p className="text-[10px] truncate max-w-[120px]">{selectedTicket.title}</p>
                </div>
              </div>
              <div className="mt-2 pt-2 border-t border-cyan-500/20 text-[10px] text-muted-foreground">
                <p>• All messages will be consolidated chronologically</p>
                <p>• Tags will be combined: {[...(ticket.tags || []), ...(selectedTicket.tags || [])].filter((v,i,a) => a.indexOf(v) === i).join(', ') || 'none'}</p>
                <p>• Searchable by both ticket IDs</p>
              </div>
            </div>
          )}

          <div>
            <label className="text-sm font-medium mb-2 block">Search for target ticket</label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by ticket ID, title, email, or content..."
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
                    result.status === 'resolved' ? 'bg-emerald-500/20 text-emerald-400' :
                    result.status === 'closed' ? 'bg-gray-500/20 text-gray-400' :
                    'bg-blue-500/20 text-blue-400'
                  }`}>{result.status}</span>
                  {result.contains_merged_ticket && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400 flex items-center gap-1">
                      <GitMerge size={10} />
                      has merges
                    </span>
                  )}
                </div>
                <p className="text-sm font-medium truncate mt-1">{result.title}</p>
                {result.customer_email && (
                  <p className="text-[10px] text-muted-foreground truncate">{result.customer_email}</p>
                )}
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
            className="h-9 px-4 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <GitMerge size={14} />
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
