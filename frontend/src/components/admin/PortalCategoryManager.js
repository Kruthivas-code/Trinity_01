import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Pencil, Trash2, Loader2, GripVertical, ExternalLink, X, ChevronDown, ChevronUp, Link2, Save } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const ICON_OPTIONS = [
  'CreditCard', 'Receipt', 'Globe', 'Boxes', 'UserCog', 'ShieldCheck',
  'Rocket', 'Bot', 'Database', 'Smartphone', 'HelpCircle', 'Mail',
  'Settings', 'Search', 'Bell', 'Lock', 'Zap', 'Code',
];

const HELP_ARTICLES = [
  { title: 'Welcome To Emergent', url: 'https://help.emergent.sh/welcome' },
  { title: 'Your First App', url: 'https://help.emergent.sh/your-first-app' },
  { title: 'Plans and Credits', url: 'https://help.emergent.sh/plans-and-credits' },
  { title: 'FAQs', url: 'https://help.emergent.sh/faqs' },
  { title: 'Voice Mode', url: 'https://help.emergent.sh/voice-mode' },
  { title: 'GitHub Integration', url: 'https://help.emergent.sh/github-integration' },
  { title: 'Universal Key', url: 'https://help.emergent.sh/universal-key' },
  { title: 'Deployment on Emergent', url: 'https://help.emergent.sh/deployment-on-emergent' },
  { title: 'Context Limits', url: 'https://help.emergent.sh/context-limits' },
  { title: 'Mobile App Development', url: 'https://help.emergent.sh/mobile-app-development' },
  { title: 'Teams Plan & Collaboration', url: 'https://help.emergent.sh/teams-plan-collaboration' },
  { title: 'Deployment Types', url: 'https://help.emergent.sh/deployment-types' },
  { title: 'Rollback Feature', url: 'https://help.emergent.sh/rollback-feature' },
  { title: 'Forking In Emergent', url: 'https://help.emergent.sh/forking-in-emergent' },
  { title: 'MCP (Model Context Protocol)', url: 'https://help.emergent.sh/mcp' },
  { title: 'Prompting Basics', url: 'https://help.emergent.sh/prompting-basics' },
  { title: 'Pre-deployment Health Check', url: 'https://help.emergent.sh/pre-deployment-health-check' },
  { title: 'Fixing Design Inconsistencies', url: 'https://help.emergent.sh/fixing-design-inconsistencies' },
  { title: 'How Do Apps Work?', url: 'https://help.emergent.sh/how-do-apps-work' },
];

const slugify = (text) =>
  text.toLowerCase().trim().replace(/[^\w\s-]/g, '').replace(/[\s_]+/g, '-').replace(/-+/g, '-');

