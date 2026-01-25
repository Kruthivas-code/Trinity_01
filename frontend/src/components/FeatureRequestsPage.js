import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Bookmark, Plus, ChevronRight, Search, Filter, 
  TrendingUp, Users, Calendar, MessageSquare, CheckCircle,
  Clock, ArrowUpRight, X, ExternalLink, ChevronDown,
  Bug, Sparkles, Zap
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const STATUS_CONFIG = {
  new: { label: 'New', color: 'bg-slate-500/20 text-slate-400', dotColor: 'bg-slate-400' },
  planned: { label: 'Planned', color: 'bg-blue-500/20 text-blue-400', dotColor: 'bg-blue-400' },
  in_progress: { label: 'In Progress', color: 'bg-amber-500/20 text-amber-400', dotColor: 'bg-amber-400' },
  completed: { label: 'Completed', color: 'bg-emerald-500/20 text-emerald-400', dotColor: 'bg-emerald-400' },
  archived: { label: 'Archived', color: 'bg-muted text-muted-foreground', dotColor: 'bg-muted-foreground' },
};

const TYPE_CONFIG = {
  feature: { label: 'Feature', color: 'bg-purple-500/20 text-purple-400', icon: Sparkles },
  bug_fix: { label: 'Bug Fix', color: 'bg-red-500/20 text-red-400', icon: Bug },
  enhancement: { label: 'Enhancement', color: 'bg-blue-500/20 text-blue-400', icon: Zap },
};

const PRIORITY_CONFIG = {
  low: { label: 'Low', color: 'bg-green-500/20 text-green-400' },
  medium: { label: 'Medium', color: 'bg-yellow-500/20 text-yellow-400' },
  high: { label: 'High', color: 'bg-orange-500/20 text-orange-400' },
  critical: { label: 'Critical', color: 'bg-red-500/20 text-red-400' },
};

