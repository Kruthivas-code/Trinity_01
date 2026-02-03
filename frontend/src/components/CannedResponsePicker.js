import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  MessageSquare, Search, Globe, User, X, Eye
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
  
  // Agent placeholders
  result = result.replace(/\{\{agent_name\}\}/g, user?.name || 'Agent');
  result = result.replace(/\{\{agent_email\}\}/g, user?.email || '');
  
  return result;
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
  const searchInputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      fetchResponses();
      // Focus search input when opened
      setTimeout(() => searchInputRef.current?.focus(), 100);
    } else {
      setSearch('');
      setSelectedResponse(null);
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
    const all = [...(responses.personal || []), ...(responses.global || [])];
    
    if (!search) return all;
    
    const searchLower = search.toLowerCase();
    return all.filter(r => 
      r.title.toLowerCase().includes(searchLower) ||
      r.shortcode.toLowerCase().includes(searchLower) ||
      r.content.toLowerCase().includes(searchLower)
    );
  }, [responses, search]);

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

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      if (selectedResponse) {
        setSelectedResponse(null);
      } else {
        onClose();
      }
    }
  };

  if (!isOpen) return null;

  const filteredResponses = getFilteredResponses();
  const previewContent = selectedResponse 
    ? replacePlaceholders(selectedResponse.content, ticket, user)
    : '';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" onKeyDown={handleKeyDown}>
      <div 
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-lg mx-4 glass rounded-xl border border-border/60 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-border/60">
          <div className="flex items-center gap-2">
            <MessageSquare size={18} className="text-primary" />
            <h3 className="font-medium">
              {selectedResponse ? 'Preview Response' : 'Canned Responses'}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-secondary transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {selectedResponse ? (
          // Preview Mode
          <div className="p-4">
            <div className="flex items-center gap-2 mb-3">
              {selectedResponse.scope === 'global' ? (
                <Globe size={14} className="text-primary" />
              ) : (
                <User size={14} className="text-amber-500" />
              )}
              <span className="font-medium">{selectedResponse.title}</span>
              <span className="text-xs font-mono text-muted-foreground">
                /{selectedResponse.shortcode}
              </span>
            </div>
            
            <div className="mb-4">
              <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
                <Eye size={12} />
                Preview (with placeholders filled)
              </div>
              <div className="p-3 bg-secondary/50 rounded-lg text-sm whitespace-pre-wrap max-h-60 overflow-y-auto">
                {previewContent}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setSelectedResponse(null)}
                className="px-3 py-1.5 text-sm rounded-lg hover:bg-secondary transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleInsert}
                className="px-4 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                data-testid="insert-canned-response-btn"
              >
                Insert into Reply
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
                  placeholder="Search responses or type shortcode..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full h-9 pl-9 pr-3 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  data-testid="search-canned-picker"
                />
              </div>
            </div>

            {/* Response List */}
            <div className="max-h-80 overflow-y-auto">
              {loading ? (
                <div className="p-4 text-center text-muted-foreground text-sm">
                  Loading...
                </div>
              ) : filteredResponses.length === 0 ? (
                <div className="p-6 text-center">
                  <MessageSquare size={24} className="mx-auto text-muted-foreground/40 mb-2" />
                  <p className="text-sm text-muted-foreground">No responses found</p>
                </div>
              ) : (
                <div className="p-2 space-y-1">
                  {/* Personal responses first */}
                  {responses.personal?.length > 0 && filteredResponses.some(r => r.scope === 'personal') && (
                    <>
                      <div className="px-2 py-1 text-xs font-medium text-muted-foreground flex items-center gap-1">
                        <User size={12} />
                        Personal
                      </div>
                      {filteredResponses
                        .filter(r => r.scope === 'personal')
                        .map(response => (
                          <button
                            key={response.response_id}
                            onClick={() => handleSelectResponse(response)}
                            className="w-full text-left px-3 py-2 rounded-lg hover:bg-secondary/70 transition-colors group"
                            data-testid={`picker-response-${response.response_id}`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-sm truncate">{response.title}</span>
                              <span className="text-xs font-mono text-muted-foreground group-hover:text-primary">
                                /{response.shortcode}
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground truncate mt-0.5">
                              {response.content.substring(0, 80)}...
                            </p>
                          </button>
                        ))}
                    </>
                  )}
                  
                  {/* Global responses */}
                  {responses.global?.length > 0 && filteredResponses.some(r => r.scope === 'global') && (
                    <>
                      <div className="px-2 py-1 text-xs font-medium text-muted-foreground flex items-center gap-1 mt-2">
                        <Globe size={12} />
                        Global
                      </div>
                      {filteredResponses
                        .filter(r => r.scope === 'global')
                        .map(response => (
                          <button
                            key={response.response_id}
                            onClick={() => handleSelectResponse(response)}
                            className="w-full text-left px-3 py-2 rounded-lg hover:bg-secondary/70 transition-colors group"
                            data-testid={`picker-response-${response.response_id}`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-sm truncate">{response.title}</span>
                              <span className="text-xs font-mono text-muted-foreground group-hover:text-primary">
                                /{response.shortcode}
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground truncate mt-0.5">
                              {response.content.substring(0, 80)}...
                            </p>
                          </button>
                        ))}
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Footer hint */}
            <div className="p-2 border-t border-border/60 text-xs text-muted-foreground text-center">
              Press <kbd className="px-1.5 py-0.5 bg-secondary rounded">Esc</kbd> to close
            </div>
          </>
        )}
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
