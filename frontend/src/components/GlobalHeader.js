/**
 * GlobalHeader - Top header with centered search bar
 * Inspired by Stripe's search-centric design
 */

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Search, Command, Plus, X, Bell, ChevronDown } from 'lucide-react';
import { TridentIcon } from './TridentIcon';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const GlobalHeader = ({ user, onCreateTicket, onOpenCommandPalette }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchFocused, setSearchFocused] = useState(false);
  const [quickResults, setQuickResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const searchRef = useRef(null);
  const debounceRef = useRef(null);

  // Get page title based on current route
  const getPageTitle = () => {
    const path = location.pathname;
    const titles = {
      '/dashboard': 'Dashboard',
      '/all-tickets': 'All Tickets',
      '/open-tickets': 'Open Tickets',
      '/waiting-tickets': 'Waiting on Customer',
      '/closed-tickets': 'Closed Tickets',
      '/teams': 'Teams',
      '/leaves': 'Leave Management',
      '/profile': 'Profile',
      '/settings': 'Settings',
      '/admin': 'Admin',
      '/search': 'Search Results',
    };
    return titles[path] || 'Trinity';
  };

  // Quick search as user types
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    
    if (!searchQuery || searchQuery.length < 2) {
      setQuickResults([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const response = await fetch(
          `${BACKEND_URL}/api/search?q=${encodeURIComponent(searchQuery)}&limit=5`,
          { credentials: 'include' }
        );
        if (response.ok) {
          const data = await response.json();
          setQuickResults(data.results?.slice(0, 6) || []);
        }
      } catch (error) {
        console.error('Search error:', error);
      } finally {
        setLoading(false);
      }
    }, 200);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchQuery]);

  // Handle search submission
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
      setSearchFocused(false);
      setQuickResults([]);
    }
  };

  // Handle clicking outside search
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setSearchFocused(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle result click
  const handleResultClick = (result) => {
    setSearchFocused(false);
    setSearchQuery('');
    setQuickResults([]);
    
    // Handle different result types
    switch (result.type) {
      case 'ticket':
        // Navigate to all-tickets and open the ticket drawer
        navigate(`/all-tickets?ticket=${result.id}`);
        // Dispatch event to open ticket drawer
        setTimeout(() => {
          window.dispatchEvent(new CustomEvent('trinity:open-ticket', { detail: { ticketId: result.id } }));
        }, 100);
        break;
      
      case 'user':
        // Navigate to profile page with user param
        navigate(`/profile?user=${result.id}`);
        break;
      
      case 'team':
        // Navigate to teams page and highlight the team
        navigate(`/teams?team=${result.id}`);
        break;
      
      case 'customer':
        // Search for all tickets from this customer
        navigate(`/search?q=customer:${encodeURIComponent(result.email || result.id)}`);
        break;
      
      case 'action':
        // Handle actions
        if (result.action === 'create_ticket' && onCreateTicket) {
          onCreateTicket();
        } else if (result.action === 'create_team') {
          navigate('/teams');
          setTimeout(() => {
            window.dispatchEvent(new CustomEvent('trinity:create-team'));
          }, 100);
        } else if (result.action === 'toggle_theme' || result.action === 'theme_light' || result.action === 'theme_dark') {
          window.dispatchEvent(new CustomEvent('trinity:toggle-theme'));
        } else if (result.action === 'logout') {
          window.location.href = '/login';
        }
        break;
      
      case 'command':
      case 'filter':
      default:
        // Navigation or filter - use the action URL
        if (result.action?.startsWith('/')) {
          navigate(result.action);
        }
        break;
    }
  };

  return (
    <header className="sticky top-0 z-50 h-14 flex items-center justify-between px-4 border-b border-border bg-card">
      {/* Left: Page Title */}
      <div className="flex items-center gap-3 min-w-[200px]">
        <h1 className="text-base font-semibold text-foreground">{getPageTitle()}</h1>
      </div>

      {/* Center: Search Bar */}
      <div ref={searchRef} className="flex-1 max-w-xl mx-4 relative">
        <form onSubmit={handleSearchSubmit}>
          <div 
            className={`
              relative flex items-center h-10 rounded-lg border transition-all duration-200
              ${searchFocused 
                ? 'bg-background border-foreground/30 ring-2 ring-foreground/10' 
                : 'bg-secondary/50 border-border hover:border-foreground/20'
              }
            `}
          >
            <Search size={16} className="absolute left-3 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setSearchFocused(true)}
              placeholder="Search tickets, users, commands..."
              className="w-full h-full pl-9 pr-20 bg-transparent text-[14px] outline-none placeholder:text-muted-foreground/60"
              data-testid="global-search-input"
            />
            <div className="absolute right-2 flex items-center gap-1">
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => { setSearchQuery(''); setQuickResults([]); }}
                  className="p-1 hover:bg-secondary/50 rounded"
                >
                  <X size={14} className="text-muted-foreground" />
                </button>
              )}
              <kbd 
                className="hidden sm:flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium bg-secondary/60 rounded border border-border/40 text-muted-foreground cursor-pointer hover:bg-secondary"
                onClick={(e) => { e.preventDefault(); onOpenCommandPalette?.(); }}
              >
                <Command size={10} />K
              </kbd>
            </div>
          </div>
        </form>

        {/* Quick Results Dropdown */}
        {searchFocused && (searchQuery.length >= 2 || quickResults.length > 0) && (
          <div className="absolute top-full left-0 right-0 mt-2 bg-card rounded-xl border border-border shadow-lg overflow-hidden z-50">
            {loading && (
              <div className="p-4 text-center text-sm text-muted-foreground">
                Searching...
              </div>
            )}
            
            {!loading && quickResults.length > 0 && (
              <div className="max-h-[400px] overflow-y-auto">
                {quickResults.map((result, idx) => (
                  <button
                    key={`${result.type}-${result.id}-${idx}`}
                    onClick={() => handleResultClick(result)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-secondary/50 transition-colors text-left"
                    data-testid={`quick-search-result-${result.type}-${idx}`}
                  >
                    <div className="w-8 h-8 rounded-lg bg-secondary/50 flex items-center justify-center shrink-0">
                      {result.picture ? (
                        <img src={result.picture} alt="" className="w-6 h-6 rounded-full" />
                      ) : (
                        <Search size={14} className="text-muted-foreground" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{result.title}</div>
                      <div className="text-xs text-muted-foreground truncate">{result.subtitle}</div>
                    </div>
                    <span className="text-[10px] text-muted-foreground bg-secondary/50 px-2 py-0.5 rounded shrink-0">
                      {result.category}
                    </span>
                  </button>
                ))}
                
                {/* View all results */}
                <button
                  onClick={handleSearchSubmit}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm text-primary hover:bg-primary/5 border-t border-border/40"
                >
                  View all results for &ldquo;{searchQuery}&rdquo;
                  <ChevronDown size={14} className="rotate-[-90deg]" />
                </button>
              </div>
            )}
            
            {!loading && searchQuery.length >= 2 && quickResults.length === 0 && (
              <div className="p-6 text-center">
                <p className="text-sm text-muted-foreground">No results found</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Try different keywords or use operators like <code className="bg-secondary/50 px-1 rounded">status:open</code>
                </p>
              </div>
            )}
            
            {/* Search tips */}
            {!searchQuery && (
              <div className="p-4 text-xs text-muted-foreground space-y-2">
                <p className="font-medium text-foreground">Search operators:</p>
                <div className="grid grid-cols-2 gap-2">
                  <span><code className="bg-secondary/50 px-1 rounded">status:open</code> Filter by status</span>
                  <span><code className="bg-secondary/50 px-1 rounded">priority:urgent</code> Filter by priority</span>
                  <span><code className="bg-secondary/50 px-1 rounded">assigned:me</code> My tickets</span>
                  <span><code className="bg-secondary/50 px-1 rounded">created:today</code> Recent tickets</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2 min-w-[200px] justify-end">
        <button
          onClick={onCreateTicket}
          className="flex items-center gap-2 h-9 px-4 rounded-lg bg-foreground text-background text-[14px] font-medium hover:bg-foreground/90 transition-colors duration-150 active:scale-[0.98]"
          data-testid="header-create-ticket"
        >
          <Plus size={16} />
          <span className="hidden sm:inline">New Ticket</span>
        </button>
      </div>
    </header>
  );
};

export default GlobalHeader;
