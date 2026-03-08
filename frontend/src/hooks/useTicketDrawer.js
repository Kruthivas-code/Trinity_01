import { useState, useEffect, useRef, useCallback } from 'react';
import { useRealtime } from '../contexts/RealtimeContext';
import { stripHtml } from '../components/tickets/EmailMessage';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const STATUSES = [
  { value: 'todo', label: 'Open', color: 'bg-slate-400' },
  { value: 'waiting', label: 'Waiting', color: 'bg-amber-400' },
  { value: 'closed', label: 'Closed', color: 'bg-emerald-400' },
  { value: 'merged', label: 'Merged', color: 'bg-violet-400' }
];

export const PRIORITIES = [
  { value: 'low', label: 'Low', color: 'text-slate-400' },
  { value: 'medium', label: 'Medium', color: 'text-amber-400' },
  { value: 'high', label: 'High', color: 'text-orange-400' },
  { value: 'urgent', label: 'Urgent', color: 'text-red-400' }
];

export const ESCALATION_LEVELS = [
  { value: 'L1', label: 'L1 - Basic', color: 'bg-blue-500' },
  { value: 'L2', label: 'L2 - Advanced', color: 'bg-amber-500' },
  { value: 'L3', label: 'L3 - Specialist', color: 'bg-red-500' }
];