const PortalCategoryManager = () => {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingCat, setEditingCat] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  const emptyForm = { title: '', slug: '', description: '', icon: 'HelpCircle', subtopics: [], help_articles: [], order: 0 };
  const [form, setForm] = useState(emptyForm);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/portal/categories`);
      if (res.ok) {
        const data = await res.json();
        setCategories(data.categories || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCategories(); }, [fetchCategories]);

  const openCreate = () => {
    setEditingCat(null);
    setForm(emptyForm);
    setShowForm(true);
  };

  const openEdit = (cat) => {
    setEditingCat(cat);
    setForm({
      title: cat.title || '',
      slug: cat.slug || '',
      description: cat.description || '',
      icon: cat.icon || 'HelpCircle',
      subtopics: cat.subtopics || [],
      help_articles: cat.help_articles || [],
      order: cat.order || 0,
    });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      const slug = form.slug.trim() || slugify(form.title);
      const payload = { ...form, slug };

      if (editingCat) {
        const res = await fetch(`${BACKEND_URL}/api/portal/admin/categories/${editingCat.slug}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || 'Update failed');
        }
      } else {
        const res = await fetch(`${BACKEND_URL}/api/portal/admin/categories`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || 'Create failed');
        }
      }
      setShowForm(false);
      setEditingCat(null);
      await fetchCategories();
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (slug) => {
    setDeleting(slug);
    try {
      const res = await fetch(`${BACKEND_URL}/api/portal/admin/categories/${slug}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (res.ok) await fetchCategories();
    } catch (e) {
      console.error(e);
    } finally {
      setDeleting(null);
    }
  };

  const addSubtopic = () => {
    setForm(f => ({ ...f, subtopics: [...f.subtopics, { name: '', items: [] }] }));
  };

  const updateSubtopic = (idx, key, val) => {
    setForm(f => {
      const subs = [...f.subtopics];
      subs[idx] = { ...subs[idx], [key]: val };
      return { ...f, subtopics: subs };
    });
  };

  const removeSubtopic = (idx) => {
    setForm(f => ({ ...f, subtopics: f.subtopics.filter((_, i) => i !== idx) }));
  };

  const toggleHelpArticle = (article) => {
    setForm(f => {
      const exists = f.help_articles.some(a => a.url === article.url);
      return {
        ...f,
        help_articles: exists
          ? f.help_articles.filter(a => a.url !== article.url)
          : [...f.help_articles, article],
      };
    });
  };

  const addCustomArticle = () => {
    setForm(f => ({
      ...f,
      help_articles: [...f.help_articles, { title: '', url: 'https://help.emergent.sh/' }],
    }));
  };

  const updateArticle = (idx, key, val) => {
    setForm(f => {
      const arts = [...f.help_articles];
      arts[idx] = { ...arts[idx], [key]: val };
      return { ...f, help_articles: arts };
    });
  };

  const removeArticle = (idx) => {
    setForm(f => ({ ...f, help_articles: f.help_articles.filter((_, i) => i !== idx) }));
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground py-8">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-sm">Loading categories...</span>
      </div>
    );
  }

  return (
    <div data-testid="portal-category-manager">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-muted-foreground">{categories.length} categories</p>
        <button
          onClick={openCreate}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-foreground text-background text-xs font-medium hover:opacity-90 transition-opacity"
          data-testid="add-category-btn"
        >
          <Plus size={13} />
          Add Category
        </button>
      </div>

      {/* Category List */}
      <div className="space-y-2">
        {categories.map((cat) => (
          <div
            key={cat.slug}
            className="rounded-lg border border-border/40 bg-secondary/20 overflow-hidden"
            data-testid={`admin-cat-${cat.slug}`}
          >
            <div className="flex items-center gap-3 px-4 py-3">
              <GripVertical size={14} className="text-muted-foreground/30 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium truncate">{cat.title}</span>
                  <span className="text-[10px] font-mono text-muted-foreground/40">/{cat.slug}</span>
                </div>
                {cat.help_articles?.length > 0 && (
                  <span className="text-[10px] text-muted-foreground/50">
                    {cat.help_articles.length} linked article{cat.help_articles.length > 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => setExpandedId(expandedId === cat.slug ? null : cat.slug)}
                  className="p-1.5 rounded hover:bg-muted/50 text-muted-foreground"
                  data-testid={`expand-cat-${cat.slug}`}
                >
                  {expandedId === cat.slug ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
                <button
                  onClick={() => openEdit(cat)}
                  className="p-1.5 rounded hover:bg-muted/50 text-muted-foreground hover:text-foreground"
                  data-testid={`edit-cat-${cat.slug}`}
                >
                  <Pencil size={13} />
                </button>
                <button
                  onClick={() => handleDelete(cat.slug)}
                  disabled={deleting === cat.slug}
                  className="p-1.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive disabled:opacity-50"
                  data-testid={`delete-cat-${cat.slug}`}
                >
                  {deleting === cat.slug ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                </button>
              </div>
            </div>

            {/* Expanded details */}
            {expandedId === cat.slug && (
              <div className="border-t border-border/20 px-4 py-3 bg-muted/10 space-y-2">
                <p className="text-xs text-muted-foreground">{cat.description}</p>
                {cat.subtopics?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-mono uppercase text-muted-foreground/50 mb-1">Subtopics</p>
                    <div className="flex flex-wrap gap-1.5">
                      {cat.subtopics.map((s, i) => (
                        <span key={i} className="text-[11px] px-2 py-0.5 rounded bg-secondary/50 border border-border/20">
                          {s.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {cat.help_articles?.length > 0 && (
                  <div>
                    <p className="text-[10px] font-mono uppercase text-muted-foreground/50 mb-1">Help Articles</p>
                    <div className="space-y-1">
                      {cat.help_articles.map((a, i) => (
                        <a
                          key={i}
                          href={a.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 text-[11px] text-primary hover:underline"
                        >
                          <ExternalLink size={10} />
                          {a.title || a.url}
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Modal Form */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" data-testid="category-form-modal">
          <div className="w-full max-w-lg bg-background border border-border rounded-xl shadow-2xl max-h-[85vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-border/40 shrink-0">
              <h3 className="text-base font-semibold">{editingCat ? 'Edit Category' : 'New Category'}</h3>
              <button onClick={() => setShowForm(false)} className="p-1 rounded hover:bg-muted" data-testid="close-category-form">
                <X size={16} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="px-5 py-4 space-y-4 overflow-y-auto flex-1">
              {/* Title & Slug */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Title</label>
                  <input
                    value={form.title}
                    onChange={e => {
                      const title = e.target.value;
                      setForm(f => ({ ...f, title, slug: !editingCat || f.slug === slugify(f.title || '') ? slugify(title) : f.slug }));
                    }}
                    placeholder="Category title"
                    className="w-full h-9 px-3 rounded-md border border-border bg-secondary/20 text-sm focus:outline-none focus:ring-1 focus:ring-foreground/20"
                    data-testid="cat-form-title"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Slug</label>
                  <input
                    value={form.slug}
                    onChange={e => setForm(f => ({ ...f, slug: e.target.value }))}
                    placeholder="category-slug"
                    className="w-full h-9 px-3 rounded-md border border-border bg-secondary/20 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-foreground/20"
                    data-testid="cat-form-slug"
                  />
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Description</label>
                <textarea
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Brief description..."
                  rows={2}
                  className="w-full px-3 py-2 rounded-md border border-border bg-secondary/20 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-foreground/20"
                  data-testid="cat-form-description"
                />
              </div>

              {/* Icon */}
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Icon</label>
                <div className="flex flex-wrap gap-1.5">
                  {ICON_OPTIONS.map(icon => (
                    <button
                      key={icon}
                      type="button"
                      onClick={() => setForm(f => ({ ...f, icon }))}
                      className={`px-2 py-1 rounded text-[10px] font-mono border transition-colors ${
                        form.icon === icon
                          ? 'bg-foreground text-background border-foreground'
                          : 'border-border/40 text-muted-foreground hover:border-foreground/30 hover:text-foreground'
                      }`}
                      data-testid={`icon-option-${icon}`}
                    >
                      {icon}
                    </button>
                  ))}
                </div>
              </div>

              {/* Subtopics */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-muted-foreground">Subtopics</label>
                  <button
                    type="button"
                    onClick={addSubtopic}
                    className="text-[10px] font-medium text-foreground/60 hover:text-foreground flex items-center gap-1"
                    data-testid="add-subtopic-btn"
                  >
                    <Plus size={10} />
                    Add
                  </button>
                </div>
                <div className="space-y-2">
                  {form.subtopics.map((sub, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <input
                        value={sub.name}
                        onChange={e => updateSubtopic(i, 'name', e.target.value)}
                        placeholder="Subtopic name"
                        className="flex-1 h-8 px-2.5 rounded-md border border-border/40 bg-secondary/20 text-xs focus:outline-none focus:ring-1 focus:ring-foreground/20"
                        data-testid={`subtopic-name-${i}`}
                      />
                      <button
                        onClick={() => removeSubtopic(i)}
                        className="p-1.5 rounded text-muted-foreground hover:text-destructive"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Help Articles */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                    <Link2 size={12} />
                    Help Articles
                  </label>
                  <button
                    type="button"
                    onClick={addCustomArticle}
                    className="text-[10px] font-medium text-foreground/60 hover:text-foreground flex items-center gap-1"
                    data-testid="add-custom-article-btn"
                  >
                    <Plus size={10} />
                    Custom URL
                  </button>
                </div>

                {/* Quick-pick from known articles */}
                <div className="mb-3 max-h-36 overflow-y-auto rounded-md border border-border/30 bg-secondary/10 p-2">
                  <p className="text-[10px] font-mono text-muted-foreground/50 mb-1.5">help.emergent.sh articles</p>
                  <div className="flex flex-wrap gap-1">
                    {HELP_ARTICLES.map(article => {
                      const selected = form.help_articles.some(a => a.url === article.url);
                      return (
                        <button
                          key={article.url}
                          type="button"
                          onClick={() => toggleHelpArticle(article)}
                          className={`text-[10px] px-2 py-0.5 rounded border transition-colors ${
                            selected
                              ? 'bg-foreground text-background border-foreground'
                              : 'border-border/30 text-muted-foreground hover:border-foreground/20 hover:text-foreground'
                          }`}
                          data-testid={`article-toggle-${article.title.replace(/\s+/g, '-').toLowerCase()}`}
                        >
                          {article.title}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Currently linked */}
                {form.help_articles.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-[10px] font-mono text-muted-foreground/50">Linked ({form.help_articles.length})</p>
                    {form.help_articles.map((art, i) => {
                      const isKnown = HELP_ARTICLES.some(a => a.url === art.url);
                      return (
                        <div key={i} className="flex items-center gap-2">
                          {isKnown ? (
                            <span className="flex-1 text-[11px] text-foreground/70 truncate">{art.title}</span>
                          ) : (
                            <>
                              <input
                                value={art.title}
                                onChange={e => updateArticle(i, 'title', e.target.value)}
                                placeholder="Title"
                                className="w-1/3 h-7 px-2 rounded border border-border/30 bg-secondary/20 text-[11px] focus:outline-none"
                              />
                              <input
                                value={art.url}
                                onChange={e => updateArticle(i, 'url', e.target.value)}
                                placeholder="https://help.emergent.sh/..."
                                className="flex-1 h-7 px-2 rounded border border-border/30 bg-secondary/20 text-[11px] font-mono focus:outline-none"
                              />
                            </>
                          )}
                          <button onClick={() => removeArticle(i)} className="p-1 rounded text-muted-foreground hover:text-destructive shrink-0">
                            <X size={11} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-border/40 shrink-0">
              <button
                onClick={() => setShowForm(false)}
                className="px-3 py-1.5 rounded-md text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                data-testid="cancel-category-form"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !form.title.trim()}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-foreground text-background text-xs font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                data-testid="save-category-btn"
              >
                {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
                {editingCat ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PortalCategoryManager;
