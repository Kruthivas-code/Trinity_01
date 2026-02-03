import React, { useState, useEffect, useRef } from 'react';
import { 
  Plus, Search, Edit2, Trash2, Globe, User, 
  MessageSquare, Copy, Check, X, AlertCircle,
  Loader2, ChevronRight, Info, Keyboard, Slash
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

const PLACEHOLDERS = [
  { key: '{{customer_name}}', label: 'Customer Name', desc: 'Name of the customer' },
  { key: '{{customer_email}}', label: 'Customer Email', desc: 'Email address of customer' },
  { key: '{{ticket_id}}', label: 'Ticket ID', desc: 'Unique ticket identifier' },
  { key: '{{ticket_title}}', label: 'Ticket Title', desc: 'Subject of the ticket' },
  { key: '{{agent_name}}', label: 'Your Name', desc: 'Your display name' },
  { key: '{{agent_email}}', label: 'Your Email', desc: 'Your email address' },
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
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const contentRef = useRef(null);

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
    } else if (formData.shortcode.length < 2) {
      newErrors.shortcode = 'Shortcode must be at least 2 characters';
    } else if (formData.shortcode.length > 30) {
      newErrors.shortcode = 'Shortcode must be 30 characters or less';
    }
    if (!formData.content.trim()) newErrors.content = 'Content is required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    setSaving(true);
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
        toast.success(editingResponse ? 'Response updated successfully' : 'Response created successfully');
        handleCloseModal();
        fetchResponses();
      } else {
        const error = await response.json();
        if (error.detail?.includes('shortcode')) {
          setErrors({ shortcode: 'This shortcode is already in use' });
        } else {
          toast.error(error.detail || 'Failed to save response');
        }
      }
    } catch (error) {
      console.error('Failed to save response:', error);
      toast.error('Failed to save response');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (responseId) => {
    if (!window.confirm('Are you sure you want to delete this canned response? This action cannot be undone.')) return;

    setDeleting(responseId);
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
    } finally {
      setDeleting(null);
    }
  };

  const handleCopyShortcode = (shortcode, id) => {
    navigator.clipboard.writeText(`/${shortcode}`);
    setCopiedId(id);
    toast.success('Shortcode copied to clipboard');
    setTimeout(() => setCopiedId(null), 2000);
  };

  const insertPlaceholder = (placeholder) => {
    // Insert at cursor position in textarea
    if (contentRef.current) {
      const start = contentRef.current.selectionStart;
      const end = contentRef.current.selectionEnd;
      const newContent = 
        formData.content.substring(0, start) + 
        placeholder + 
        formData.content.substring(end);
      
      setFormData(prev => ({ ...prev, content: newContent }));
      
      // Restore focus and cursor position
      setTimeout(() => {
        contentRef.current.focus();
        contentRef.current.setSelectionRange(start + placeholder.length, start + placeholder.length);
      }, 0);
    } else {
      setFormData(prev => ({
        ...prev,
        content: prev.content + placeholder
      }));
    }
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
  const totalCount = responses.global.length + responses.personal.length;

  return (
    <div className="h-full overflow-auto p-6" data-testid="canned-responses-page">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-foreground flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-primary/15 flex items-center justify-center">
                <MessageSquare className="text-primary" size={20} />
              </div>
              Canned Responses
            </h1>
            <p className="text-sm text-muted-foreground mt-2 max-w-xl">
              Pre-written templates for quick replies. Use the picker in ticket drawer or type <code className="px-1.5 py-0.5 bg-secondary rounded text-xs font-mono">/shortcode</code> to insert.
            </p>
          </div>
          <button
            onClick={() => handleOpenModal()}
            className="flex items-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium text-sm shadow-lg shadow-primary/20"
            data-testid="add-canned-response-btn"
          >
            <Plus size={18} />
            New Response
          </button>
        </div>

        {/* Usage Tips Card */}
        <div className="mb-6 p-4 rounded-xl bg-secondary/30 border border-border/40">
          <h3 className="text-sm font-medium flex items-center gap-2 mb-3">
            <Keyboard size={14} className="text-primary" />
            Quick Access Methods
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-muted-foreground">
            <div className="flex items-start gap-2">
              <kbd className="px-1.5 py-0.5 bg-secondary rounded text-[10px] font-mono shrink-0">⌘/</kbd>
              <span>Open canned response picker in ticket drawer</span>
            </div>
            <div className="flex items-start gap-2">
              <div className="flex items-center gap-1 shrink-0">
                <Slash size={12} className="text-primary" />
                <span className="font-mono">shortcode</span>
              </div>
              <span>Type in reply box for autocomplete</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="px-1.5 py-0.5 bg-secondary rounded text-[10px] shrink-0">Canned ▼</span>
              <span>Click button in reply toolbar</span>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 mb-4">
          <div className="relative flex-1 max-w-md">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by title, shortcode, or content..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full h-10 pl-9 pr-4 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all placeholder:text-muted-foreground/60"
              data-testid="search-canned-responses"
            />
          </div>
          <div className="flex items-center bg-secondary/50 rounded-lg p-1 border border-border/40">
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
                {scope === 'all' && <span className="text-xs text-muted-foreground">({totalCount})</span>}
              </button>
            ))}
          </div>
        </div>

        {/* Responses List */}
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="flex items-center gap-3 text-muted-foreground">
              <Loader2 size={20} className="animate-spin" />
              <span>Loading canned responses...</span>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredResponses.length === 0 ? (
              <div className="text-center py-16 glass rounded-xl border border-border/60">
                <div className="w-16 h-16 rounded-2xl bg-secondary/50 flex items-center justify-center mx-auto mb-4">
                  <MessageSquare size={28} className="text-muted-foreground/40" />
                </div>
                <p className="text-muted-foreground font-medium">
                  {search ? 'No responses match your search' : 'No canned responses yet'}
                </p>
                <p className="text-sm text-muted-foreground/60 mt-1">
                  {search ? 'Try a different search term' : 'Create your first response to speed up your workflow'}
                </p>
                {!search && (
                  <button
                    onClick={() => handleOpenModal()}
                    className="mt-4 text-primary text-sm hover:underline font-medium"
                  >
                    Create your first response →
                  </button>
                )}
              </div>
            ) : (
              filteredResponses.map((response) => (
                <div
                  key={response.response_id}
                  className="glass rounded-xl border border-border/60 p-4 hover:border-primary/30 transition-all group"
                  data-testid={`canned-response-${response.response_id}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <div className={`w-6 h-6 rounded-md flex items-center justify-center ${
                          response.scope === 'global' 
                            ? 'bg-primary/15 text-primary' 
                            : 'bg-amber-500/15 text-amber-500'
                        }`}>
                          {response.scope === 'global' ? (
                            <Globe size={13} />
                          ) : (
                            <User size={13} />
                          )}
                        </div>
                        <h3 className="font-medium text-foreground truncate">{response.title}</h3>
                        <button
                          onClick={() => handleCopyShortcode(response.shortcode, response.response_id)}
                          className="flex items-center gap-1 px-2 py-1 text-xs font-mono bg-secondary/70 rounded-md hover:bg-secondary transition-colors group/copy"
                          title="Click to copy shortcode"
                          data-testid={`copy-shortcode-${response.response_id}`}
                        >
                          /{response.shortcode}
                          {copiedId === response.response_id ? (
                            <Check size={12} className="text-emerald-500" />
                          ) : (
                            <Copy size={12} className="text-muted-foreground opacity-0 group-hover/copy:opacity-100 transition-opacity" />
                          )}
                        </button>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-2 whitespace-pre-wrap leading-relaxed">
                        {response.content}
                      </p>
                      <p className="text-xs text-muted-foreground/60 mt-2 flex items-center gap-2">
                        <span>Created by {response.created_by_name || 'Unknown'}</span>
                        {response.updated_at && response.updated_at !== response.created_at && (
                          <span>• Edited</span>
                        )}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => handleOpenModal(response)}
                        className="p-2 rounded-lg hover:bg-secondary transition-colors"
                        title="Edit response"
                        data-testid={`edit-${response.response_id}`}
                      >
                        <Edit2 size={16} className="text-muted-foreground" />
                      </button>
                      <button
                        onClick={() => handleDelete(response.response_id)}
                        disabled={deleting === response.response_id}
                        className="p-2 rounded-lg hover:bg-red-500/10 transition-colors disabled:opacity-50"
                        title="Delete response"
                        data-testid={`delete-${response.response_id}`}
                      >
                        {deleting === response.response_id ? (
                          <Loader2 size={16} className="animate-spin text-red-400" />
                        ) : (
                          <Trash2 size={16} className="text-red-400" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Stats Footer */}
        {!loading && totalCount > 0 && (
          <div className="mt-6 flex items-center gap-6 text-sm text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Globe size={14} className="text-primary" />
              {responses.global.length} global
            </span>
            <span className="flex items-center gap-1.5">
              <User size={14} className="text-amber-500" />
              {responses.personal.length} personal
            </span>
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" data-testid="canned-response-modal">
          <div 
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={handleCloseModal}
          />
          <div className="relative w-full max-w-2xl mx-4 glass rounded-xl border border-border/60 shadow-2xl max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-border/60 shrink-0">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                {editingResponse ? (
                  <>
                    <Edit2 size={18} className="text-primary" />
                    Edit Response
                  </>
                ) : (
                  <>
                    <Plus size={18} className="text-primary" />
                    New Canned Response
                  </>
                )}
              </h2>
              <button
                onClick={handleCloseModal}
                className="p-2 rounded-lg hover:bg-secondary transition-colors"
                data-testid="modal-close-btn"
              >
                <X size={18} />
              </button>
            </div>
            
            {/* Modal Content */}
            <div className="p-4 space-y-4 overflow-y-auto flex-1">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium mb-1.5">Title <span className="text-red-400">*</span></label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="e.g., Refund Confirmation"
                  className={`w-full h-10 px-3 rounded-lg bg-secondary/50 border text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all ${
                    errors.title ? 'border-red-500 focus:ring-red-500/50' : 'border-border'
                  }`}
                  data-testid="canned-response-title"
                  autoFocus
                />
                {errors.title && (
                  <p className="text-xs text-red-400 mt-1.5 flex items-center gap-1">
                    <AlertCircle size={12} />
                    {errors.title}
                  </p>
                )}
              </div>

              {/* Shortcode */}
              <div>
                <label className="block text-sm font-medium mb-1.5">Shortcode <span className="text-red-400">*</span></label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground font-mono">/</span>
                  <input
                    type="text"
                    value={formData.shortcode}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      shortcode: e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, '')
                    }))}
                    placeholder="refund"
                    className={`w-full h-10 pl-7 pr-3 rounded-lg bg-secondary/50 border text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all ${
                      errors.shortcode ? 'border-red-500 focus:ring-red-500/50' : 'border-border'
                    }`}
                    data-testid="canned-response-shortcode"
                  />
                </div>
                {errors.shortcode ? (
                  <p className="text-xs text-red-400 mt-1.5 flex items-center gap-1">
                    <AlertCircle size={12} />
                    {errors.shortcode}
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground mt-1.5">
                    Type <code className="px-1 bg-secondary rounded font-mono">/{formData.shortcode || 'shortcode'}</code> in reply box to insert
                  </p>
                )}
              </div>

              {/* Scope */}
              <div>
                <label className="block text-sm font-medium mb-1.5">Visibility</label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, scope: 'global' }))}
                    className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border transition-all ${
                      formData.scope === 'global'
                        ? 'bg-primary/15 border-primary/50 text-primary ring-1 ring-primary/20'
                        : 'bg-secondary/50 border-border text-muted-foreground hover:text-foreground hover:border-border/80'
                    }`}
                    data-testid="scope-global"
                  >
                    <Globe size={16} />
                    <span className="font-medium">Global</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, scope: 'personal' }))}
                    className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border transition-all ${
                      formData.scope === 'personal'
                        ? 'bg-amber-500/15 border-amber-500/50 text-amber-400 ring-1 ring-amber-500/20'
                        : 'bg-secondary/50 border-border text-muted-foreground hover:text-foreground hover:border-border/80'
                    }`}
                    data-testid="scope-personal"
                  >
                    <User size={16} />
                    <span className="font-medium">Personal</span>
                  </button>
                </div>
                <p className="text-xs text-muted-foreground mt-1.5">
                  {formData.scope === 'global' 
                    ? 'Everyone on your team can see and use this response' 
                    : 'Only you can see and use this response'}
                </p>
              </div>

              {/* Placeholders */}
              <div>
                <label className="block text-sm font-medium mb-1.5">Dynamic Placeholders</label>
                <div className="flex flex-wrap gap-1.5">
                  {PLACEHOLDERS.map((p) => (
                    <button
                      key={p.key}
                      type="button"
                      onClick={() => insertPlaceholder(p.key)}
                      className="px-2 py-1 text-xs font-mono bg-secondary/70 border border-border/40 rounded-md hover:bg-primary/15 hover:text-primary hover:border-primary/30 transition-all"
                      title={p.desc}
                    >
                      {p.key}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-1.5 flex items-center gap-1">
                  <Info size={11} />
                  Click to insert. Placeholders are replaced with actual values when used.
                </p>
              </div>

              {/* Content */}
              <div>
                <label className="block text-sm font-medium mb-1.5">Content <span className="text-red-400">*</span></label>
                <textarea
                  ref={contentRef}
                  value={formData.content}
                  onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
                  placeholder="Hi {{customer_name}},

Thank you for reaching out. I'd be happy to help you with...

Best regards,
{{agent_name}}"
                  rows={10}
                  className={`w-full px-3 py-2.5 rounded-lg bg-secondary/50 border text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-mono leading-relaxed ${
                    errors.content ? 'border-red-500 focus:ring-red-500/50' : 'border-border'
                  }`}
                  data-testid="canned-response-content"
                />
                {errors.content && (
                  <p className="text-xs text-red-400 mt-1.5 flex items-center gap-1">
                    <AlertCircle size={12} />
                    {errors.content}
                  </p>
                )}
                <p className="text-xs text-muted-foreground mt-1.5 text-right">
                  {formData.content.length} characters
                </p>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-2 p-4 border-t border-border/60 shrink-0 bg-secondary/10">
              <button
                onClick={handleCloseModal}
                className="px-4 py-2 text-sm rounded-lg hover:bg-secondary transition-colors"
                disabled={saving}
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={saving}
                className="px-5 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium flex items-center gap-2 disabled:opacity-50"
                data-testid="save-canned-response-btn"
              >
                {saving ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>{editingResponse ? 'Update' : 'Create'} Response</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CannedResponsesPage;