const FeatureRequestsPage = ({ user }) => {
  const navigate = useNavigate();
  const [featureRequests, setFeatureRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [sortBy, setSortBy] = useState('mentions'); // mentions, created, updated
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState({
    new: true,
    planned: true,
    in_progress: true,
    completed: false,
    archived: false
  });

  const fetchFeatureRequests = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    fetchFeatureRequests();
  }, [fetchFeatureRequests]);

  const filteredRequests = featureRequests.filter(fr => {
    const matchesSearch = !searchQuery || 
      fr.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      fr.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || fr.status === statusFilter;
    const matchesType = typeFilter === 'all' || fr.request_type === typeFilter;
    return matchesSearch && matchesStatus && matchesType;
  });

  const sortedRequests = [...filteredRequests].sort((a, b) => {
    switch (sortBy) {
      case 'mentions':
        return (b.mentions_count || 0) - (a.mentions_count || 0);
      case 'created':
        return new Date(b.created_at) - new Date(a.created_at);
      case 'updated':
        return new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at);
      default:
        return 0;
    }
  });

  // Group by status
  const groupedRequests = sortedRequests.reduce((acc, fr) => {
    const status = fr.status || 'new';
    if (!acc[status]) acc[status] = [];
    acc[status].push(fr);
    return acc;
  }, {});

  const toggleGroup = (status) => {
    setExpandedGroups(prev => ({ ...prev, [status]: !prev[status] }));
  };

  const stats = {
    total: featureRequests.length,
    new: featureRequests.filter(fr => fr.status === 'new').length,
    planned: featureRequests.filter(fr => fr.status === 'planned').length,
    inProgress: featureRequests.filter(fr => fr.status === 'in_progress').length,
    completed: featureRequests.filter(fr => fr.status === 'completed').length,
    totalMentions: featureRequests.reduce((sum, fr) => sum + (fr.mentions_count || 0), 0)
  };

  const handleCreateRequest = async (title, description) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/feature-requests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ title, description })
      });
      if (response.ok) {
        fetchFeatureRequests();
        setShowCreateModal(false);
      }
    } catch (error) {
      console.error('Failed to create feature request:', error);
    }
  };

  const handleUpdateStatus = async (featureRequestId, newStatus) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/feature-requests/${featureRequestId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ status: newStatus })
      });
      if (response.ok) {
        fetchFeatureRequests();
      }
    } catch (error) {
      console.error('Failed to update status:', error);
    }
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="glass rounded-xl p-6">
          <div className="animate-pulse text-foreground">Loading feature requests...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150">
        <div className="px-4 md:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bookmark size={20} className="text-primary" />
            <h1 className="text-lg font-semibold">Feature Requests</h1>
            <span className="text-sm text-muted-foreground">
              Track and prioritize product improvements
            </span>
          </div>
          
          <button
            onClick={() => setShowCreateModal(true)}
            className="h-9 px-4 flex items-center gap-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-interactive"
            data-testid="create-feature-request-btn"
          >
            <Plus size={16} />
            New Request
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="px-4 md:px-6 py-4 border-b border-border/30">
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary/30">
            <Bookmark size={16} className="text-primary" />
            <span className="text-sm">{stats.total} Total</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-500/10">
            <div className="w-2 h-2 rounded-full bg-slate-400" />
            <span className="text-sm">{stats.new} New</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-500/10">
            <div className="w-2 h-2 rounded-full bg-blue-400" />
            <span className="text-sm">{stats.planned} Planned</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/10">
            <div className="w-2 h-2 rounded-full bg-amber-400" />
            <span className="text-sm">{stats.inProgress} In Progress</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-500/10">
            <CheckCircle size={16} className="text-emerald-400" />
            <span className="text-sm">{stats.completed} Completed</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary/10 ml-auto">
            <MessageSquare size={16} className="text-primary" />
            <span className="text-sm font-medium">{stats.totalMentions} Total Mentions</span>
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="px-4 md:px-6 py-3 flex items-center gap-3 border-b border-border/30">
        <div className="flex-1 relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search feature requests..."
            className="w-full max-w-md h-9 pl-9 pr-3 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 px-3 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="all">All Statuses</option>
            <option value="new">New</option>
            <option value="planned">Planned</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="archived">Archived</option>
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="h-9 px-3 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="mentions">Most Mentioned</option>
            <option value="created">Recently Created</option>
            <option value="updated">Recently Updated</option>
          </select>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        {sortedRequests.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <Bookmark size={48} className="text-muted-foreground/30 mb-4" />
            <h3 className="text-lg font-medium mb-2">No feature requests found</h3>
            <p className="text-muted-foreground text-sm mb-4">
              {searchQuery ? 'Try adjusting your search' : 'Create your first feature request to get started'}
            </p>
            {!searchQuery && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="h-9 px-4 flex items-center gap-2 rounded-lg bg-primary text-primary-foreground text-sm"
              >
                <Plus size={16} />
                Create Feature Request
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(STATUS_CONFIG).map(([status, config]) => {
              const items = groupedRequests[status] || [];
              if (items.length === 0 && statusFilter !== 'all' && statusFilter !== status) return null;
              
              return (
                <div key={status} className="space-y-2">
                  <button
                    onClick={() => toggleGroup(status)}
                    className="w-full flex items-center justify-between py-2 hover:bg-secondary/20 rounded-lg px-2 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${config.dotColor}`} />
                      <span className="text-sm font-medium">{config.label}</span>
                      <span className="text-xs text-muted-foreground">({items.length})</span>
                    </div>
                    {expandedGroups[status] ? (
                      <ChevronDown size={16} className="text-muted-foreground" />
                    ) : (
                      <ChevronRight size={16} className="text-muted-foreground" />
                    )}
                  </button>
                  
                  {expandedGroups[status] && items.length > 0 && (
                    <div className="space-y-2 ml-4">
                      {items.map(fr => (
                        <FeatureRequestCard
                          key={fr.feature_request_id}
                          request={fr}
                          statusConfig={config}
                          onClick={() => setSelectedRequest(fr)}
                          onStatusChange={handleUpdateStatus}
                        />
                      ))}
                    </div>
                  )}
                  
                  {expandedGroups[status] && items.length === 0 && (
                    <p className="text-sm text-muted-foreground ml-4 py-2">No items</p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <CreateFeatureRequestModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateRequest}
        />
      )}

      {/* Detail Drawer */}
      {selectedRequest && (
        <FeatureRequestDrawer
          request={selectedRequest}
          onClose={() => setSelectedRequest(null)}
          onStatusChange={handleUpdateStatus}
          onRefresh={fetchFeatureRequests}
        />
      )}
    </div>
  );
};

// Feature Request Card Component
const FeatureRequestCard = ({ request, statusConfig, onClick, onStatusChange }) => {
  const [showStatusMenu, setShowStatusMenu] = useState(false);

  return (
    <div
      className="p-4 rounded-lg bg-card border border-border/40 hover:border-primary/30 transition-colors cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-muted-foreground">{request.feature_request_id}</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${statusConfig.color}`}>
              {statusConfig.label}
            </span>
          </div>
          <h3 className="text-sm font-medium truncate">{request.title}</h3>
          {request.description && (
            <p className="text-xs text-muted-foreground line-clamp-2 mt-1">{request.description}</p>
          )}
        </div>
        
        <div className="flex items-center gap-4 shrink-0">
          <div className="flex items-center gap-1 text-primary">
            <MessageSquare size={14} />
            <span className="text-sm font-medium">{request.mentions_count || 0}</span>
          </div>
          <div className="flex items-center gap-1 text-muted-foreground">
            <Users size={14} />
            <span className="text-sm">{request.linked_tickets?.length || 0}</span>
          </div>
          <div className="relative" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setShowStatusMenu(!showStatusMenu)}
              className="h-7 px-2 text-xs rounded border border-border/40 hover:bg-secondary/50 transition-colors"
            >
              Change Status
            </button>
            
            {showStatusMenu && (
              <div className="absolute right-0 top-8 z-10 w-36 bg-popover border border-border rounded-lg shadow-xl py-1">
                {Object.entries(STATUS_CONFIG).map(([status, config]) => (
                  <button
                    key={status}
                    onClick={() => {
                      onStatusChange(request.feature_request_id, status);
                      setShowStatusMenu(false);
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 text-left"
                  >
                    <div className={`w-2 h-2 rounded-full ${config.dotColor}`} />
                    {config.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      
      <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <Calendar size={12} />
          <span>Created {new Date(request.created_at).toLocaleDateString()}</span>
        </div>
        {request.linked_tickets?.length > 0 && (
          <div className="flex items-center gap-1">
            <ExternalLink size={12} />
            <span>{request.linked_tickets.length} linked ticket(s)</span>
          </div>
        )}
      </div>
    </div>
  );
};

// Create Feature Request Modal
const CreateFeatureRequestModal = ({ onClose, onCreate }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg glass rounded-xl border border-border/60 shadow-2xl">
        <div className="p-4 border-b border-border/40">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bookmark size={18} className="text-primary" />
              <h3 className="text-base font-semibold">Create Feature Request</h3>
            </div>
            <button onClick={onClose} className="h-8 w-8 flex items-center justify-center rounded hover:bg-secondary/50">
              <X size={18} />
            </button>
          </div>
        </div>
        
        <div className="p-4 space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Title *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Feature request title..."
              className="w-full h-10 px-3 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              autoFocus
            />
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the feature request..."
              rows={4}
              className="w-full px-3 py-2 rounded-lg bg-secondary/50 border border-border/40 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
            />
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
            onClick={() => onCreate(title, description)}
            disabled={!title.trim()}
            className="h-9 px-4 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Create
          </button>
        </div>
      </div>
    </div>
  );
};

// Feature Request Drawer
const FeatureRequestDrawer = ({ request, onClose, onStatusChange, onRefresh }) => {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchDetails();
  }, [request.feature_request_id]);

  const fetchDetails = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/feature-requests/${request.feature_request_id}`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setDetails(data);
      }
    } catch (error) {
      console.error('Failed to fetch details:', error);
    }
    setLoading(false);
  };

  const statusConfig = STATUS_CONFIG[request.status || 'new'];

  return (
    <>
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
        onClick={onClose}
      />
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-xl z-[60] bg-card border-l border-border/40 shadow-2xl flex flex-col">
        {/* Header */}
        <div className="h-14 px-4 flex items-center justify-between border-b border-border/40 shrink-0">
          <div className="flex items-center gap-2">
            <Bookmark size={18} className="text-primary" />
            <span className="font-medium">{request.feature_request_id}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${statusConfig.color}`}>
              {statusConfig.label}
            </span>
          </div>
          <button
            onClick={onClose}
            className="h-8 w-8 flex items-center justify-center rounded hover:bg-secondary/50"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          <div>
            <h2 className="text-lg font-semibold mb-2">{request.title}</h2>
            <p className="text-sm text-muted-foreground">{request.description || 'No description'}</p>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary/10">
              <MessageSquare size={16} className="text-primary" />
              <span className="text-sm font-medium">{request.mentions_count || 0} mentions</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary/50">
              <Users size={16} />
              <span className="text-sm">{details?.linked_ticket_details?.length || 0} tickets</span>
            </div>
          </div>

          {/* Status Change */}
          <div>
            <label className="text-sm font-medium mb-2 block">Status</label>
            <div className="flex flex-wrap gap-2">
              {Object.entries(STATUS_CONFIG).map(([status, config]) => (
                <button
                  key={status}
                  onClick={() => {
                    onStatusChange(request.feature_request_id, status);
                    onRefresh();
                  }}
                  className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
                    request.status === status 
                      ? config.color 
                      : 'bg-secondary/30 hover:bg-secondary/50'
                  }`}
                >
                  {config.label}
                </button>
              ))}
            </div>
          </div>

          {/* Linked Tickets */}
          <div>
            <h3 className="text-sm font-medium mb-3">Linked Tickets</h3>
            {loading ? (
              <div className="text-sm text-muted-foreground">Loading...</div>
            ) : details?.linked_ticket_details?.length > 0 ? (
              <div className="space-y-2">
                {details.linked_ticket_details.map(ticket => (
                  <button
                    key={ticket.ticket_id}
                    onClick={() => navigate(`/all-tickets?ticket=${ticket.ticket_id}`)}
                    className="w-full p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors text-left"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-muted-foreground">{ticket.ticket_id}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                        ticket.status === 'resolved' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-500/20 text-blue-400'
                      }`}>{ticket.status}</span>
                    </div>
                    <p className="text-sm truncate mt-1">{ticket.title}</p>
                    <div className="text-xs text-muted-foreground mt-1">
                      {ticket.customer_email}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No linked tickets yet</p>
            )}
          </div>

          {/* Metadata */}
          <div className="text-xs text-muted-foreground space-y-1 border-t border-border/30 pt-4">
            <p>Created: {new Date(request.created_at).toLocaleString()}</p>
            {request.updated_at && (
              <p>Updated: {new Date(request.updated_at).toLocaleString()}</p>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

export default FeatureRequestsPage;
