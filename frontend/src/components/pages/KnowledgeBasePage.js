import React, { useState, useEffect, useCallback } from 'react';
import {
  BookOpen, Search, Plus, Trash2, Pencil, Sparkles, Download,
  ExternalLink, Tag, Filter, X, FileText, Check, Loader2,
  Copy, Link2, ChevronDown
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const STATUS_CONFIG = {
  draft: { label: 'Draft', bg: 'bg-slate-100 dark:bg-slate-800', text: 'text-slate-700 dark:text-slate-300', border: 'border-slate-200 dark:border-slate-700' },
  refined: { label: 'Refined', bg: 'bg-blue-50 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-300', border: 'border-blue-200 dark:border-blue-800' },
  published: { label: 'Published', bg: 'bg-emerald-50 dark:bg-emerald-900/30', text: 'text-emerald-700 dark:text-emerald-300', border: 'border-emerald-200 dark:border-emerald-800' },
};

const StatusBadge = ({ status }) => {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${config.bg} ${config.text} ${config.border}`} data-testid={`snippet-status-${status}`}>
      {config.label}
    </span>
  );
};

export default function KnowledgeBasePage({ user }) {
  const [snippets, setSnippets] = useState([]);
  const [allTags, setAllTags] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterTag, setFilterTag] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [editingSnippet, setEditingSnippet] = useState(null);
  const [refiningId, setRefiningId] = useState(null);
  const [formData, setFormData] = useState({ title: '', content: '', tags: '', status: 'draft', external_url: '', snippet_type: 'internal' });

  const fetchSnippets = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (filterTag) params.append('tag', filterTag);
      if (filterStatus) params.append('status', filterStatus);
      const res = await fetch(`${BACKEND_URL}/api/knowledge-base?${params}`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setSnippets(data.items || []);
        setTotal(data.total || 0);
        setAllTags(data.tags || []);
      }
    } catch (err) {
      console.error('Failed to fetch KB snippets:', err);
    } finally {
      setLoading(false);
    }
  }, [search, filterTag, filterStatus]);

  useEffect(() => { fetchSnippets(); }, [fetchSnippets]);

  const handleSave = async () => {
    const tags = formData.tags ? formData.tags.split(',').map(t => t.trim()).filter(Boolean) : [];
    const body = { ...formData, tags };
    const isEdit = !!editingSnippet;
    const url = isEdit ? `${BACKEND_URL}/api/knowledge-base/${editingSnippet.snippet_id}` : `${BACKEND_URL}/api/knowledge-base`;
    const method = isEdit ? 'PUT' : 'POST';

    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });
      if (res.ok) {
        resetForm();
        fetchSnippets();
      }
    } catch (err) {
      console.error('Failed to save snippet:', err);
    }
  };

  const handleDelete = async (snippetId) => {
    if (!window.confirm('Delete this snippet?')) return;
    try {
      await fetch(`${BACKEND_URL}/api/knowledge-base/${snippetId}`, { method: 'DELETE', credentials: 'include' });
      fetchSnippets();
    } catch (err) {
      console.error('Failed to delete snippet:', err);
    }
  };

  const handleRefine = async (snippetId) => {
    setRefiningId(snippetId);
    try {
      const res = await fetch(`${BACKEND_URL}/api/knowledge-base/${snippetId}/refine`, {
        method: 'POST',
        credentials: 'include',
      });
      if (res.ok) {
        fetchSnippets();
      }
    } catch (err) {
      console.error('AI refine failed:', err);
    } finally {
      setRefiningId(null);
    }
  };

  const handlePublish = async (snippet) => {
    const newStatus = snippet.status === 'published' ? 'draft' : 'published';
    try {
      await fetch(`${BACKEND_URL}/api/knowledge-base/${snippet.snippet_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ status: newStatus }),
      });
      fetchSnippets();
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleExport = async (format) => {
    window.open(`${BACKEND_URL}/api/knowledge-base-export?format=${format}`, '_blank');
  };

  const startEdit = (snippet) => {
    setEditingSnippet(snippet);
    setFormData({
      title: snippet.title,
      content: snippet.content,
      tags: (snippet.tags || []).join(', '),
      status: snippet.status,
      external_url: snippet.external_url || '',
      snippet_type: snippet.snippet_type || 'internal',
    });
    setShowCreate(true);
  };

  const resetForm = () => {
    setShowCreate(false);
    setEditingSnippet(null);
    setFormData({ title: '', content: '', tags: '', status: 'draft', external_url: '', snippet_type: 'internal' });
  };

  const copyContent = (content) => {
    navigator.clipboard.writeText(content);
  };

  return (
    <div className="max-w-6xl mx-auto" data-testid="knowledge-base-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2">
            <BookOpen size={22} className="text-primary" />
            Knowledge Base
          </h1>
          <p className="text-sm text-muted-foreground mt-1">{total} snippet{total !== 1 ? 's' : ''}</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative group">
            <button
              onClick={() => handleExport('json')}
              className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-border hover:bg-secondary transition-colors"
              data-testid="kb-export-btn"
            >
              <Download size={14} />
              Export
              <ChevronDown size={12} />
            </button>
            <div className="absolute right-0 mt-1 w-36 bg-card border border-border rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-20">
              <button onClick={() => handleExport('json')} className="w-full text-left px-3 py-2 text-sm hover:bg-secondary rounded-t-lg" data-testid="kb-export-json">JSON</button>
              <button onClick={() => handleExport('csv')} className="w-full text-left px-3 py-2 text-sm hover:bg-secondary rounded-b-lg" data-testid="kb-export-csv">CSV</button>
            </div>
          </div>
          <button
            onClick={() => { resetForm(); setShowCreate(true); }}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
            data-testid="kb-create-btn"
          >
            <Plus size={14} />
            New Snippet
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search snippets..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-9 pl-9 pr-3 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            data-testid="kb-search-input"
          />
        </div>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="h-9 px-3 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          data-testid="kb-filter-status"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="refined">Refined</option>
          <option value="published">Published</option>
        </select>
        {allTags.length > 0 && (
          <select
            value={filterTag}
            onChange={(e) => setFilterTag(e.target.value)}
            className="h-9 px-3 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            data-testid="kb-filter-tag"
          >
            <option value="">All Tags</option>
            {allTags.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        )}
        {(filterTag || filterStatus) && (
          <button onClick={() => { setFilterTag(''); setFilterStatus(''); }} className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1">
            <X size={12} /> Clear
          </button>
        )}
      </div>

      {/* Create/Edit Form */}
      {showCreate && (
        <div className="mb-6 p-4 rounded-xl border border-border bg-card" data-testid="kb-form">
          <h2 className="text-sm font-semibold mb-3">{editingSnippet ? 'Edit Snippet' : 'New Snippet'}</h2>
          <div className="space-y-3">
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-xs font-medium text-muted-foreground mb-1">Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData(p => ({ ...p, title: e.target.value }))}
                  placeholder="Article title..."
                  className="w-full h-9 px-3 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  data-testid="kb-form-title"
                />
              </div>
              <div className="w-48">
                <label className="block text-xs font-medium text-muted-foreground mb-1">Type</label>
                <select
                  value={formData.snippet_type}
                  onChange={(e) => setFormData(p => ({ ...p, snippet_type: e.target.value }))}
                  className="w-full h-9 px-3 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  data-testid="kb-form-type"
                >
                  <option value="internal">Internal Snippet</option>
                  <option value="external">External Link</option>
                </select>
              </div>
            </div>
            {formData.snippet_type === 'external' && (
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">External URL</label>
                <input
                  type="url"
                  value={formData.external_url}
                  onChange={(e) => setFormData(p => ({ ...p, external_url: e.target.value }))}
                  placeholder="https://help.example.com/article/..."
                  className="w-full h-9 px-3 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  data-testid="kb-form-url"
                />
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Content</label>
              <textarea
                value={formData.content}
                onChange={(e) => setFormData(p => ({ ...p, content: e.target.value }))}
                placeholder="Knowledge base article content..."
                rows={6}
                className="w-full px-3 py-2 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                data-testid="kb-form-content"
              />
            </div>
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-xs font-medium text-muted-foreground mb-1">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={formData.tags}
                  onChange={(e) => setFormData(p => ({ ...p, tags: e.target.value }))}
                  placeholder="billing, password, login..."
                  className="w-full h-9 px-3 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  data-testid="kb-form-tags"
                />
              </div>
              <div className="w-36">
                <label className="block text-xs font-medium text-muted-foreground mb-1">Status</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData(p => ({ ...p, status: e.target.value }))}
                  className="w-full h-9 px-3 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  data-testid="kb-form-status"
                >
                  <option value="draft">Draft</option>
                  <option value="published">Published</option>
                </select>
              </div>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={handleSave}
                disabled={!formData.title.trim()}
                className="flex items-center gap-1.5 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium disabled:opacity-50"
                data-testid="kb-form-save"
              >
                <Check size={14} />
                {editingSnippet ? 'Update' : 'Create'}
              </button>
              <button onClick={resetForm} className="px-3 py-2 text-sm rounded-lg hover:bg-secondary transition-colors" data-testid="kb-form-cancel">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Snippets List */}
      {loading ? (
        <div className="py-12 text-center text-sm text-muted-foreground">
          <Loader2 size={20} className="mx-auto animate-spin mb-2" />
          Loading snippets...
        </div>
      ) : snippets.length === 0 ? (
        <div className="py-16 text-center" data-testid="kb-empty-state">
          <BookOpen size={40} className="mx-auto text-muted-foreground/30 mb-3" />
          <p className="text-sm text-muted-foreground mb-1">No knowledge base snippets yet</p>
          <p className="text-xs text-muted-foreground/70 mb-4">Create snippets from agent replies or add external help article links</p>
          <button
            onClick={() => { resetForm(); setShowCreate(true); }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            <Plus size={14} /> Create First Snippet
          </button>
        </div>
      ) : (
        <div className="space-y-2" data-testid="kb-snippets-list">
          {snippets.map((snippet) => (
            <div
              key={snippet.snippet_id}
              className="group p-4 rounded-xl border border-border bg-card hover:border-primary/20 transition-colors"
              data-testid={`kb-snippet-${snippet.snippet_id}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {snippet.snippet_type === 'external' ? (
                      <ExternalLink size={14} className="text-blue-500 shrink-0" />
                    ) : (
                      <FileText size={14} className="text-muted-foreground shrink-0" />
                    )}
                    <h3 className="text-sm font-medium truncate">{snippet.title}</h3>
                    <StatusBadge status={snippet.status} />
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                    {snippet.content?.substring(0, 200)}{snippet.content?.length > 200 ? '...' : ''}
                  </p>
                  <div className="flex items-center gap-2 flex-wrap">
                    {(snippet.tags || []).map(tag => (
                      <span key={tag} className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-secondary text-muted-foreground">
                        <Tag size={9} />{tag}
                      </span>
                    ))}
                    {snippet.source_ticket_id && (
                      <span className="text-[10px] text-muted-foreground">from {snippet.source_ticket_id}</span>
                    )}
                    {snippet.external_url && (
                      <a href={snippet.external_url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-blue-500 hover:underline flex items-center gap-0.5">
                        <Link2 size={9} />{snippet.external_url.substring(0, 40)}...
                      </a>
                    )}
                    <span className="text-[10px] text-muted-foreground/60">
                      by {snippet.created_by_name} · {new Date(snippet.created_at?.endsWith?.('Z') ? snippet.created_at : snippet.created_at + 'Z').toLocaleDateString('en-US', { timeZone: 'Asia/Kolkata' })}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  <button
                    onClick={() => copyContent(snippet.content)}
                    className="p-1.5 rounded-lg hover:bg-secondary transition-colors"
                    title="Copy content"
                    data-testid={`kb-copy-${snippet.snippet_id}`}
                  >
                    <Copy size={13} className="text-muted-foreground" />
                  </button>
                  <button
                    onClick={() => handleRefine(snippet.snippet_id)}
                    disabled={refiningId === snippet.snippet_id}
                    className="p-1.5 rounded-lg hover:bg-secondary transition-colors disabled:opacity-50"
                    title="AI Refine"
                    data-testid={`kb-refine-${snippet.snippet_id}`}
                  >
                    {refiningId === snippet.snippet_id ? (
                      <Loader2 size={13} className="animate-spin text-primary" />
                    ) : (
                      <Sparkles size={13} className="text-primary" />
                    )}
                  </button>
                  <button
                    onClick={() => handlePublish(snippet)}
                    className="p-1.5 rounded-lg hover:bg-secondary transition-colors"
                    title={snippet.status === 'published' ? 'Unpublish' : 'Publish'}
                    data-testid={`kb-publish-${snippet.snippet_id}`}
                  >
                    <Check size={13} className={snippet.status === 'published' ? 'text-emerald-500' : 'text-muted-foreground'} />
                  </button>
                  <button
                    onClick={() => startEdit(snippet)}
                    className="p-1.5 rounded-lg hover:bg-secondary transition-colors"
                    title="Edit"
                    data-testid={`kb-edit-${snippet.snippet_id}`}
                  >
                    <Pencil size={13} className="text-muted-foreground" />
                  </button>
                  <button
                    onClick={() => handleDelete(snippet.snippet_id)}
                    className="p-1.5 rounded-lg hover:bg-secondary transition-colors"
                    title="Delete"
                    data-testid={`kb-delete-${snippet.snippet_id}`}
                  >
                    <Trash2 size={13} className="text-red-400" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
