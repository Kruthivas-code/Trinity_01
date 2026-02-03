import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  MessageSquare, Search, Globe, User, X, Eye, Command, Slash,
  ChevronRight, Keyboard, ArrowUp, ArrowDown, CornerDownLeft
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
  const searchInputRef = useRef(null);
  const listRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      fetchResponses();
      // Focus search input when opened
      setTimeout(() => searchInputRef.current?.focus(), 50);
    } else {
      setSearch('');
      setSelectedResponse(null);
      setActiveIndex(0);
    }
  }, [isOpen]);

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
    if (selectedResponse) {
      // In preview mode
      if (e.key === 'Escape') {
        e.preventDefault();
        setSelectedResponse(null);
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
  };

  const handleInsert = () => {
    if (selectedResponse) {
      const filledContent = replacePlaceholders(selectedResponse.content, ticket, user);
      onSelect(filledContent);
      onClose();
    }
  };

  if (!isOpen) return null;

  const previewContent = selectedResponse 
    ? replacePlaceholders(selectedResponse.content, ticket, user)
    : '';

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center" 
      onKeyDown={handleKeyDown}
      data-testid="canned-response-picker-modal"
    >
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-xl mx-4 glass rounded-xl border border-border/60 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-border/60 bg-secondary/20">
          <div className="flex items-center gap-2">
            <MessageSquare size={18} className="text-primary" />
            <h3 className="font-medium text-sm">
              {selectedResponse ? 'Preview & Insert' : 'Select Canned Response'}
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

        {selectedResponse ? (
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
                onClick={() => setSelectedResponse(null)}
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
                  {!search && (
                    <p className="text-xs text-muted-foreground/60 mt-1">
                      Go to Canned Responses page to create some
                    </p>
                  )}
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
            <div className="p-2 border-t border-border/60 bg-secondary/10">
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

export { replacePlaceholders };
export default CannedResponsePicker;
