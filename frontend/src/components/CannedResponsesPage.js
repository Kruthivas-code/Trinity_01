import React, { useState, useEffect } from 'react';
import { 
  Plus, Search, Edit2, Trash2, Globe, User, 
  MessageSquare, Copy, Check, X, AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

const PLACEHOLDERS = [
  { key: '{{customer_name}}', label: 'Customer Name' },
  { key: '{{customer_email}}', label: 'Customer Email' },
  { key: '{{ticket_id}}', label: 'Ticket ID' },
  { key: '{{ticket_title}}', label: 'Ticket Title' },
  { key: '{{agent_name}}', label: 'Your Name' },
  { key: '{{agent_email}}', label: 'Your Email' },
];

const CannedResponsesPage = ({ user }) => {
  const [responses, setResponses] = useState({ global: [], personal: [] });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [scopeFilter, setScopeFilter] = useState('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingResponse, setEditingResponse] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    shortcode: '',
    content: '',
    scope: 'global'
  });
  const [errors, setErrors] = useState({});
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    fetchResponses();
  }, []);

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
      toast.error('Failed to load canned responses');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (response = null) => {
    if (response) {
      setEditingResponse(response);
      setFormData({
        title: response.title,
        shortcode: response.shortcode,
        content: response.content,
        scope: response.scope
      });
    } else {
      setEditingResponse(null);
      setFormData({
        title: '',
        shortcode: '',
        content: '',
        scope: 'global'
      });
    }
    setErrors({});
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingResponse(null);
    setFormData({ title: '', shortcode: '', content: '', scope: 'global' });
    setErrors({});
  };

  const validateForm = () => {
    const newErrors = {};
    if (!formData.title.trim()) newErrors.title = 'Title is required';
    if (!formData.shortcode.trim()) newErrors.shortcode = 'Shortcode is required';
    else if (!/^[a-zA-Z0-9_-]+$/.test(formData.shortcode)) {
      newErrors.shortcode = 'Only letters, numbers, hyphens and underscores allowed';
    }
    if (!formData.content.trim()) newErrors.content = 'Content is required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    try {
      const url = editingResponse 
        ? `${BACKEND_URL}/api/canned-responses/${editingResponse.response_id}`
        : `${BACKEND_URL}/api/canned-responses`;
      
      const response = await fetch(url, {
        method: editingResponse ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        toast.success(editingResponse ? 'Response updated' : 'Response created');
        handleCloseModal();
        fetchResponses();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to save response');
      }
    } catch (error) {
      console.error('Failed to save response:', error);
      toast.error('Failed to save response');
    }
  };

  const handleDelete = async (responseId) => {
    if (!window.confirm('Are you sure you want to delete this canned response?')) return;

    try {
      const response = await fetch(`${BACKEND_URL}/api/canned-responses/${responseId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.ok) {
        toast.success('Response deleted');
        fetchResponses();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to delete response');
      }
    } catch (error) {
      console.error('Failed to delete response:', error);
      toast.error('Failed to delete response');
    }
  };

  const handleCopyShortcode = (shortcode, id) => {
    navigator.clipboard.writeText(`/${shortcode}`);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const insertPlaceholder = (placeholder) => {
    setFormData(prev => ({
      ...prev,
      content: prev.content + placeholder
    }));
  };

  const getFilteredResponses = () => {
    let filtered = [];
    
    if (scopeFilter === 'all' || scopeFilter === 'global') {
      filtered = [...filtered, ...responses.global];
    }
    if (scopeFilter === 'all' || scopeFilter === 'personal') {
      filtered = [...filtered, ...responses.personal];
    }

    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(r => 
        r.title.toLowerCase().includes(searchLower) ||
        r.shortcode.toLowerCase().includes(searchLower) ||
        r.content.toLowerCase().includes(searchLower)
      );
    }

    return filtered;
  };

  const filteredResponses = getFilteredResponses();

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Loading canned responses...</div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-foreground flex items-center gap-2">
              <MessageSquare className="text-primary" size={24} />
              Canned Responses
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Pre-written message templates for quick replies. Type <code className="px-1.5 py-0.5 bg-secondary rounded text-xs">/shortcode</code> in any reply box.
            </p>
          </div>
          <button
            onClick={() => handleOpenModal()}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            data-testid="add-canned-response-btn"
          >
            <Plus size={18} />
            New Response
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 mb-4">
          <div className="relative flex-1 max-w-md">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search responses..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full h-10 pl-9 pr-4 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              data-testid="search-canned-responses"
            />
          </div>
          <div className="flex items-center bg-secondary/50 rounded-lg p-1">
            {['all', 'global', 'personal'].map((scope) => (
              <button
                key={scope}
                onClick={() => setScopeFilter(scope)}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  scopeFilter === scope 
                    ? 'bg-background text-foreground shadow-sm' 
                    : 'text-muted-foreground hover:text-foreground'
                }`}
                data-testid={`filter-${scope}`}
              >
                {scope === 'global' && <Globe size={14} />}
                {scope === 'personal' && <User size={14} />}
                <span className="capitalize">{scope}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Responses List */}
        <div className="space-y-3">
          {filteredResponses.length === 0 ? (
            <div className="text-center py-12 glass rounded-xl border border-border/60">
              <MessageSquare size={40} className="mx-auto text-muted-foreground/40 mb-3" />
              <p className="text-muted-foreground">No canned responses found</p>
              <button
                onClick={() => handleOpenModal()}
                className="mt-3 text-primary text-sm hover:underline"
              >
                Create your first response
              </button>
            </div>
          ) : (
            filteredResponses.map((response) => (
              <div
                key={response.response_id}
                className="glass rounded-lg border border-border/60 p-4 hover:border-border transition-colors"
                data-testid={`canned-response-${response.response_id}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {response.scope === 'global' ? (
                        <Globe size={14} className="text-primary shrink-0" />
                      ) : (
                        <User size={14} className="text-amber-500 shrink-0" />
                      )}
                      <h3 className="font-medium text-foreground truncate">{response.title}</h3>
                      <button
                        onClick={() => handleCopyShortcode(response.shortcode, response.response_id)}
                        className="flex items-center gap-1 px-2 py-0.5 text-xs font-mono bg-secondary rounded hover:bg-secondary/80 transition-colors"
                        title="Click to copy"
                      >
                        /{response.shortcode}
                        {copiedId === response.response_id ? (
                          <Check size={12} className="text-emerald-500" />
                        ) : (
                          <Copy size={12} className="text-muted-foreground" />
                        )}
                      </button>
                    </div>
                    <p className="text-sm text-muted-foreground line-clamp-2 whitespace-pre-wrap">
                      {response.content}
                    </p>
                    <p className="text-xs text-muted-foreground/60 mt-2">
                      Created by {response.created_by_name || 'Unknown'}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => handleOpenModal(response)}
                      className="p-2 rounded-lg hover:bg-secondary transition-colors"
                      title="Edit"
                      data-testid={`edit-${response.response_id}`}
                    >
                      <Edit2 size={16} className="text-muted-foreground" />
                    </button>
                    <button
                      onClick={() => handleDelete(response.response_id)}
                      className="p-2 rounded-lg hover:bg-red-500/10 transition-colors"
                      title="Delete"
                      data-testid={`delete-${response.response_id}`}
                    >
                      <Trash2 size={16} className="text-red-400" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Stats */}
        <div className="mt-6 flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Globe size={14} />
            {responses.global.length} global
          </span>
          <span className="flex items-center gap-1">
            <User size={14} />
            {responses.personal.length} personal
          </span>
        </div>
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div 
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={handleCloseModal}
          />
          <div className="relative w-full max-w-2xl mx-4 glass rounded-xl border border-border/60 shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-border/60">
              <h2 className="text-lg font-semibold">
                {editingResponse ? 'Edit Canned Response' : 'New Canned Response'}
              </h2>
              <button
                onClick={handleCloseModal}
                className="p-2 rounded-lg hover:bg-secondary transition-colors"
              >
                <X size={18} />
              </button>
            </div>
            
            <div className="p-4 space-y-4 max-h-[70vh] overflow-y-auto">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium mb-1">Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="e.g., Refund Confirmation"
                  className={`w-full h-10 px-3 rounded-lg bg-secondary/50 border text-sm focus:outline-none focus:ring-1 focus:ring-primary ${
                    errors.title ? 'border-red-500' : 'border-border'
                  }`}
                  data-testid="canned-response-title"
                />
                {errors.title && (
                  <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                    <AlertCircle size={12} />
                    {errors.title}
                  </p>
                )}
              </div>

              {/* Shortcode */}
              <div>
                <label className="block text-sm font-medium mb-1">Shortcode</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">/</span>
                  <input
                    type="text"
                    value={formData.shortcode}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      shortcode: e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, '')
                    }))}
                    placeholder="refund"
                    className={`w-full h-10 pl-7 pr-3 rounded-lg bg-secondary/50 border text-sm font-mono focus:outline-none focus:ring-1 focus:ring-primary ${
                      errors.shortcode ? 'border-red-500' : 'border-border'
                    }`}
                    data-testid="canned-response-shortcode"
                  />
                </div>
                {errors.shortcode ? (
                  <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                    <AlertCircle size={12} />
                    {errors.shortcode}
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground mt-1">
                    Type <code className="px-1 bg-secondary rounded">/{formData.shortcode || 'shortcode'}</code> to insert this response
                  </p>
                )}
              </div>

              {/* Scope */}
              <div>
                <label className="block text-sm font-medium mb-1">Scope</label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, scope: 'global' }))}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                      formData.scope === 'global'
                        ? 'bg-primary/20 border-primary text-primary'
                        : 'bg-secondary/50 border-border text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    <Globe size={16} />
                    Global
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, scope: 'personal' }))}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                      formData.scope === 'personal'
                        ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                        : 'bg-secondary/50 border-border text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    <User size={16} />
                    Personal
                  </button>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {formData.scope === 'global' 
                    ? 'Everyone can see and use this response' 
                    : 'Only you can see and use this response'}
                </p>
              </div>

              {/* Placeholders */}
              <div>
                <label className="block text-sm font-medium mb-1">Insert Placeholder</label>
                <div className="flex flex-wrap gap-2">
                  {PLACEHOLDERS.map((p) => (
                    <button
                      key={p.key}
                      type="button"
                      onClick={() => insertPlaceholder(p.key)}
                      className="px-2 py-1 text-xs font-mono bg-secondary rounded hover:bg-secondary/80 transition-colors"
                    >
                      {p.key}
                    </button>
                  ))}
                </div>
              </div>

              {/* Content */}
              <div>
                <label className="block text-sm font-medium mb-1">Content</label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
                  placeholder="Hi {{customer_name}},&#10;&#10;Thank you for reaching out..."
                  rows={8}
                  className={`w-full px-3 py-2 rounded-lg bg-secondary/50 border text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary ${
                    errors.content ? 'border-red-500' : 'border-border'
                  }`}
                  data-testid="canned-response-content"
                />
                {errors.content && (
                  <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                    <AlertCircle size={12} />
                    {errors.content}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 p-4 border-t border-border/60">
              <button
                onClick={handleCloseModal}
                className="px-4 py-2 text-sm rounded-lg hover:bg-secondary transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                data-testid="save-canned-response-btn"
              >
                {editingResponse ? 'Update' : 'Create'} Response
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CannedResponsesPage;
