import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { 
  MessageSquare, Search, Globe, User, X, Eye, Command, Slash,
  ChevronRight, Keyboard, ArrowUp, ArrowDown, CornerDownLeft,
  Plus, Loader2, AlertCircle, Check
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

/**
 * Replaces placeholders in content with actual values from ticket/user context
 */
const replacePlaceholders = (content, ticket, user) => {
  if (!content) return content;
  
  let result = content;
  
  // Customer placeholders
  result = result.replace(/\{\{customer_name\}\}/g, ticket?.customer_name || ticket?.created_by_name || 'Customer');
  result = result.replace(/\{\{customer_email\}\}/g, ticket?.customer_email || ticket?.email_sender || '');
  result = result.replace(/\{\{ticket_id\}\}/g, ticket?.ticket_id || ticket?.id || '');
  result = result.replace(/\{\{ticket_title\}\}/g, ticket?.title || '');
  result = result.replace(/\{\{ticket_subject\}\}/g, ticket?.title || '');
  
  // Agent placeholders
  result = result.replace(/\{\{agent_name\}\}/g, user?.name || 'Agent');
  result = result.replace(/\{\{agent_email\}\}/g, user?.email || '');
  
  return result;
};

/**
 * Converts plain text with newlines to HTML with <br> tags for contenteditable
 */
const textToHtml = (text) => {
  if (!text) return text;
  // Escape HTML entities first
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  // Convert newlines to <br> tags
  return escaped.replace(/\n/g, '<br>');
};

/**
 * Highlight matching text in search results
 */
const HighlightMatch = ({ text, search }) => {
  if (!search || !text) return <span>{text}</span>;
  
  const parts = text.split(new RegExp(`(${search.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
  
  return (
    <span>
      {parts.map((part, i) => 
        part.toLowerCase() === search.toLowerCase() ? (
          <mark key={i} className="bg-primary/30 text-primary rounded px-0.5">{part}</mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </span>
  );
};

/**
 * CannedResponsePicker - Modal/dropdown for selecting canned responses
 * 
 * Props:
 * - isOpen: boolean - whether picker is visible
 * - onClose: function - called when picker is closed
 * - onSelect: function(content) - called with the filled content when a response is selected
 * - ticket: object - current ticket for placeholder replacement
 * - user: object - current user for placeholder replacement
 */
const CannedResponsePicker = ({ isOpen, onClose, onSelect, ticket, user }) => {
  const [responses, setResponses] = useState({ global: [], personal: [] });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedResponse, setSelectedResponse] = useState(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [mode, setMode] = useState('list'); // 'list' | 'preview' | 'create'
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [newResponse, setNewResponse] = useState({
    title: '',
    shortcode: '',
    content: '',
    scope: 'personal'
  });
  const searchInputRef = useRef(null);
  const titleInputRef = useRef(null);
  const listRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      fetchResponses();
      setMode('list');
      setCreateError('');
      setNewResponse({ title: '', shortcode: '', content: '', scope: 'personal' });
      // Focus search input when opened
      setTimeout(() => searchInputRef.current?.focus(), 50);
    } else {
      setSearch('');
      setSelectedResponse(null);
      setActiveIndex(0);
      setMode('list');
    }
  }, [isOpen]);

  // Focus title input when entering create mode
  useEffect(() => {
    if (mode === 'create') {
      setTimeout(() => titleInputRef.current?.focus(), 50);
    }
  }, [mode]);

  const fetchResponses = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BACKEND_URL}/api/canned-responses`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setResponses(data);
      }
    } catch (error) {
      console.error('Failed to fetch canned responses:', error);
    } finally {
      setLoading(false);
    }
  };

  const getFilteredResponses = useCallback(() => {
    // Personal first, then global
    const all = [...(responses.personal || []), ...(responses.global || [])];
    
    if (!search) return all;
    
    const searchLower = search.toLowerCase();
    return all.filter(r => 
      r.title.toLowerCase().includes(searchLower) ||
      r.shortcode.toLowerCase().includes(searchLower) ||
      r.content.toLowerCase().includes(searchLower)
    );
  }, [responses, search]);

  const filteredResponses = getFilteredResponses();

  // Keyboard navigation
  const handleKeyDown = (e) => {
    // In create mode, only handle Escape
    if (mode === 'create') {
      if (e.key === 'Escape') {
        e.preventDefault();
        setMode('list');
        setCreateError('');
      }
      return;
    }

    if (mode === 'preview') {
      // In preview mode
      if (e.key === 'Escape') {
        e.preventDefault();
        setSelectedResponse(null);
        setMode('list');
      } else if (e.key === 'Enter') {
        e.preventDefault();
        handleInsert();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveIndex(prev => Math.min(prev + 1, filteredResponses.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setActiveIndex(prev => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (filteredResponses[activeIndex]) {
          setSelectedResponse(filteredResponses[activeIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        onClose();
        break;
      case 'Tab':
        e.preventDefault();
        if (filteredResponses[activeIndex]) {
          setSelectedResponse(filteredResponses[activeIndex]);
        }
        break;
      default:
        break;
    }
  };

  // Scroll active item into view
  useEffect(() => {
    if (listRef.current && filteredResponses.length > 0) {
      const activeElement = listRef.current.querySelector(`[data-index="${activeIndex}"]`);
      if (activeElement) {
        activeElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }
  }, [activeIndex, filteredResponses.length]);

  // Reset active index when search changes
  useEffect(() => {
    setActiveIndex(0);
  }, [search]);

  const handleSelectResponse = (response) => {
    setSelectedResponse(response);
    setMode('preview');
  };

  const handleInsert = () => {
    if (selectedResponse) {
      const filledContent = replacePlaceholders(selectedResponse.content, ticket, user);
      // Convert newlines to HTML for the RichTextEditor
      const htmlContent = textToHtml(filledContent);
      onSelect(htmlContent);
      onClose();
    }
  };

  const handleCreateResponse = async () => {
    // Validate
    if (!newResponse.title.trim()) {
      setCreateError('Title is required');
      return;
    }
    if (!newResponse.shortcode.trim()) {
      setCreateError('Shortcode is required');
      return;
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(newResponse.shortcode.trim())) {
      setCreateError('Shortcode can only contain letters, numbers, hyphens, and underscores');
      return;
    }
    if (!newResponse.content.trim()) {
      setCreateError('Content is required');
      return;
    }

    setCreating(true);
    setCreateError('');

    try {
      const response = await fetch(`${BACKEND_URL}/api/canned-responses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          title: newResponse.title.trim(),
          shortcode: newResponse.shortcode.trim().toLowerCase(),
          content: newResponse.content.trim(),
          scope: newResponse.scope
        })
      });

      if (response.ok) {
        const created = await response.json();
        // Refresh the list
        await fetchResponses();
        // Switch to preview of the newly created response
        setSelectedResponse(created);
        setMode('preview');
        setNewResponse({ title: '', shortcode: '', content: '', scope: 'personal' });
      } else {
        const err = await response.json();
        setCreateError(err.detail || 'Failed to create canned response');
      }
    } catch (error) {
      console.error('Failed to create canned response:', error);
      setCreateError('Network error. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  if (!isOpen) return null;

  const previewContent = selectedResponse 
    ? replacePlaceholders(selectedResponse.content, ticket, user)
    : '';

  const modalContent = (
    <div 
      className="fixed inset-0 z-[9999] flex items-center justify-center" 
      onKeyDown={handleKeyDown}
      data-testid="canned-response-picker-modal"
    >
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-xl mx-4 glass rounded-xl border border-border/60 shadow-2xl overflow-hidden max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-border/60 bg-secondary/20">
          <div className="flex items-center gap-2">
            <MessageSquare size={18} className="text-primary" />
            <h3 className="font-medium text-sm">
              {mode === 'create' ? 'Create New Response' : mode === 'preview' ? 'Preview & Insert' : 'Select Canned Response'}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-secondary transition-colors"
            data-testid="canned-picker-close"
          >
            <X size={16} />
          </button>
        </div>

        {mode === 'create' ? (
          // Create Mode
          <div className="flex flex-col">
            <div className="p-4 space-y-3 flex-1 max-h-[60vh] overflow-y-auto">
              {/* Title */}
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Title</label>
                <input
                  ref={titleInputRef}
                  type="text"
                  placeholder="e.g. Welcome greeting"
                  value={newResponse.title}
                  onChange={(e) => { setNewResponse(prev => ({ ...prev, title: e.target.value })); setCreateError(''); }}
                  className="w-full h-9 px-3 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground/60"
                  data-testid="create-canned-title"
                  maxLength={100}
                />
              </div>

              {/* Shortcode */}
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Shortcode <span className="text-muted-foreground/50">(type /{'{shortcode}'} to quick-insert)</span>
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">/</span>
                  <input
                    type="text"
                    placeholder="e.g. welcome"
                    value={newResponse.shortcode}
                    onChange={(e) => { 
                      const val = e.target.value.replace(/[^a-zA-Z0-9_-]/g, '');
                      setNewResponse(prev => ({ ...prev, shortcode: val })); 
                      setCreateError(''); 
                    }}
                    className="w-full h-9 pl-7 pr-3 rounded-lg bg-secondary/50 border border-border text-sm font-mono focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground/60"
                    data-testid="create-canned-shortcode"
                    maxLength={50}
                  />
                </div>
              </div>

              {/* Content */}
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Content</label>
                <textarea
                  placeholder="Type your canned response content here...&#10;&#10;Available placeholders: {{customer_name}}, {{ticket_id}}, {{agent_name}}"
                  value={newResponse.content}
                  onChange={(e) => { setNewResponse(prev => ({ ...prev, content: e.target.value })); setCreateError(''); }}
                  className="w-full h-32 px-3 py-2 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground/60 resize-none"
                  data-testid="create-canned-content"
                  maxLength={5000}
                />
                <p className="text-[10px] text-muted-foreground/60 mt-1">{newResponse.content.length}/5000 characters</p>
              </div>

              {/* Scope */}
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">Visibility</label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setNewResponse(prev => ({ ...prev, scope: 'personal' }))}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                      newResponse.scope === 'personal'
                        ? 'bg-amber-500/10 border-amber-500/30 text-amber-700'
                        : 'border-border hover:bg-secondary/50 text-muted-foreground'
                    }`}
                    data-testid="create-scope-personal"
                  >
                    <User size={13} />
                    Personal
                  </button>
                  <button
                    type="button"
                    onClick={() => setNewResponse(prev => ({ ...prev, scope: 'global' }))}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                      newResponse.scope === 'global'
                        ? 'bg-primary/10 border-primary/30 text-primary'
                        : 'border-border hover:bg-secondary/50 text-muted-foreground'
                    }`}
                    data-testid="create-scope-global"
                  >
                    <Globe size={13} />
                    Global (all agents)
                  </button>
                </div>
              </div>

              {/* Error */}
              {createError && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-red-600" data-testid="create-canned-error">
                  <AlertCircle size={14} className="shrink-0" />
                  {createError}
                </div>
              )}
            </div>

            {/* Create Footer */}
            <div className="flex items-center justify-between p-3 border-t border-border/60 bg-secondary/10">
              <button
                onClick={() => { setMode('list'); setCreateError(''); }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg hover:bg-secondary transition-colors"
                data-testid="create-canned-back"
              >
                <ChevronRight size={14} className="rotate-180" />
                Back
              </button>
              <button
                onClick={handleCreateResponse}
                disabled={creating || !newResponse.title.trim() || !newResponse.shortcode.trim() || !newResponse.content.trim()}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="create-canned-submit"
              >
                {creating ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Check size={14} />
                    Create Response
                  </>
                )}
              </button>
            </div>
          </div>
        ) : mode === 'preview' ? (
          // Preview Mode
          <div className="flex flex-col">
            <div className="p-4 flex-1">
              <div className="flex items-center gap-2 mb-3">
                {selectedResponse.scope === 'global' ? (
                  <Globe size={14} className="text-primary" />
                ) : (
                  <User size={14} className="text-amber-500" />
                )}
                <span className="font-medium text-sm">{selectedResponse.title}</span>
                <span className="text-xs font-mono text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">
                  /{selectedResponse.shortcode}
                </span>
              </div>
              
              <div>
                <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
                  <Eye size={12} />
                  Preview (placeholders resolved)
                </div>
                <div 
                  className="p-3 bg-secondary/50 rounded-lg text-sm whitespace-pre-wrap max-h-48 overflow-y-auto border border-border/30"
                  data-testid="canned-preview-content"
                >
                  {previewContent}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 border-t border-border/60 bg-secondary/10">
              <button
                onClick={() => { setSelectedResponse(null); setMode('list'); }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg hover:bg-secondary transition-colors"
                data-testid="canned-back-btn"
              >
                <ChevronRight size={14} className="rotate-180" />
                Back
              </button>
              <button
                onClick={handleInsert}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium shadow-lg shadow-primary/20"
                data-testid="canned-insert-btn"
              >
                Insert into Reply
                <CornerDownLeft size={14} />
              </button>
            </div>
          </div>
        ) : (
          // List Mode
          <>
            {/* Search */}
            <div className="p-3 border-b border-border/60">
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  ref={searchInputRef}
                  type="text"
                  placeholder="Search by title, shortcode, or content..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full h-9 pl-9 pr-3 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground/60"
                  data-testid="canned-picker-search"
                />
              </div>
              {search && (
                <p className="text-xs text-muted-foreground mt-2">
                  {filteredResponses.length} result{filteredResponses.length !== 1 ? 's' : ''} found
                </p>
              )}
            </div>

            {/* Response List */}
            <div ref={listRef} className="max-h-80 overflow-y-auto">
              {loading ? (
                <div className="p-6 text-center">
                  <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                    Loading responses...
                  </div>
                </div>
              ) : filteredResponses.length === 0 ? (
                <div className="p-8 text-center">
                  <MessageSquare size={32} className="mx-auto text-muted-foreground/30 mb-3" />
                  <p className="text-sm text-muted-foreground">
                    {search ? 'No responses match your search' : 'No canned responses yet'}
                  </p>
                  <button
                    onClick={() => {
                      setMode('create');
                      // Pre-fill shortcode from search if applicable
                      if (search && /^[a-zA-Z0-9_-]+$/.test(search)) {
                        setNewResponse(prev => ({ ...prev, shortcode: search.toLowerCase() }));
                      }
                    }}
                    className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                    data-testid="canned-create-from-empty"
                  >
                    <Plus size={14} />
                    Create New Response
                  </button>
                </div>
              ) : (
                <div className="p-2 space-y-0.5">
                  {/* Group by scope */}
                  {responses.personal?.length > 0 && filteredResponses.some(r => r.scope === 'personal') && (
                    <>
                      <div className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                        <User size={11} />
                        My Responses
                      </div>
                      {filteredResponses
                        .filter(r => r.scope === 'personal')
                        .map((response, idx) => {
                          const globalIdx = filteredResponses.indexOf(response);
                          return (
                            <button
                              key={response.response_id}
                              data-index={globalIdx}
                              onClick={() => handleSelectResponse(response)}
                              className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors group ${
                                activeIndex === globalIdx 
                                  ? 'bg-primary/15 ring-1 ring-primary/30' 
                                  : 'hover:bg-secondary/70'
                              }`}
                              data-testid={`picker-response-${response.response_id}`}
                            >
                              <div className="flex items-center justify-between gap-2">
                                <span className="font-medium text-sm truncate">
                                  <HighlightMatch text={response.title} search={search} />
                                </span>
                                <span className={`text-xs font-mono px-1.5 py-0.5 rounded transition-colors ${
                                  activeIndex === globalIdx
                                    ? 'bg-primary/20 text-primary'
                                    : 'bg-secondary text-muted-foreground group-hover:text-primary'
                                }`}>
                                  /{response.shortcode}
                                </span>
                              </div>
                              <p className="text-xs text-muted-foreground truncate mt-1 leading-relaxed">
                                {response.content.substring(0, 100)}{response.content.length > 100 ? '...' : ''}
                              </p>
                            </button>
                          );
                        })}
                    </>
                  )}
                  
                  {/* Global responses */}
                  {responses.global?.length > 0 && filteredResponses.some(r => r.scope === 'global') && (
                    <>
                      <div className="px-2 py-1.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5 mt-2">
                        <Globe size={11} />
                        Global Responses
                      </div>
                      {filteredResponses
                        .filter(r => r.scope === 'global')
                        .map((response, idx) => {
                          const globalIdx = filteredResponses.indexOf(response);
                          return (
                            <button
                              key={response.response_id}
                              data-index={globalIdx}
                              onClick={() => handleSelectResponse(response)}
                              className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors group ${
                                activeIndex === globalIdx 
                                  ? 'bg-primary/15 ring-1 ring-primary/30' 
                                  : 'hover:bg-secondary/70'
                              }`}
                              data-testid={`picker-response-${response.response_id}`}
                            >
                              <div className="flex items-center justify-between gap-2">
                                <span className="font-medium text-sm truncate">
                                  <HighlightMatch text={response.title} search={search} />
                                </span>
                                <span className={`text-xs font-mono px-1.5 py-0.5 rounded transition-colors ${
                                  activeIndex === globalIdx
                                    ? 'bg-primary/20 text-primary'
                                    : 'bg-secondary text-muted-foreground group-hover:text-primary'
                                }`}>
                                  /{response.shortcode}
                                </span>
                              </div>
                              <p className="text-xs text-muted-foreground truncate mt-1 leading-relaxed">
                                {response.content.substring(0, 100)}{response.content.length > 100 ? '...' : ''}
                              </p>
                            </button>
                          );
                        })}
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Footer with keyboard hints */}
            <div className="p-2 border-t border-border/60 bg-secondary/10 shrink-0">
              <div className="flex items-center justify-center gap-4 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1">
                  <kbd className="px-1 py-0.5 bg-secondary rounded text-[9px]"><ArrowUp size={9} /></kbd>
                  <kbd className="px-1 py-0.5 bg-secondary rounded text-[9px]"><ArrowDown size={9} /></kbd>
                  Navigate
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-secondary rounded text-[9px]">Enter</kbd>
                  Select
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-secondary rounded text-[9px]">Esc</kbd>
                  Close
                </span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );

  // Use portal to render at document body level
  return createPortal(modalContent, document.body);
};

/**
 * ShortcodeAutocomplete - Dropdown for /shortcode autocomplete
 * Renders inline near the cursor position
 */
export const ShortcodeAutocomplete = ({ 
  suggestions, 
  activeIndex, 
  onSelect, 
  position,
  ticket,
  user 
}) => {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div 
      className="absolute z-50 glass rounded-lg border border-border/60 shadow-xl py-1 min-w-[280px] max-w-[400px] max-h-[200px] overflow-y-auto"
      style={{ 
        left: position?.left || 0, 
        bottom: position?.bottom || '100%',
        transform: 'translateY(-4px)'
      }}
      data-testid="shortcode-autocomplete"
    >
      {suggestions.map((response, idx) => (
        <button
          key={response.response_id}
          onClick={() => onSelect(idx)}
          className={`w-full text-left px-3 py-2 transition-colors ${
            idx === activeIndex 
              ? 'bg-primary/15' 
              : 'hover:bg-secondary/70'
          }`}
        >
          <div className="flex items-center gap-2">
            {response.scope === 'personal' ? (
              <User size={11} className="text-amber-500 shrink-0" />
            ) : (
              <Globe size={11} className="text-primary shrink-0" />
            )}
            <span className="font-medium text-sm truncate">{response.title}</span>
            <span className="text-xs font-mono text-muted-foreground bg-secondary px-1 py-0.5 rounded ml-auto shrink-0">
              /{response.shortcode}
            </span>
          </div>
          <p className="text-xs text-muted-foreground truncate mt-0.5 pl-4">
            {response.content.substring(0, 60)}...
          </p>
        </button>
      ))}
      <div className="px-3 py-1.5 border-t border-border/40 text-[10px] text-muted-foreground text-center">
        <kbd className="px-1 py-0.5 bg-secondary rounded">Tab</kbd> or <kbd className="px-1 py-0.5 bg-secondary rounded">Enter</kbd> to insert
      </div>
    </div>
  );
};

/**
 * Hook for shortcode autocomplete in textareas
 * 
 * Returns:
 * - suggestions: array of matching responses
 * - activeSuggestionIndex: current highlighted suggestion
 * - showSuggestions: whether to show the dropdown
 * - handleKeyDown: attach to textarea's onKeyDown
 * - handleChange: call when textarea value changes
 * - selectSuggestion: call when a suggestion is clicked
 * - hideSuggestions: manually hide the dropdown
 */
export const useCannedResponseAutocomplete = (ticket, user) => {
  const [responses, setResponses] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(0);
  const [triggerPosition, setTriggerPosition] = useState(null);

  // Fetch responses on mount
  useEffect(() => {
    const fetchResponses = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/canned-responses`, {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          // Combine personal (priority) and global
          setResponses([...(data.personal || []), ...(data.global || [])]);
        }
      } catch (error) {
        console.error('Failed to fetch canned responses:', error);
      }
    };
    fetchResponses();
  }, []);

  const handleChange = useCallback((value, cursorPosition) => {
    // Find if we're in a shortcode context (typing after /)
    const textBeforeCursor = value.substring(0, cursorPosition);
    const lastSlashIndex = textBeforeCursor.lastIndexOf('/');
    
    if (lastSlashIndex === -1) {
      setShowSuggestions(false);
      return;
    }
    
    // Check if the slash is at start of line or after whitespace
    const charBeforeSlash = textBeforeCursor[lastSlashIndex - 1];
    if (lastSlashIndex > 0 && charBeforeSlash && !/\s/.test(charBeforeSlash)) {
      setShowSuggestions(false);
      return;
    }
    
    // Get the shortcode being typed
    const shortcodeQuery = textBeforeCursor.substring(lastSlashIndex + 1).toLowerCase();
    
    // Check if there's whitespace after the query (means shortcode is complete)
    if (/\s/.test(shortcodeQuery)) {
      setShowSuggestions(false);
      return;
    }
    
    // Filter responses
    const matching = responses.filter(r => 
      r.shortcode.toLowerCase().startsWith(shortcodeQuery) ||
      r.title.toLowerCase().includes(shortcodeQuery)
    ).slice(0, 5);
    
    if (matching.length > 0) {
      setSuggestions(matching);
      setShowSuggestions(true);
      setActiveSuggestionIndex(0);
      setTriggerPosition(lastSlashIndex);
    } else {
      setShowSuggestions(false);
    }
  }, [responses]);

  const selectSuggestion = useCallback((index, currentValue, cursorPosition) => {
    const response = suggestions[index];
    if (!response || triggerPosition === null) return null;
    
    // Replace the shortcode with the response content
    const textBeforeTrigger = currentValue.substring(0, triggerPosition);
    const textAfterCursor = currentValue.substring(cursorPosition);
    const filledContent = replacePlaceholders(response.content, ticket, user);
    
    const newValue = textBeforeTrigger + filledContent + textAfterCursor;
    const newCursorPosition = triggerPosition + filledContent.length;
    
    setShowSuggestions(false);
    setSuggestions([]);
    
    return { newValue, newCursorPosition };
  }, [suggestions, triggerPosition, ticket, user]);

  const handleKeyDown = useCallback((e, currentValue, cursorPosition) => {
    if (!showSuggestions) return false;
    
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveSuggestionIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        return true;
        
      case 'ArrowUp':
        e.preventDefault();
        setActiveSuggestionIndex(prev => prev > 0 ? prev - 1 : prev);
        return true;
        
      case 'Tab':
      case 'Enter':
        if (suggestions.length > 0) {
          e.preventDefault();
          return selectSuggestion(activeSuggestionIndex, currentValue, cursorPosition);
        }
        return false;
        
      case 'Escape':
        e.preventDefault();
        setShowSuggestions(false);
        return true;
        
      default:
        return false;
    }
  }, [showSuggestions, suggestions, activeSuggestionIndex, selectSuggestion]);

  const hideSuggestions = useCallback(() => {
    setShowSuggestions(false);
  }, []);

  return {
    suggestions,
    activeSuggestionIndex,
    showSuggestions,
    handleKeyDown,
    handleChange,
    selectSuggestion,
    hideSuggestions
  };
};

export { replacePlaceholders, textToHtml };
export default CannedResponsePicker;
