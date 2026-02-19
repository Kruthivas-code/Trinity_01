import React, { useState, useEffect } from 'react';
import { X, Loader2, Bookmark, FileText } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const FeatureRequestModal = ({ ticket, onClose, onLink }) => {
  const [featureRequests, setFeatureRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateNew, setShowCreateNew] = useState(false);
  const [newFeatureTitle, setNewFeatureTitle] = useState('');
  const [newFeatureDescription, setNewFeatureDescription] = useState('');

  useEffect(() => {
    fetchFeatureRequests();
  }, []);

  const fetchFeatureRequests = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/feature-requests`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setFeatureRequests(data);
      }
    } catch (error) {
      console.error('Failed to fetch feature requests:', error);
    }
    setLoading(false);
  };

  const createAndLink = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/feature-requests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ 
          title: newFeatureTitle, 
          description: newFeatureDescription,
          linked_ticket_id: ticket.id
        })
      });
      if (response.ok) {
        const data = await response.json();
        onLink(data.feature_request_id);
      }
    } catch (error) {
      console.error('Failed to create feature request:', error);
    }
  };

  const filteredRequests = featureRequests.filter(fr => 
    fr.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    fr.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg glass rounded-xl border border-border/60 shadow-2xl">
        <div className="p-4 border-b border-border/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bookmark size={18} className="text-primary" />
              <h3 className="text-base font-semibold">Link to Feature Request</h3>
            </div>
            <button onClick={onClose} className="h-8 w-8 flex items-center justify-center rounded hover:bg-secondary/50">
              <X size={18} />
            </button>
          </div>
        </div>
        
        <div className="p-4 space-y-4">
          {!showCreateNew ? (
            <>
              <div>
                <label className="text-sm font-medium mb-2 block">Search existing feature requests</label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search..."
                  className="w-full h-10 px-3 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              
              <div className="max-h-64 overflow-y-auto space-y-1">
                {loading && (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 size={20} className="animate-spin text-muted-foreground" />
                  </div>
                )}
                {!loading && filteredRequests.map(fr => (
                  <button
                    key={fr.feature_request_id}
                    onClick={() => onLink(fr.feature_request_id)}
                    className="w-full p-3 rounded-lg text-left bg-secondary/30 hover:bg-secondary/50 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                        fr.status === 'planned' ? 'bg-blue-500/20 text-blue-400' :
                        fr.status === 'in_progress' ? 'bg-amber-500/20 text-amber-400' :
                        fr.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' :
                        'bg-secondary text-muted-foreground'
                      }`}>{fr.status}</span>
                      <span className="text-xs text-muted-foreground">{fr.mentions_count || 0} mentions</span>
                    </div>
                    <p className="text-sm font-medium mt-1">{fr.title}</p>
                  </button>
                ))}
                {!loading && filteredRequests.length === 0 && (
                  <p className="text-center text-sm text-muted-foreground py-4">No feature requests found</p>
                )}
              </div>
              
              <button
                onClick={() => setShowCreateNew(true)}
                className="w-full h-10 flex items-center justify-center gap-2 rounded-lg border border-dashed border-border/60 text-sm text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors"
              >
                <FileText size={16} />
                Create new feature request
              </button>
            </>
          ) : (
            <>
              <div>
                <label className="text-sm font-medium mb-2 block">Title</label>
                <input
                  type="text"
                  value={newFeatureTitle}
                  onChange={(e) => setNewFeatureTitle(e.target.value)}
                  placeholder="Feature request title..."
                  className="w-full h-10 px-3 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  autoFocus
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Description</label>
                <textarea
                  value={newFeatureDescription}
                  onChange={(e) => setNewFeatureDescription(e.target.value)}
                  placeholder="Describe the feature request..."
                  rows={4}
                  className="w-full px-3 py-2 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                />
              </div>
            </>
          )}
        </div>
        
        <div className="p-4 border-t border-border/40 flex justify-end gap-2">
          {showCreateNew ? (
            <>
              <button
                onClick={() => setShowCreateNew(false)}
                className="h-9 px-4 text-sm rounded-lg border border-border/40 hover:bg-secondary/50 transition-colors"
              >
                Back
              </button>
              <button
                onClick={createAndLink}
                disabled={!newFeatureTitle.trim()}
                className="h-9 px-4 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Create & Link
              </button>
            </>
          ) : (
            <button
              onClick={onClose}
              className="h-9 px-4 text-sm rounded-lg border border-border/40 hover:bg-secondary/50 transition-colors"
            >
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default FeatureRequestModal;
