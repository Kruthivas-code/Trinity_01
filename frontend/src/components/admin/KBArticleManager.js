import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Pencil, Trash2, Loader2, X, Save, Eye, EyeOff, ChevronDown, ChevronRight, FileText, ExternalLink, ArrowLeft } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const slugify = (t) => t.toLowerCase().trim().replace(/[^\w\s-]/g, '').replace(/[\s_]+/g, '-').replace(/-+/g, '-');

const KBArticleManager = () => {
  const [articles, setArticles] = useState([]);
  const [navGroups, setNavGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // slug of article being edited
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const [expandedGroups, setExpandedGroups] = useState({});
  const [creating, setCreating] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/kb/admin/articles`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setArticles(data.articles || []);
        setNavGroups(data.nav_groups || []);
        // Auto-expand all groups
        const expanded = {};
        (data.nav_groups || []).forEach(g => { expanded[g.key] = true; });
        setExpandedGroups(expanded);
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const openEdit = (art) => {
    setCreating(false);
    setEditing(art.slug);
    setForm({ ...art });
  };

  const openCreate = (sectionKey, sectionLabel, navGroupKey, navGroupLabel) => {
    setEditing(null);
    setCreating(true);
    setForm({
      title: '',
      slug: '',
      section_key: sectionKey,
      section_label: sectionLabel,
      nav_group_key: navGroupKey,
      nav_group_label: navGroupLabel,
      content_markdown: '',
      published: true,
      order: articles.length,
    });
  };

  const handleSave = async () => {
    if (!form || !form.title.trim()) return;
    setSaving(true);
    try {
      const slug = form.slug.trim() || slugify(form.title);
      const payload = { ...form, slug };
      delete payload.created_at;
      delete payload.updated_at;
      delete payload.source_url;

      const url = creating
        ? `${BACKEND_URL}/api/kb/admin/articles`
        : `${BACKEND_URL}/api/kb/admin/articles/${editing}`;
      const method = creating ? 'POST' : 'PUT';

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Save failed');
      }
      setEditing(null);
      setCreating(false);
      setForm(null);
      await fetchAll();
    } catch (e) { console.error(e); }
    finally { setSaving(false); }
  };

  const handleDelete = async (slug) => {
    setDeleting(slug);
    try {
      await fetch(`${BACKEND_URL}/api/kb/admin/articles/${slug}`, { method: 'DELETE', credentials: 'include' });
      if (editing === slug) { setEditing(null); setForm(null); }
      await fetchAll();
    } catch (e) { console.error(e); }
    finally { setDeleting(null); }
  };

  const togglePublished = async (art) => {
    try {
      await fetch(`${BACKEND_URL}/api/kb/admin/articles/${art.slug}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ published: !art.published }),
      });
      await fetchAll();
    } catch (e) { console.error(e); }
  };

  // Build tree
  const tree = navGroups.map(group => ({
    ...group,
    sections: group.sections.map(sec => ({
      ...sec,
      articles: articles.filter(a => a.section_key === sec.key && a.nav_group_key === group.key),
    })),
  }));

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground py-8">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-sm">Loading articles...</span>
      </div>
    );
  }

  // Editor view
  if (form) {
    return (
      <div data-testid="kb-article-editor">
        <button
          onClick={() => { setForm(null); setEditing(null); setCreating(false); }}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-4 transition-colors"
          data-testid="back-to-list"
        >
          <ArrowLeft size={13} />
          Back to articles
        </button>

        <div className="space-y-4">
          {/* Title & Slug */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Title</label>
              <input
                value={form.title}
                onChange={e => {
                  const title = e.target.value;
                  setForm(f => ({
                    ...f,
                    title,
                    slug: creating || f.slug === slugify(f.title || '') ? slugify(title) : f.slug,
                  }));
                }}
                placeholder="Article title"
                className="w-full h-9 px-3 rounded-md border border-border bg-secondary/20 text-sm focus:outline-none focus:ring-1 focus:ring-foreground/20"
                data-testid="article-title-input"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Slug</label>
              <input
                value={form.slug}
                onChange={e => setForm(f => ({ ...f, slug: e.target.value }))}
                placeholder="article-slug"
                className="w-full h-9 px-3 rounded-md border border-border bg-secondary/20 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-foreground/20"
                data-testid="article-slug-input"
              />
            </div>
          </div>

          {/* Nav Group & Section */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Nav Group</label>
              <select
                value={form.nav_group_key}
                onChange={e => {
                  const group = navGroups.find(g => g.key === e.target.value);
                  setForm(f => ({
                    ...f,
                    nav_group_key: e.target.value,
                    nav_group_label: group?.label || e.target.value,
                    section_key: group?.sections?.[0]?.key || '',
                    section_label: group?.sections?.[0]?.label || '',
                  }));
                }}
                className="w-full h-9 px-3 rounded-md border border-border bg-secondary/20 text-sm focus:outline-none focus:ring-1 focus:ring-foreground/20"
                data-testid="article-nav-group"
              >
                {navGroups.map(g => (
                  <option key={g.key} value={g.key}>{g.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Section</label>
              <select
                value={form.section_key}
                onChange={e => {
                  const group = navGroups.find(g => g.key === form.nav_group_key);
                  const sec = group?.sections?.find(s => s.key === e.target.value);
                  setForm(f => ({ ...f, section_key: e.target.value, section_label: sec?.label || e.target.value }));
                }}
                className="w-full h-9 px-3 rounded-md border border-border bg-secondary/20 text-sm focus:outline-none focus:ring-1 focus:ring-foreground/20"
                data-testid="article-section"
              >
                {(navGroups.find(g => g.key === form.nav_group_key)?.sections || []).map(s => (
                  <option key={s.key} value={s.key}>{s.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Published & Order */}
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={form.published}
                onChange={e => setForm(f => ({ ...f, published: e.target.checked }))}
                className="rounded border-border"
                data-testid="article-published-check"
              />
              <span className="text-muted-foreground">Published</span>
            </label>
            <div className="flex items-center gap-2">
              <label className="text-xs text-muted-foreground">Order:</label>
              <input
                type="number"
                value={form.order}
                onChange={e => setForm(f => ({ ...f, order: parseInt(e.target.value) || 0 }))}
                className="w-16 h-7 px-2 rounded border border-border bg-secondary/20 text-xs text-center focus:outline-none"
                data-testid="article-order-input"
              />
            </div>
          </div>

          {/* Markdown Editor */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-muted-foreground">Content (Markdown)</label>
              <span className="text-[10px] text-muted-foreground/50">
                {form.content_markdown?.length || 0} chars
              </span>
            </div>
            <textarea
              value={form.content_markdown}
              onChange={e => setForm(f => ({ ...f, content_markdown: e.target.value }))}
              placeholder="# Heading&#10;&#10;Your article content in markdown..."
              rows={20}
              className="w-full px-4 py-3 rounded-lg border border-border bg-secondary/20 text-sm font-mono leading-relaxed resize-y focus:outline-none focus:ring-1 focus:ring-foreground/20"
              style={{ minHeight: '300px', tabSize: 2 }}
              data-testid="article-content-editor"
            />
          </div>

          {/* Save/Cancel */}
          <div className="flex items-center justify-between pt-2">
            <a
              href={`/docs/${form.slug}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              data-testid="preview-article-link"
            >
              <ExternalLink size={12} />
              Preview
            </a>
            <div className="flex items-center gap-2">
              <button
                onClick={() => { setForm(null); setEditing(null); setCreating(false); }}
                className="px-3 py-1.5 rounded-md text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                data-testid="cancel-article-edit"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !form.title.trim()}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-foreground text-background text-xs font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                data-testid="save-article-btn"
              >
                {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
                {creating ? 'Create' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // List view - tree structure
  return (
    <div data-testid="kb-article-manager">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-muted-foreground">{articles.length} articles</p>
        <a href="/dashboard/kb-editor" className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-foreground text-background text-xs font-medium hover:opacity-90 transition-opacity" data-testid="open-full-editor">
          <Pencil size={12} />
          Open Full Editor
        </a>
      </div>

      <div className="space-y-1">
        {tree.map(group => (
          <div key={group.key} className="mb-2" data-testid={`kb-group-${group.key}`}>
            {/* Group header */}
            <button
              onClick={() => setExpandedGroups(g => ({ ...g, [group.key]: !g[group.key] }))}
              className="flex items-center gap-2 w-full px-3 py-2 rounded-lg hover:bg-muted/50 transition-colors text-left"
              data-testid={`kb-group-toggle-${group.key}`}
            >
              {expandedGroups[group.key] ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
              <span className="text-sm font-semibold">{group.label}</span>
              <span className="text-[10px] text-muted-foreground/50 ml-auto">
                {group.sections.reduce((sum, s) => sum + s.articles.length, 0)}
              </span>
            </button>

            {expandedGroups[group.key] && (
              <div className="ml-3 border-l border-border/30 pl-2">
                {group.sections.map(sec => (
                  <div key={sec.key} className="mb-2" data-testid={`kb-section-${sec.key}`}>
                    {/* Section label */}
                    <div className="flex items-center justify-between px-3 py-1.5">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/50">
                        {sec.label}
                      </span>
                      <button
                        onClick={() => openCreate(sec.key, sec.label, group.key, group.label)}
                        className="p-1 rounded text-muted-foreground/30 hover:text-foreground hover:bg-muted/50 transition-colors"
                        title={`Add article to ${sec.label}`}
                        data-testid={`add-article-${sec.key}`}
                      >
                        <Plus size={12} />
                      </button>
                    </div>

                    {/* Articles in section */}
                    {sec.articles.map(art => (
                      <div
                        key={art.slug}
                        className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-muted/30 group transition-colors"
                        data-testid={`kb-article-row-${art.slug}`}
                      >
                        <FileText size={13} className={art.published ? 'text-muted-foreground/40' : 'text-muted-foreground/20'} />
                        <button
                          onClick={() => openEdit(art)}
                          className="flex-1 text-left text-sm truncate text-foreground/80 hover:text-foreground transition-colors"
                          data-testid={`edit-article-${art.slug}`}
                        >
                          {art.title}
                        </button>
                        {!art.published && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">draft</span>
                        )}
                        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                          <button
                            onClick={() => togglePublished(art)}
                            className="p-1 rounded text-muted-foreground hover:text-foreground"
                            title={art.published ? 'Unpublish' : 'Publish'}
                            data-testid={`toggle-pub-${art.slug}`}
                          >
                            {art.published ? <Eye size={12} /> : <EyeOff size={12} />}
                          </button>
                          <button
                            onClick={() => handleDelete(art.slug)}
                            disabled={deleting === art.slug}
                            className="p-1 rounded text-muted-foreground hover:text-destructive"
                            title="Delete"
                            data-testid={`delete-article-${art.slug}`}
                          >
                            {deleting === art.slug ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                          </button>
                        </div>
                      </div>
                    ))}

                    {sec.articles.length === 0 && (
                      <div className="px-3 py-2 text-[11px] text-muted-foreground/30 italic">No articles</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default KBArticleManager;
