import React, { useState, useRef, useEffect, useCallback } from 'react';
import { AtSign } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * MentionInput - A textarea with @mention autocomplete functionality
 * 
 * Props:
 * - value: Current text value
 * - onChange: Callback when text changes (receives text, mentions array)
 * - onSubmit: Callback when user submits (Enter key)
 * - placeholder: Placeholder text
 * - className: Additional CSS classes
 * - disabled: Disable input
 */
const MentionInput = ({ 
  value = '', 
  onChange, 
  onSubmit, 
  placeholder = 'Add a note... Use @ to mention someone',
  className = '',
  disabled = false,
  rows = 3
}) => {
  const [users, setUsers] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestionFilter, setSuggestionFilter] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [mentionStartIndex, setMentionStartIndex] = useState(-1);
  const textareaRef = useRef(null);
  const suggestionsRef = useRef(null);

  // Fetch users for autocomplete
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/users`, {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          setUsers(data);
        }
      } catch (error) {
        console.error('Failed to fetch users:', error);
      }
    };
    fetchUsers();
  }, []);

  // Filter users based on current search term
  const filteredUsers = users.filter(user => 
    user.name?.toLowerCase().includes(suggestionFilter.toLowerCase()) ||
    user.email?.toLowerCase().includes(suggestionFilter.toLowerCase())
  ).slice(0, 5);

  // Extract mentions from text
  const extractMentions = useCallback((text) => {
    const mentionRegex = /@\[([^\]]+)\]\(([^)]+)\)/g;
    const mentions = [];
    let match;
    while ((match = mentionRegex.exec(text)) !== null) {
      mentions.push(match[2]); // user_id
    }
    return mentions;
  }, []);

  // Handle text change
  const handleChange = (e) => {
    const newValue = e.target.value;
    const newCursorPos = e.target.selectionStart;
    setCursorPosition(newCursorPos);

    // Check if we should show mention suggestions
    const textBeforeCursor = newValue.slice(0, newCursorPos);
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');
    
    // Check if @ is at start or preceded by whitespace
    if (lastAtIndex !== -1) {
      const charBeforeAt = lastAtIndex > 0 ? textBeforeCursor[lastAtIndex - 1] : ' ';
      const textAfterAt = textBeforeCursor.slice(lastAtIndex + 1);
      
      // Show suggestions if @ is at valid position and no space after @
      if ((charBeforeAt === ' ' || charBeforeAt === '\n' || lastAtIndex === 0) && !textAfterAt.includes(' ')) {
        setMentionStartIndex(lastAtIndex);
        setSuggestionFilter(textAfterAt);
        setShowSuggestions(true);
        setSelectedIndex(0);
      } else {
        setShowSuggestions(false);
        setMentionStartIndex(-1);
      }
    } else {
      setShowSuggestions(false);
      setMentionStartIndex(-1);
    }

    // Call onChange with value and extracted mentions
    const mentions = extractMentions(newValue);
    onChange?.(newValue, mentions);
  };

  // Insert mention into text
  const insertMention = (user) => {
    if (mentionStartIndex === -1) return;

    const beforeMention = value.slice(0, mentionStartIndex);
    const afterMention = value.slice(cursorPosition);
    
    // Format: @[Display Name](user_id)
    const mentionText = `@[${user.name}](${user.user_id || user.id}) `;
    const newValue = beforeMention + mentionText + afterMention;
    
    // Extract all mentions
    const mentions = extractMentions(newValue);
    
    onChange?.(newValue, mentions);
    setShowSuggestions(false);
    setMentionStartIndex(-1);

    // Move cursor to end of mention
    const newCursorPos = beforeMention.length + mentionText.length;
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
      }
    }, 0);
  };

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
    if (showSuggestions && filteredUsers.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, filteredUsers.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        insertMention(filteredUsers[selectedIndex]);
      } else if (e.key === 'Escape') {
        setShowSuggestions(false);
      }
    } else if (e.key === 'Enter' && !e.shiftKey && !showSuggestions) {
      e.preventDefault();
      onSubmit?.();
    }
  };

  // Convert stored format to display format for rendering
  const getDisplayValue = () => {
    return value;
  };

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(e.target) &&
          textareaRef.current && !textareaRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative">
      <textarea
        ref={textareaRef}
        value={getDisplayValue()}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={rows}
        className={`w-full px-3 py-2 rounded-lg bg-secondary/50 border border-border 
          focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none ${className}`}
        data-testid="mention-input"
      />
      
      {/* @ hint */}
      {!value && (
        <div className="absolute right-3 top-2.5 flex items-center gap-1 text-muted-foreground/50 pointer-events-none">
          <AtSign size={14} />
          <span className="text-xs">mention</span>
        </div>
      )}

      {/* Suggestions dropdown */}
      {showSuggestions && filteredUsers.length > 0 && (
        <div
          ref={suggestionsRef}
          className="absolute z-50 mt-1 w-64 bg-card border border-border rounded-lg shadow-xl overflow-hidden"
          data-testid="mention-suggestions"
        >
          <div className="px-3 py-2 text-xs text-muted-foreground border-b border-border bg-secondary/30">
            Mention a team member
          </div>
          {filteredUsers.map((user, index) => (
            <button
              key={user.user_id || user.id}
              onClick={() => insertMention(user)}
              onMouseEnter={() => setSelectedIndex(index)}
              className={`w-full flex items-center gap-3 px-3 py-2 text-left transition-colors ${
                index === selectedIndex ? 'bg-primary/10' : 'hover:bg-secondary/50'
              }`}
              data-testid={`mention-suggestion-${index}`}
            >
              <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-sm text-primary font-medium shrink-0">
                {user.name?.charAt(0).toUpperCase() || '?'}
              </div>
              <div className="min-w-0">
                <div className="font-medium text-sm truncate">{user.name}</div>
                <div className="text-xs text-muted-foreground truncate">{user.email}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * Helper function to render text with mentions highlighted
 * Converts @[Name](id) format to styled spans
 */
export const renderTextWithMentions = (text, users = []) => {
  if (!text) return null;
  
  // Match @[Display Name](user_id)
  const mentionRegex = /@\[([^\]]+)\]\(([^)]+)\)/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = mentionRegex.exec(text)) !== null) {
    // Add text before mention
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    
    // Add mention as styled element
    const displayName = match[1];
    const userId = match[2];
    parts.push(
      <span 
        key={match.index} 
        className="inline-flex items-center px-1.5 py-0.5 rounded bg-primary/20 text-primary text-sm font-medium"
        data-user-id={userId}
      >
        @{displayName}
      </span>
    );
    
    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : text;
};

/**
 * Extract plain text display from mention format
 * Converts @[Name](id) to @Name
 */
export const getPlainTextFromMentions = (text) => {
  if (!text) return '';
  return text.replace(/@\[([^\]]+)\]\([^)]+\)/g, '@$1');
};

export default MentionInput;
