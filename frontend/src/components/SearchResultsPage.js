/**
 * SearchResultsPage - Dedicated search results page
 * Full-featured search with filters, sorting, and export
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { 
  Search, Filter, X, Ticket, User, Users, Settings, Zap,
  Clock, FileText, ChevronDown, ChevronRight, Loader2,
  ArrowUpDown, Download, Bookmark, AlertCircle, Building
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Category icons
const categoryIcons = {
  'Tickets': Ticket,
  'Users': User,
  'Teams': Users,
  'Customers': Building,
  'Navigation': Settings,
  'Actions': Zap,
  'Admin': Settings,
  'Quick Filters': Filter,
  'Shifts': Clock,
  'Routing Rules': FileText,
  'Custom Fields': FileText,
};

// Priority colors
const priorityColors = {
  urgent: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-green-500/20 text-green-400 border-green-500/30',
};

// Status colors
const statusColors = {
  'open': 'bg-blue-500/20 text-blue-400',
  'in-progress': 'bg-purple-500/20 text-purple-400',
  'waiting': 'bg-yellow-500/20 text-yellow-400',
  'closed': 'bg-gray-500/20 text-gray-400',
};

const SearchResultsPage = ({ user }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [results, setResults] = useState([]);
  const [resultsByCategory, setResultsByCategory] = useState({});
  const [operators, setOperators] = useState({});
  const [loading, setLoading] = useState(false);
  const [totalResults, setTotalResults] = useState(0);
  
  // Filters
  const [activeFilters, setActiveFilters] = useState({
    type: searchParams.get('type') || null,
    status: null,
    priority: null,
  });
  const [showFilters, setShowFilters] = useState(true);
  const [expandedCategories, setExpandedCategories] = useState({});

  // Perform search
  const performSearch = useCallback(async (searchQuery, filters = {}) => {
    if (!searchQuery) {
      setResults([]);
      setResultsByCategory({});
      return;
    }

    setLoading(true);
    try {
      let url = `${BACKEND_URL}/api/search?q=${encodeURIComponent(searchQuery)}&limit=20`;
      if (filters.type) {
        url += `&type=${filters.type}`;
      }
      
      const response = await fetch(url, { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setResults(data.results || []);
        setResultsByCategory(data.by_category || {});
        setOperators(data.operators || {});
        setTotalResults(data.total || 0);
        
        // Auto-expand categories with results
        const expanded = {};
        Object.keys(data.by_category || {}).forEach(cat => {
          if (data.by_category[cat]?.length > 0) {
            expanded[cat] = true;
          }
        });
        setExpandedCategories(expanded);
      }
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Search when query changes
  useEffect(() => {
    const q = searchParams.get('q');
    if (q) {
      setQuery(q);
      performSearch(q, activeFilters);
    }
  }, [searchParams, performSearch, activeFilters]);

  // Handle search submit
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      setSearchParams({ q: query.trim() });
    }
  };

  // Handle result click
  const handleResultClick = (result) => {
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
        setSearchParams({ q: `customer:${result.email || result.id}` });
        break;
      
      case 'shift':
      case 'routing_rule':
      case 'custom_field':
        // Navigate to admin page with appropriate tab
        if (result.action?.startsWith('/')) {
          navigate(result.action);
        }
        break;
      
      case 'action':
        // Handle actions
        if (result.action === 'create_ticket') {
          window.dispatchEvent(new CustomEvent('trinity:create-ticket'));
        } else if (result.action === 'create_team') {
          navigate('/teams');
          setTimeout(() => {
            window.dispatchEvent(new CustomEvent('trinity:create-team'));
          }, 100);
        } else if (result.action === 'toggle_theme' || result.action === 'theme_light' || result.action === 'theme_dark') {
          window.dispatchEvent(new CustomEvent('trinity:toggle-theme'));
        } else if (result.action === 'export_tickets') {
          handleExport();
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

  // Toggle category expansion
  const toggleCategory = (category) => {
    setExpandedCategories(prev => ({
      ...prev,
      [category]: !prev[category]
    }));
  };

  // Filter by type
  const filterByType = (type) => {
    setActiveFilters(prev => ({
      ...prev,
      type: prev.type === type ? null : type
    }));
    if (query) {
      performSearch(query, { ...activeFilters, type: activeFilters.type === type ? null : type });
    }
  };

  // Export results
  const handleExport = () => {
    const ticketResults = results.filter(r => r.type === 'ticket');
    if (ticketResults.length === 0) {
      alert('No tickets to export');
      return;
    }
    
    const csv = [
      ['ID', 'Title', 'Status', 'Priority', 'Customer', 'Created'],
      ...ticketResults.map(t => [
        t.id,
        t.title,
        t.status || '',
        t.priority || '',
        t.customer_email || '',
        t.created_at || ''
      ])
    ].map(row => row.join(',')).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `search-results-${Date.now()}.csv`;
    a.click();
  };

  // Get filter counts
  const getTypeCounts = () => {
    const counts = {};
    results.forEach(r => {
      counts[r.type] = (counts[r.type] || 0) + 1;
    });
    return counts;
  };
  const typeCounts = getTypeCounts();

  return (
    <div className="h-full flex flex-col">
      {/* Search Header */}
      <div className="sticky top-0 z-40 bg-background/95 backdrop-blur-sm border-b border-border/50">
        <div className="p-4">
          <form onSubmit={handleSearchSubmit} className="max-w-3xl mx-auto">
            <div className="relative">
              <Search size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search everything... (try: status:open priority:urgent)"
                className="w-full h-12 pl-12 pr-4 rounded-xl bg-secondary/40 border border-border/50 focus:border-primary/50 focus:ring-2 focus:ring-primary/20 outline-none text-base transition-all"
                data-testid="search-page-input"
              />
              {loading && (
                <Loader2 size={20} className="absolute right-4 top-1/2 -translate-y-1/2 animate-spin text-muted-foreground" />
              )}
            </div>
          </form>
          
          {/* Active operators display */}
          {Object.keys(operators).length > 0 && (
            <div className="flex items-center gap-2 mt-3 max-w-3xl mx-auto">
              <span className="text-xs text-muted-foreground">Active filters:</span>
              {Object.entries(operators).map(([key, value]) => (
                <span 
                  key={key}
                  className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary border border-primary/20"
                >
                  {key}:{value}
                </span>
              ))}
            </div>
          )}
        </div>
        
        {/* Results summary bar */}
        {query && !loading && (
          <div className="px-4 pb-3 flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Found <span className="font-medium text-foreground">{totalResults}</span> results for "{query}"
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  showFilters ? 'bg-primary/10 text-primary' : 'hover:bg-secondary/50'
                }`}
              >
                <Filter size={14} />
                Filters
              </button>
              <button
                onClick={handleExport}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm hover:bg-secondary/50 transition-colors"
              >
                <Download size={14} />
                Export
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <div className="flex">
          {/* Filters Sidebar */}
          {showFilters && query && (
            <aside className="w-56 shrink-0 border-r border-border/50 p-4 space-y-6">
              {/* Type Filter */}
              <div>
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                  Result Type
                </h3>
                <div className="space-y-1">
                  {[
                    { value: 'ticket', label: 'Tickets', icon: Ticket },
                    { value: 'user', label: 'Users', icon: User },
                    { value: 'team', label: 'Teams', icon: Users },
                    { value: 'customer', label: 'Customers', icon: Building },
                    { value: 'command', label: 'Commands', icon: Zap },
                  ].map(({ value, label, icon: Icon }) => (
                    <button
                      key={value}
                      onClick={() => filterByType(value)}
                      className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                        activeFilters.type === value
                          ? 'bg-primary/10 text-primary'
                          : 'hover:bg-secondary/50'
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        <Icon size={14} />
                        {label}
                      </span>
                      {typeCounts[value] && (
                        <span className="text-xs bg-secondary/50 px-1.5 py-0.5 rounded">
                          {typeCounts[value]}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* Quick Filters */}
              <div>
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                  Quick Filters
                </h3>
                <div className="space-y-1">
                  {[
                    { query: 'status:open', label: 'Open tickets' },
                    { query: 'priority:urgent', label: 'Urgent' },
                    { query: 'assigned:me', label: 'Assigned to me' },
                    { query: 'created:today', label: 'Created today' },
                  ].map(({ query: q, label }) => (
                    <button
                      key={q}
                      onClick={() => setSearchParams({ q: `${query} ${q}`.trim() })}
                      className="w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-secondary/50 transition-colors"
                    >
                      + {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Search Tips */}
              <div className="text-xs text-muted-foreground space-y-1.5 pt-4 border-t border-border/50">
                <p className="font-medium text-foreground">Search operators</p>
                <p><code className="bg-secondary/50 px-1 rounded">status:open</code></p>
                <p><code className="bg-secondary/50 px-1 rounded">priority:urgent</code></p>
                <p><code className="bg-secondary/50 px-1 rounded">team:support</code></p>
                <p><code className="bg-secondary/50 px-1 rounded">customer:@email</code></p>
                <p><code className="bg-secondary/50 px-1 rounded">created:last-week</code></p>
              </div>
            </aside>
          )}

          {/* Results */}
          <main className="flex-1 p-4">
            {/* Loading */}
            {loading && (
              <div className="flex items-center justify-center py-20">
                <Loader2 size={32} className="animate-spin text-primary" />
              </div>
            )}

            {/* No query */}
            {!query && !loading && (
              <div className="text-center py-20">
                <Search size={48} className="mx-auto mb-4 text-muted-foreground/30" />
                <h2 className="text-xl font-semibold mb-2">Search Trinity</h2>
                <p className="text-muted-foreground mb-6">
                  Search for tickets, users, teams, customers, and more
                </p>
                <div className="max-w-md mx-auto text-left space-y-2 text-sm">
                  <p className="font-medium">Try these searches:</p>
                  <button 
                    onClick={() => setSearchParams({ q: 'status:open' })}
                    className="block w-full text-left px-4 py-2 rounded-lg bg-secondary/30 hover:bg-secondary/50"
                  >
                    <code>status:open</code> - All open tickets
                  </button>
                  <button 
                    onClick={() => setSearchParams({ q: 'priority:urgent created:today' })}
                    className="block w-full text-left px-4 py-2 rounded-lg bg-secondary/30 hover:bg-secondary/50"
                  >
                    <code>priority:urgent created:today</code> - Urgent tickets from today
                  </button>
                  <button 
                    onClick={() => setSearchParams({ q: 'assigned:me' })}
                    className="block w-full text-left px-4 py-2 rounded-lg bg-secondary/30 hover:bg-secondary/50"
                  >
                    <code>assigned:me</code> - My tickets
                  </button>
                </div>
              </div>
            )}

            {/* No results */}
            {query && !loading && results.length === 0 && (
              <div className="text-center py-20">
                <AlertCircle size={48} className="mx-auto mb-4 text-muted-foreground/30" />
                <h2 className="text-xl font-semibold mb-2">No results found</h2>
                <p className="text-muted-foreground">
                  No matches for "{query}". Try different keywords or operators.
                </p>
              </div>
            )}

            {/* Results by category */}
            {query && !loading && results.length > 0 && (
              <div className="space-y-4">
                {Object.entries(resultsByCategory).map(([category, items]) => {
                  if (!items || items.length === 0) return null;
                  
                  const Icon = categoryIcons[items[0]?.category] || FileText;
                  const isExpanded = expandedCategories[category] !== false;
                  
                  return (
                    <div key={category} className="card-premium rounded-xl overflow-hidden">
                      {/* Category Header */}
                      <button
                        onClick={() => toggleCategory(category)}
                        className="w-full flex items-center justify-between px-4 py-3 hover:bg-secondary/30 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Icon size={16} className="text-primary" />
                          <span className="font-medium capitalize">{category.replace('_', ' ')}</span>
                          <span className="text-xs text-muted-foreground bg-secondary/50 px-2 py-0.5 rounded-full">
                            {items.length}
                          </span>
                        </div>
                        {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </button>
                      
                      {/* Category Items */}
                      {isExpanded && (
                        <div className="border-t border-border/30">
                          {items.map((result, idx) => (
                            <button
                              key={`${result.type}-${result.id}-${idx}`}
                              onClick={() => handleResultClick(result)}
                              className="w-full flex items-center gap-4 px-4 py-3 hover:bg-secondary/30 transition-colors text-left border-b border-border/20 last:border-b-0"
                              data-testid={`search-result-${result.type}-${idx}`}
                            >
                              {/* Icon/Avatar */}
                              <div className="w-10 h-10 rounded-lg bg-secondary/50 flex items-center justify-center shrink-0">
                                {result.picture ? (
                                  <img src={result.picture} alt="" className="w-8 h-8 rounded-full" />
                                ) : (
                                  <Icon size={18} className="text-muted-foreground" />
                                )}
                              </div>
                              
                              {/* Content */}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium truncate">{result.title}</span>
                                  {result.priority && (
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${priorityColors[result.priority]}`}>
                                      {result.priority}
                                    </span>
                                  )}
                                  {result.status && (
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${statusColors[result.status]}`}>
                                      {result.status}
                                    </span>
                                  )}
                                </div>
                                <p className="text-sm text-muted-foreground truncate mt-0.5">
                                  {result.subtitle}
                                </p>
                              </div>
                              
                              {/* Meta */}
                              <div className="text-right shrink-0">
                                {result.created_at && (
                                  <p className="text-xs text-muted-foreground">
                                    {new Date(result.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true })}
                                  </p>
                                )}
                              </div>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
};

export default SearchResultsPage;
