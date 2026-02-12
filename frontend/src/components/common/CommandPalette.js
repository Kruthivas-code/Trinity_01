/**
 * Trinity Command Palette (Cmd+K / Ctrl+K)
 * Universal search across tickets, users, teams, and platform features
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, Command, ArrowRight, Ticket, User, Users, 
  Settings, LayoutDashboard, Zap, Clock, FileText,
  Loader2, X, ArrowUp, ArrowDown, CornerDownLeft
} from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Category icons
const categoryIcons = {
  'Navigation': LayoutDashboard,
  'Actions': Zap,
  'Admin': Settings,
  'Tickets': Ticket,
  'Users': User,
  'Teams': Users,
  'Shifts': Clock,
  'Routing Rules': FileText,
};

// Priority colors for tickets
const priorityColors = {
  urgent: 'text-red-400',
  high: 'text-orange-400',
  medium: 'text-yellow-400',
  low: 'text-green-400',
};

const CommandPalette = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [recentSearches, setRecentSearches] = useState([]);
  const inputRef = useRef(null);
  const resultsRef = useRef(null);
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();
  const debounceRef = useRef(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setResults([]);
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
      
      // Load recent searches from localStorage
      const recent = JSON.parse(localStorage.getItem('trinity_recent_searches') || '[]');
      setRecentSearches(recent.slice(0, 5));
    }
  }, [isOpen]);

  // Search function with debounce
  const performSearch = useCallback(async (searchQuery) => {
    if (!searchQuery || searchQuery.length < 2) {
      setResults([]);
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `${BACKEND_URL}/api/search?q=${encodeURIComponent(searchQuery)}&limit=5`,
        { credentials: 'include' }
      );
      
      if (response.ok) {
        const data = await response.json();
        setResults(data.results || []);
        setSelectedIndex(0);
      }
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    
    debounceRef.current = setTimeout(() => {
      performSearch(query);
    }, 200);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query, performSearch]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev => 
            prev < results.length - 1 ? prev + 1 : 0
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev => 
            prev > 0 ? prev - 1 : results.length - 1
          );
          break;
        case 'Enter':
          e.preventDefault();
          if (results[selectedIndex]) {
            handleSelect(results[selectedIndex]);
          }
          break;
        case 'Escape':
          onClose();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, results, selectedIndex, onClose]);

  // Scroll selected item into view
  useEffect(() => {
    if (resultsRef.current && results.length > 0) {
      const selectedElement = resultsRef.current.children[selectedIndex];
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex, results.length]);

  // Handle item selection
  const handleSelect = (item) => {
    // Save to recent searches
    if (query) {
      const recent = JSON.parse(localStorage.getItem('trinity_recent_searches') || '[]');
      const filtered = recent.filter(r => r !== query);
      localStorage.setItem('trinity_recent_searches', JSON.stringify([query, ...filtered].slice(0, 10)));
    }

    // Handle different result types
    switch (item.type) {
      case 'ticket':
        // Open ticket drawer
        onClose();
        navigate(`/all-tickets?ticket=${item.id}`);
        setTimeout(() => {
          window.dispatchEvent(new CustomEvent('trinity:open-ticket', { detail: { ticketId: item.id } }));
        }, 100);
        break;
      
      case 'user':
        // Navigate to user profile
        onClose();
        navigate(`/profile?user=${item.id}`);
        break;
      
      case 'team':
        // Navigate to teams page and highlight
        onClose();
        navigate(`/teams?team=${item.id}`);
        break;
      
      case 'customer':
        // Search for customer's tickets
        onClose();
        navigate(`/search?q=customer:${encodeURIComponent(item.email || item.id)}`);
        break;
      
      case 'action':
        // Execute action
        switch (item.action) {
          case 'create_ticket':
            onClose();
            window.dispatchEvent(new CustomEvent('trinity:create-ticket'));
            break;
          case 'create_team':
            onClose();
            navigate('/teams');
            setTimeout(() => {
              window.dispatchEvent(new CustomEvent('trinity:create-team'));
            }, 100);
            break;
          case 'export':
          case 'export_tickets':
          case 'export_users':
            onClose();
            navigate('/settings');
            break;
          case 'toggle_theme':
          case 'theme_light':
          case 'theme_dark':
            setTheme(theme === 'dark' ? 'light' : 'dark');
            onClose();
            break;
          case 'logout':
            onClose();
            window.location.href = '/login';
            break;
          default:
            break;
        }
        break;
      
      case 'command':
      case 'filter':
      case 'shift':
      case 'routing_rule':
      case 'custom_field':
      default:
        // Navigation - use the action URL
        if (item.action?.startsWith('/')) {
          onClose();
          navigate(item.action);
        }
        break;
    }
  };

  // Handle recent search click
  const handleRecentSearch = (searchTerm) => {
    setQuery(searchTerm);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-2xl mx-4 glass rounded-xl border border-border/60 shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-4 duration-200">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border/40">
          <Search size={20} className="text-muted-foreground shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search tickets, users, teams, or type a command..."
            className="flex-1 bg-transparent text-base outline-none placeholder:text-muted-foreground/60"
            data-testid="command-palette-input"
          />
          {loading && <Loader2 size={18} className="animate-spin text-muted-foreground" />}
          <kbd className="hidden sm:flex items-center gap-1 px-2 py-1 text-[10px] font-medium bg-secondary/60 rounded border border-border/40 text-muted-foreground">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div 
          ref={resultsRef}
          className="max-h-[400px] overflow-y-auto"
          data-testid="command-palette-results"
        >
          {/* Recent searches (when no query) */}
          {!query && recentSearches.length > 0 && (
            <div className="p-2">
              <div className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Recent Searches
              </div>
              {recentSearches.map((term, idx) => (
                <button
                  key={idx}
                  onClick={() => handleRecentSearch(term)}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left hover:bg-secondary/50 transition-interactive text-sm"
                >
                  <Clock size={16} className="text-muted-foreground" />
                  <span>{term}</span>
                </button>
              ))}
            </div>
          )}

          {/* Quick actions (when no query) */}
          {!query && (
            <div className="p-2 border-t border-border/30">
              <div className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Quick Actions
              </div>
              {[
                { icon: Ticket, label: 'Create new ticket', action: 'create_ticket' },
                { icon: LayoutDashboard, label: 'Go to Dashboard', path: '/dashboard' },
                { icon: Settings, label: 'Toggle theme', action: 'toggle_theme' },
              ].map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => item.path ? navigate(item.path) || onClose() : handleSelect({ type: 'action', action: item.action })}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left hover:bg-secondary/50 transition-interactive text-sm"
                >
                  <item.icon size={16} className="text-primary" />
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          )}

          {/* Search results */}
          {query && results.length > 0 && (
            <div className="p-2">
              {results.map((item, idx) => {
                const Icon = categoryIcons[item.category] || FileText;
                const isSelected = idx === selectedIndex;
                
                return (
                  <button
                    key={`${item.type}-${item.id}`}
                    onClick={() => handleSelect(item)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    className={`
                      w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-interactive
                      ${isSelected ? 'bg-primary/15 text-foreground' : 'hover:bg-secondary/50'}
                    `}
                    data-testid={`search-result-${item.id}`}
                  >
                    <div className={`
                      w-8 h-8 rounded-lg flex items-center justify-center shrink-0
                      ${isSelected ? 'bg-primary/20' : 'bg-secondary/50'}
                    `}>
                      {item.picture ? (
                        <img src={item.picture} alt="" className="w-6 h-6 rounded-full" />
                      ) : (
                        <Icon size={16} className={isSelected ? 'text-primary' : 'text-muted-foreground'} />
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium truncate">{item.title}</span>
                        {item.type === 'ticket' && item.priority && (
                          <span className={`text-xs ${priorityColors[item.priority]}`}>
                            {item.priority}
                          </span>
                        )}
                      </div>
                      {item.description && (
                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                          {item.description}
                        </p>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[10px] text-muted-foreground bg-secondary/50 px-2 py-0.5 rounded">
                        {item.category}
                      </span>
                      {isSelected && (
                        <ArrowRight size={14} className="text-primary" />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* No results */}
          {query && query.length >= 2 && !loading && results.length === 0 && (
            <div className="p-8 text-center text-muted-foreground">
              <Search size={32} className="mx-auto mb-3 opacity-30" />
              <p>No results found for &quot;{query}&quot;</p>
              <p className="text-sm mt-1">Try searching for tickets, users, or commands</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-2.5 border-t border-border/40 text-xs text-muted-foreground bg-secondary/20">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <ArrowUp size={12} />
              <ArrowDown size={12} />
              navigate
            </span>
            <span className="flex items-center gap-1.5">
              <CornerDownLeft size={12} />
              select
            </span>
          </div>
          <span className="flex items-center gap-1.5">
            <Command size={12} />
            K to open
          </span>
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;
