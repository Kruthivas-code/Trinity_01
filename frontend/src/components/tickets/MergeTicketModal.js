import React, { useState, useEffect } from 'react';
import { X, Loader2, GitMerge } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

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
                <div className="text-muted-foreground">&rarr;</div>
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

export default MergeTicketModal;
