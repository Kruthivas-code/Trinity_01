import React, { useState, useEffect } from 'react';
import { X, Loader2, Link } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const LinkTicketModal = ({ ticket, linkedTickets, onClose, onLink, onUnlink }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [linkType, setLinkType] = useState('related');

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
                {linkedTickets.map(link => {
                  const getLinkTypeLabel = (type) => {
                    switch (type) {
                      case 'split_from': return 'Split from';
                      case 'split_to': return 'Split to';
                      case 'blocks': return 'Blocks';
                      case 'blocked_by': return 'Blocked by';
                      case 'duplicates': return 'Duplicates';
                      default: return 'Related to';
                    }
                  };
                  return (
                    <div key={link.ticket_id} className="flex items-center justify-between p-2 rounded-lg bg-secondary/30">
                      <div>
                        <span className="text-xs text-muted-foreground">{getLinkTypeLabel(link.link_type)}</span>
                        <p className="text-sm font-medium">{link.ticket_id} - {link.title}</p>
                      </div>
                      <button 
                        onClick={() => onUnlink(link.ticket_id)}
                        className="h-7 w-7 flex items-center justify-center rounded hover:bg-red-500/20 text-red-400"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  );
                })}
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

export default LinkTicketModal;