const useTicketDrawer = ({ ticket, users, currentUser, isOpen, onClose, onUpdate, onDelete }) => {
  // Real-time context for typing indicators
  const realtimeContext = useRealtime();
  const { joinLocation, leaveLocation, sendTyping, typingUsers, isConnected } = realtimeContext || {};

  // Animation state for closing
  const [isClosing, setIsClosing] = useState(false);
  const closeTimeoutRef = useRef(null);

  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (closeTimeoutRef.current) {
        clearTimeout(closeTimeoutRef.current);
      }
    };
  }, []);

  // Reset closing state when drawer opens
  useEffect(() => {
    if (isOpen) {
      setIsClosing(false);
      if (closeTimeoutRef.current) {
        clearTimeout(closeTimeoutRef.current);
        closeTimeoutRef.current = null;
      }
    }
  }, [isOpen]);

  // Handle close with animation
  const handleCloseWithAnimation = useCallback(() => {
    if (isClosing) return;
    setIsClosing(true);
    closeTimeoutRef.current = setTimeout(() => {
      setIsClosing(false);
      closeTimeoutRef.current = null;
      onClose();
    }, 200);
  }, [onClose, isClosing]);

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
  const [inputMode, setInputMode] = useState('reply');
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Image attachments
  const [attachedImages, setAttachedImages] = useState([]);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [ccEmails, setCcEmails] = useState([]);
  const [showCcField, setShowCcField] = useState(false);
  const imageInputRef = useRef(null);

  // Canned responses picker
  const [showCannedPicker, setShowCannedPicker] = useState(false);

  // Knowledge Base picker
  const [showKBPicker, setShowKBPicker] = useState(false);

  // Related tickets (from same customer)
  const [relatedTickets, setRelatedTickets] = useState([]);
  const [loadingRelated, setLoadingRelated] = useState(false);

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

  // Modal states
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

  // Activity tab state
  const [activeTab, setActiveTab] = useState('conversation');
  const [activityFeed, setActivityFeed] = useState([]);
  const [loadingActivity, setLoadingActivity] = useState(false);

  // CSAT state
  const [csatData, setCsatData] = useState(null);
  const [sendingCsat, setSendingCsat] = useState(false);

  // Linked Feature Requests state
  const [linkedFeatureRequests, setLinkedFeatureRequests] = useState([]);

  // Merge-related state
  const [mergedTickets, setMergedTickets] = useState([]);
  const [mergeSuggestions, setMergeSuggestions] = useState([]);
  const [dismissedMergeSuggestions, setDismissedMergeSuggestions] = useState([]);
  const [messageSourceFilter, setMessageSourceFilter] = useState('all');
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
  const typingTimeoutRef = useRef(null);

  // Join/leave ticket room for real-time presence
  useEffect(() => {
    if (isOpen && ticket && joinLocation && leaveLocation) {
      joinLocation('ticket', ticket.ticket_id || ticket.id);
      return () => {
        leaveLocation('ticket', ticket.ticket_id || ticket.id);
      };
    }
  }, [isOpen, ticket, joinLocation, leaveLocation]);

  // Handle typing indicator - debounced
  const handleTypingChange = useCallback((isTyping) => {
    if (!sendTyping || !ticket) return;

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    sendTyping('ticket', ticket.ticket_id || ticket.id, isTyping);

    if (isTyping) {
      typingTimeoutRef.current = setTimeout(() => {
        sendTyping('ticket', ticket.ticket_id || ticket.id, false);
      }, 3000);
    }
  }, [sendTyping, ticket]);

  // Filter out current user from typing users
  const othersTyping = (typingUsers || []).filter(u =>
    u.user_id !== currentUser?.user_id && u.user_id !== currentUser?.id
  );

  // Use ticket ID as the primary dependency
  const ticketId = ticket?.ticket_id || ticket?.id;
  const prevTicketIdRef = useRef(null);

  useEffect(() => {
    if (ticket && ticketId && ticketId !== prevTicketIdRef.current) {
      prevTicketIdRef.current = ticketId;

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
      setMergedTickets(ticket.merged_tickets || []);
      setMessageSourceFilter('all');
      setDismissedMergeSuggestions([]);
      setActiveTab('conversation');
      setActivityFeed([]);
      fetchNotes(ticketId);
      fetchRelatedTickets(ticketId);
      fetchCustomFields();
      fetchAssignmentOptions(ticketId);
      fetchAvailableTags();
      fetchCsatData(ticketId);
      fetchLinkedFeatureRequests(ticketId);
      fetchMergeSuggestions(ticketId);
      fetchActivityFeed(ticketId);
    }
  }, [ticketId]);

  // Auto-save when form data changes (debounced)
  const autoSaveTimeoutRef = useRef(null);
  const initialLoadRef = useRef(true);

  useEffect(() => {
    if (initialLoadRef.current) {
      initialLoadRef.current = false;
      return;
    }
    if (!ticket) return;

    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current);
    }

    autoSaveTimeoutRef.current = setTimeout(() => {
      onUpdate(ticket.id, {
        ...formData,
        custom_fields: customFieldValues
      });
    }, 500);

    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }
    };
  }, [formData, customFieldValues]);

  // Reset initial load flag when ticket changes
  useEffect(() => {
    initialLoadRef.current = true;
  }, [ticket?.id]);

  // --- Fetch functions ---

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

  const handleUnmerge = async (sourceTicketId) => {
    if (!ticket) return;
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/unmerge/${sourceTicketId}`, {
        method: 'POST',
        credentials: 'include'
      });
      if (response.ok) {
        setMergedTickets(prev => prev.filter(m => m.ticket_id !== sourceTicketId));
        fetchNotes(ticket.id);
        if (onUpdate) {
          onUpdate(ticket.id, { merged_tickets: mergedTickets.filter(m => m.ticket_id !== sourceTicketId) });
        }
      }
    } catch (error) {
      console.error('Failed to unmerge ticket:', error);
    }
  };

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

  const handleUnlinkTicket = async (targetTicketId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/unlink/${targetTicketId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      if (response.ok) {
        setLinkedTickets(prev => prev.filter(t => t.ticket_id !== targetTicketId));
      }
    } catch (error) {
      console.error('Failed to unlink ticket:', error);
    }
  };

  const fetchActivityFeed = async (ticketId) => {
    try {
      setLoadingActivity(true);
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}/activity-feed`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setActivityFeed(data.activities || data || []);
      }
    } catch (error) {
      console.error('Failed to fetch activity feed:', error);
      setActivityFeed([]);
    } finally {
      setLoadingActivity(false);
    }
  };

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

  const fetchAvailableTags = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets?limit=200`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        const tickets = data.tickets || data;
        const allTags = new Set();
        tickets.forEach(t => (t.tags || []).forEach(tag => allTags.add(tag)));
        setAvailableTags(Array.from(allTags).sort());
      }
    } catch (error) {
      console.error('Failed to fetch tags:', error);
    }
  };

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

  const filteredTags = availableTags.filter(tag =>
    tag.toLowerCase().includes(tagInput.toLowerCase()) &&
    !ticketTags.includes(tag)
  );

  const handleAssign = async (userId) => {
    setFormData({ ...formData, assignee_id: userId });
    setShowAssignDropdown(false);

    if (onUpdate && ticket) {
      await onUpdate(ticket.id, { assignee_id: userId });
    }
  };

  const handleAssignToMe = async () => {
    const myUserId = currentUser?.user_id || currentUser?.id;
    if (myUserId) {
      await handleAssign(myUserId);
    }
  };

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

      if (!response.ok) {
        setIsStarred(!newStarred);
      }
    } catch (error) {
      setIsStarred(!newStarred);
      console.error('Operation failed');
    }
  };

  const handleCopyLink = () => {
    const url = `${window.location.origin}/all-tickets?ticket=${ticket.ticket_id || ticket.id}`;
    navigator.clipboard.writeText(url);
    setShowMoreMenu(false);
  };

  const handleCopyTicketId = () => {
    const ticketId = ticket.ticket_id || ticket.id;
    navigator.clipboard.writeText(ticketId);
  };

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

      if (!response.ok) {
        setSnoozed(!newSnoozed);
      }
    } catch (error) {
      setSnoozed(!newSnoozed);
      console.error('Operation failed');
    }
    setShowMoreMenu(false);
  };

  const handlePrint = () => {
    window.print();
    setShowMoreMenu(false);
  };

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
        setFormData(prev => ({
          ...prev,
          escalation_level: newLevel,
          team_id: data.assignment?.team_id || prev.team_id,
          assignee_id: data.assignment?.assignee_id || null
        }));
        fetchAssignmentOptions(ticket.id);
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

      if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault();
        setShowCannedPicker(true);
        return;
      }

      if (e.key === 'Escape') {
        e.preventDefault();
        if (showCannedPicker) { setShowCannedPicker(false); return; }
        if (showMergeModal) { setShowMergeModal(false); return; }
        if (showLinkModal) { setShowLinkModal(false); return; }
        if (showSplitModal) { setShowSplitModal(false); return; }
        if (showFeatureRequestModal) { setShowFeatureRequestModal(false); return; }
        if (showMoreMenu) { setShowMoreMenu(false); return; }
        if (showAssignDropdown) { setShowAssignDropdown(false); return; }
        if (showTagDropdown) { setShowTagDropdown(false); return; }
        handleCloseWithAnimation();
        return;
      }

      if (!isTyping) {
        if (e.key === 'n' || e.key === 'N') { e.preventDefault(); setInputMode('note'); }
        if (e.key === 'r' || e.key === 'R') { e.preventDefault(); setInputMode('reply'); }
        if (e.key === 's' || e.key === 'S') { e.preventDefault(); handleToggleStar(); }
        if (e.key === 'a' || e.key === 'A') { e.preventDefault(); handleAssignToMe(); }
        if (e.key === 'm' || e.key === 'M') { e.preventDefault(); setShowMergeModal(true); }
        if (e.key === 'l' || e.key === 'L') { e.preventDefault(); setShowLinkModal(true); }
        if (e.key === 'c' || e.key === 'C') { e.preventDefault(); handleCopyLink(); }
        if (e.key === 'd' || e.key === 'D') { e.preventDefault(); setShowDeleteConfirm(true); }
        if (e.key >= '1' && e.key <= '4') {
          e.preventDefault();
          const priorities = ['low', 'medium', 'high', 'urgent'];
          const newPriority = priorities[parseInt(e.key) - 1];
          setFormData(prev => ({ ...prev, priority: newPriority }));
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, showCannedPicker, showMergeModal, showLinkModal, showSplitModal, showFeatureRequestModal, showMoreMenu, showAssignDropdown, showTagDropdown, handleCloseWithAnimation, inputText]);

  const fetchNotes = async (ticketId) => {
    setLoadingNotes(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticketId}/notes?limit=500`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setNotes(data.messages || data);
      }
    } catch (error) {
      console.error('Failed to fetch notes:', error);
    } finally {
      setLoadingNotes(false);
    }
  };

  const handleSubmitInput = async () => {
    const plainText = stripHtml(inputText);
    const hasContent = plainText.trim() || attachedImages.length > 0;
    if (!hasContent || !ticket || submitting) return;

    handleTypingChange(false);

    setSubmitting(true);
    try {
      let finalContent = inputText.trim();

      if (attachedImages.length > 0) {
        const imageHtml = attachedImages.map(img =>
          `<div class="attached-image" style="margin: 8px 0;"><img src="${img.url}" alt="${img.name}" style="max-width: 100%; max-height: 400px; border-radius: 8px;" /></div>`
        ).join('');
        finalContent = finalContent ? `${finalContent}<br><br>${imageHtml}` : imageHtml;
      }


      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          content: finalContent,
          type: inputMode === 'reply' ? 'reply' : 'internal_note',
          mentions: inputMentions,
          images: attachedImages.map(img => ({ url: img.url, name: img.name })),
          cc: inputMode === 'reply' ? ccEmails.filter(e => e.trim()) : [],
        })
      });
      if (response.ok) {
        setInputText('');
        setInputMentions([]);
        setAttachedImages([]);
        setCcEmails([]);
        setShowCcField(false);
        fetchNotes(ticket.id);
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

  const handleCannedResponseSelect = (content) => {
    if (inputText.trim()) {
      setInputText(prev => prev + '<br><br>' + content);
    } else {
      setInputText(content);
    }
    setShowCannedPicker(false);
  };

  const handleKBInsertLink = (url, title) => {
    const linkHtml = `<a href="${url}" target="_blank" rel="noopener noreferrer">${title || url}</a>`;
    if (inputText.trim()) {
      setInputText(prev => prev + '<br>' + linkHtml);
    } else {
      setInputText(linkHtml);
    }
  };

  const handleKBInsertContent = (content) => {
    const htmlContent = content.replace(/\n/g, '<br>');
    if (inputText.trim()) {
      setInputText(prev => prev + '<br><br>' + htmlContent);
    } else {
      setInputText(htmlContent);
    }
  };

  const handleSaveToKB = async (content, title) => {
    const plainText = stripHtml(content);
    try {
      await fetch(`${BACKEND_URL}/api/knowledge-base`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          title: title || ticket?.title || 'Untitled Snippet',
          content: plainText,
          source_ticket_id: ticket?.ticket_id,
          status: 'draft',
          snippet_type: 'internal',
        }),
      });
    } catch (err) {
      console.error('Failed to save to KB:', err);
    }
  };

  const handleImageUpload = async (event) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setUploadingImage(true);

    try {
      const newImages = [];

      for (const file of files) {
        if (!file.type.startsWith('image/')) continue;
        if (file.size > 10 * 1024 * 1024) continue;

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${BACKEND_URL}/api/upload/image`, {
          method: 'POST',
          credentials: 'include',
          body: formData
        });

        if (response.ok) {
          const data = await response.json();
          newImages.push({
            id: data.filename,
            url: `${BACKEND_URL}${data.url}`,
            name: file.name,
            size: data.size
          });
        }
      }

      if (newImages.length > 0) {
        setAttachedImages(prev => [...prev, ...newImages]);
      }
    } catch (error) {
      console.error('Image upload failed:', error);
    } finally {
      setUploadingImage(false);
      if (imageInputRef.current) {
        imageInputRef.current.value = '';
      }
    }
  };

  const removeAttachedImage = (imageId) => {
    setAttachedImages(prev => prev.filter(img => img.id !== imageId));
  };

  const handleDelete = () => {
    if (ticket) {
      onDelete(ticket.id);
    }
  };

  const toggleSection = (section) => {
    setSectionsExpanded(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // --- Modal callback handlers ---

  const handleMerge = async (targetTicketId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ target_ticket_id: targetTicketId })
      });
      if (response.ok) {
        setShowMergeModal(false);
        if (onUpdate) {
          await onUpdate(ticket.id, { _merged: true, _mergedInto: targetTicketId }, true);
        }
        handleCloseWithAnimation();
      }
    } catch (error) {
      console.error('Merge failed:', error);
    }
  };

  // One-click merge: merges the SUGGESTED ticket into the CURRENT ticket
  const handleAcceptMergeSuggestion = async (sourceTicketId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${sourceTicketId}/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ target_ticket_id: ticket.id })
      });
      if (response.ok) {
        // Remove merged suggestion from list
        setMergeSuggestions(prev => prev.filter(s => s.ticket_id !== sourceTicketId));
        // Refresh notes to show newly merged messages
        fetchNotes(ticket.id);
        fetchActivityFeed(ticket.id);
        if (onUpdate) {
          onUpdate(ticket.id, { _suggestionMerged: sourceTicketId });
        }
      }
    } catch (error) {
      console.error('Accept merge suggestion failed:', error);
    }
  };

  const handleLinkTicket = async (targetTicketId, linkType) => {
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
  };

  const handleLinkModalUnlink = async (targetTicketId) => {
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
  };

  const handleSplitTicket = async (splitIndex, newTicketTitle) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/split`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ split_at_index: splitIndex, new_ticket_title: newTicketTitle })
      });
      if (response.ok) {
        const data = await response.json();
        setShowSplitModal(false);
        if (data.updated_ticket?.linked_tickets) {
          setLinkedTickets(data.updated_ticket.linked_tickets);
        }
        fetchNotes(ticket.id);
        onUpdate && onUpdate(ticket.id, { _split: true, new_ticket_id: data.new_ticket_id });
      }
    } catch (error) {
      console.error('Split failed:', error);
    }
  };

  const handleLinkFeatureRequest = async (featureRequestId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets/${ticket.id}/feature-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ feature_request_id: featureRequestId })
      });
      if (response.ok) {
        setShowFeatureRequestModal(false);
        fetchLinkedFeatureRequests(ticket.id);
      }
    } catch (error) {
      console.error('Link to feature request failed:', error);
    }
  };

  // --- Computed values ---

  const getStatusConfig = (status) => STATUSES.find(s => s.value === status) || STATUSES[0];
  const getPriorityConfig = (priority) => PRIORITIES.find(p => p.value === priority) || PRIORITIES[1];
  const getAssignee = () => formData.assignee_id && Array.isArray(users) ? users.find(u => u.id === formData.assignee_id) : null;

  const statusConfig = getStatusConfig(formData.status);
  const priorityConfig = getPriorityConfig(formData.priority);
  const assignee = getAssignee();

  // Build conversation thread from messages only (single source of truth).
  // The notes API now includes type: "original", so we don't inject ticket.description.
  const conversationThread = ticket ? [
    ...notes.map(note => ({
      type: note.type || 'internal_note',
      sender: note.author_name || 'Unknown',
      senderEmail: note.author_email || null,
      subject: note.type === 'original' ? ticket.title : null,
      content: note.content || note.text,
      timestamp: note.created_at,
      isAgentMessage: note.type !== 'customer_reply' && note.type !== 'original',
      original_ticket_id: note.original_ticket_id || null,
      merge_color_index: note.merge_color_index,
      merged_ticket_title: note.merged_ticket_title,
      emailData: (note.email_html || note.source === 'email') ? {
        email_html: note.email_html || '',
        email_text: note.email_text || '',
        email_sender: note.author_email,
      } : null,
      source: note.source || null
    }))
  ].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)) : [];

  return {
    // Animation
    isClosing,
    handleCloseWithAnimation,
    // Form
    formData, setFormData,
    showDeleteConfirm, setShowDeleteConfirm,
    handleDelete,
    // Notes/conversation
    notes,
    inputText, setInputText,
    inputMentions, setInputMentions,
    inputMode, setInputMode,
    loadingNotes, submitting,
    handleSubmitInput,
    handleTypingChange,
    // Images
    attachedImages, uploadingImage, imageInputRef,
    handleImageUpload, removeAttachedImage,
    // CC
    ccEmails, setCcEmails,
    showCcField, setShowCcField,
    // Pickers
    showCannedPicker, setShowCannedPicker,
    handleCannedResponseSelect,
    showKBPicker, setShowKBPicker,
    handleKBInsertLink, handleKBInsertContent,
    // Related tickets
    relatedTickets, loadingRelated,
    // Custom fields
    customFields, customFieldValues, setCustomFieldValues,
    // Assignment
    assignmentOptions, showAssignDropdown, setShowAssignDropdown,
    escalating, handleEscalate, handleAssign, handleAssignToMe, handleAssignToTeam,
    // Star/more/snooze
    isStarred, handleToggleStar,
    showMoreMenu, setShowMoreMenu,
    snoozed, handleToggleSnooze,
    handleCopyLink, handleCopyTicketId, handlePrint, handleOpenInNewTab,
    // Modals
    showMergeModal, setShowMergeModal,
    showLinkModal, setShowLinkModal,
    showSplitModal, setShowSplitModal,
    showFeatureRequestModal, setShowFeatureRequestModal,
    splitMessageIndex, setSplitMessageIndex,
    handleMerge, handleAcceptMergeSuggestion, handleLinkTicket, handleLinkModalUnlink,
    handleSplitTicket, handleLinkFeatureRequest,
    // Linked tickets
    linkedTickets, handleUnlinkTicket,
    // Tags
    ticketTags, tagInput, setTagInput,
    showTagDropdown, setShowTagDropdown,
    availableTags, loadingTags, filteredTags,
    handleAddTag, handleRemoveTag,
    // Activity
    activeTab, setActiveTab,
    activityFeed, loadingActivity,
    // CSAT
    csatData, sendingCsat, handleSendCsat,
    // Feature requests
    linkedFeatureRequests, handleUnlinkFeatureRequest,
    // Merge
    mergedTickets, mergeSuggestions,
    dismissedMergeSuggestions, setDismissedMergeSuggestions,
    messageSourceFilter, setMessageSourceFilter,
    showMergedPanel, setShowMergedPanel,
    handleUnmerge,
    // Sections
    sectionsExpanded, toggleSection,
    // Refs
    conversationRef,
    // Typing
    othersTyping,
    // Computed
    statusConfig, priorityConfig, assignee,
    getStatusConfig, getPriorityConfig,
    conversationThread,
    // KB
    handleSaveToKB,
  };
};

export default useTicketDrawer;
