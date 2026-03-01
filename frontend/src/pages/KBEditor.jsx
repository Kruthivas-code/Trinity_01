/**
 * KBEditor — Knowledge Base article editor
 * Single-page layout with Document Settings, Draft, and Rich Text Content sections.
 * Supports Visual Edit and Markdown modes with a full Preview page.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronLeft, Save, Loader2, Settings,
  Sun, Moon, Share2, Globe, Eye
} from 'lucide-react';
import { ArticleSidebar } from './kb-editor/ArticleSidebar';
import { NavManager } from './kb-editor/NavManager';
import { SocialLinksPanel } from './kb-editor/SocialLinksPanel';
import { GlobalSettingsModal } from './kb-editor/GlobalSettingsModal';
import { RichTextEditor } from './kb-editor/RichTextEditor';
import { EDITOR_THEMES } from './kb-editor/editorTheme';
import { EditorThemeProvider } from './kb-editor/EditorThemeContext';
import { ArticlePreview } from './kb-editor/ArticlePreview';

const API = process.env.REACT_APP_BACKEND_URL;

const KBEditor = () => {
  const { slug: paramSlug } = useParams();
  const navigate = useNavigate();

  const [articles, setArticles] = useState([]);
  const [navGroups, setNavGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(null);
  const [originalSlug, setOriginalSlug] = useState(null);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [isNew, setIsNew] = useState(false);
  const [expanded, setExpanded] = useState({});
  const [navManagerOpen, setNavManagerOpen] = useState(false);
  const [socialLinksOpen, setSocialLinksOpen] = useState(false);
  const [globalSettingsOpen, setGlobalSettingsOpen] = useState(false);
  const [editMode, setEditMode] = useState('visual');
  const [showPreview, setShowPreview] = useState(false);

  // Theme
  const [editorTheme, setEditorTheme] = useState(() => localStorage.getItem('kb-editor-theme') || 'dark');
  const isDark = editorTheme === 'dark';
  const theme = isDark ? EDITOR_THEMES.dark : EDITOR_THEMES.light;

  const toggleTheme = useCallback(() => {
    setEditorTheme(prev => {
      const next = prev === 'dark' ? 'light' : 'dark';
      localStorage.setItem('kb-editor-theme', next);
      return next;
    });
  }, []);

  useEffect(() => {
    if (isDark) document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
    return () => { document.documentElement.classList.remove('dark'); };
  }, [isDark]);

  useEffect(() => {
    document.documentElement.style.overflow = 'hidden';
    document.body.style.overflow = 'hidden';
    return () => { document.documentElement.style.overflow = ''; document.body.style.overflow = ''; };
  }, []);

  const slugify = (t) => t.toLowerCase().trim().replace(/[^\w\s-]/g, '').replace(/[\s_]+/g, '-').replace(/-+/g, '-');

  // Fetch data
  const fetchAll = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/kb/admin/articles`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setArticles(data.articles || []);
        setNavGroups(data.nav_groups || []);
        const exp = {};
        (data.nav_groups || []).forEach(g => { g.sections?.forEach(s => { exp[`${g.key}-${s.key}`] = true; }); });
        setExpanded(exp);
        return data;
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
    return null;
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Load article when slug changes or auto-select first
  useEffect(() => {
    if (!paramSlug || paramSlug === 'new') {
      if (paramSlug === 'new') {
        setIsNew(true);
        setOriginalSlug(null);
        setForm({
          title: '', slug: '', description: '', content_markdown: '',
          nav_group_key: '', nav_group_label: '',
          section_key: '', section_label: '',
          published: false, order: articles.length
        });
      } else if (articles.length > 0 && !form) {
        navigate(`/dashboard/kb-editor/${articles[0].slug}`, { replace: true });
      }
      return;
    }
    // Lazy-load full article content (content_markdown excluded from listing)
    const loadArticle = async () => {
      try {
        const res = await fetch(`${API}/api/kb/admin/articles/${paramSlug}`, { credentials: 'include' });
        if (res.ok) {
          const art = await res.json();
          setIsNew(false);
          setOriginalSlug(art.slug);
          setForm({ ...art });
        }
      } catch (e) { console.error('Failed to load article:', e); }
    };
    loadArticle();
  }, [paramSlug, articles, navGroups, navigate]);

  // Validation
  const canSave = form && form.title?.trim() && form.slug?.trim();

  // Save
  const handleSave = useCallback(async () => {
    if (!canSave) return;
    setSaving(true);
    try {
      const slug = form.slug.trim();
      const payload = { ...form, slug };
      delete payload.created_at; delete payload.updated_at; delete payload.source_url;
      delete payload.feedback_total; delete payload.feedback_helpful;
      const url = isNew ? `${API}/api/kb/admin/articles` : `${API}/api/kb/admin/articles/${originalSlug}`;
      const method = isNew ? 'POST' : 'PUT';
      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify(payload) });
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'Save failed'); }
      setLastSaved(new Date());
      if (isNew || slug !== originalSlug) {
        setIsNew(false);
        setOriginalSlug(slug);
        navigate(`/dashboard/kb-editor/${slug}`, { replace: true });
      }
      await fetchAll();
    } catch (e) { console.error(e); alert(e.message); }
    finally { setSaving(false); }
  }, [form, isNew, originalSlug, navigate, fetchAll, canSave]);

  // Cmd+S
  useEffect(() => {
    const handler = (e) => { if ((e.metaKey || e.ctrlKey) && e.key === 's') { e.preventDefault(); handleSave(); } };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleSave]);

  const handleDelete = async (slug) => {
    if (!window.confirm('Delete this article permanently?')) return;
    setDeleting(slug);
    try {
      await fetch(`${API}/api/kb/admin/articles/${slug}`, { method: 'DELETE', credentials: 'include' });
      if (paramSlug === slug) {
        setForm(null);
        navigate('/dashboard/kb-editor', { replace: true });
      }
      await fetchAll();
    } catch (e) { console.error(e); }
    finally { setDeleting(null); }
  };

  // Image upload — returns URL
  const uploadImage = useCallback(async (file) => {
    if (!file || !file.type.startsWith('image/')) return null;
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API}/api/kb/admin/images`, { method: 'POST', credentials: 'include', body: formData });
      if (!res.ok) throw new Error('Upload failed');
      const { url } = await res.json();
      return url;
    } catch (e) { console.error(e); alert(`Image upload failed: ${e.message}`); return null; }
  }, []);

  const saveNavigation = async (newGroups) => {
    try {
      const res = await fetch(`${API}/api/kb/admin/navigation`, { method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nav_groups: newGroups }) });
      if (!res.ok) throw new Error('Failed to save');
      await fetchAll();
      setNavManagerOpen(false);
    } catch (e) { alert('Failed to save navigation: ' + e.message); }
  };

  const bulkMoveArticles = async (srcGroupKey, srcSectionKey, tgtGroupKey, tgtGroupLabel, tgtSectionKey, tgtSectionLabel) => {
    try {
      const res = await fetch(`${API}/api/kb/admin/articles/bulk-move`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_group_key: srcGroupKey, source_section_key: srcSectionKey, target_group_key: tgtGroupKey, target_group_label: tgtGroupLabel, target_section_key: tgtSectionKey, target_section_label: tgtSectionLabel })
      });
      if (!res.ok) throw new Error('Failed to move');
      const data = await res.json();
      await fetchAll();
      return data.moved;
    } catch (e) { alert('Failed to move articles: ' + e.message); return 0; }
  };

  // Build sidebar tree
  const tree = useMemo(() => navGroups.map(group => ({
    ...group,
    sections: (group.sections || []).map(sec => ({
      ...sec,
      articles: articles.filter(a => a.section_key === sec.key && a.nav_group_key === group.key),
    })),
  })), [navGroups, articles]);

  // Flatten sections for category dropdown
  const categoryOptions = useMemo(() => {
    const opts = [];
    navGroups.forEach(g => {
      opts.push({ type: 'group', key: g.key, label: g.label });
      (g.sections || []).forEach(s => {
        opts.push({ type: 'section', groupKey: g.key, groupLabel: g.label, key: s.key, label: s.label });
      });
    });
    return opts;
  }, [navGroups]);

  if (loading) {
    return <div className={`h-screen flex items-center justify-center ${theme.bg}`}><Loader2 className="w-6 h-6 animate-spin text-[#00A1B2]" /></div>;
  }

  const bgStyle = isDark ? {} : { backgroundColor: '#ffffff' };
  const panelBgStyle = isDark ? {} : { backgroundColor: '#f9fafb' };

  // Get the preview URL for the slug
  const docsBaseUrl = window.location.origin + '/docs/';

  return (
    <div className={`h-screen ${theme.bg} flex flex-col`} style={bgStyle} data-testid="kb-editor-page">
      {/* Header */}
      <header className={`h-14 flex items-center px-4 border-b ${theme.border} ${theme.panelBg} flex-shrink-0 gap-3 z-30`} style={panelBgStyle} data-testid="editor-header">
        <button onClick={() => navigate('/dashboard/settings')} className={`flex items-center gap-2 ${theme.textMuted} ${theme.hoverText} transition-colors`} data-testid="back-to-dashboard">
          <ChevronLeft className="w-4 h-4" /><span className="text-sm">Dashboard</span>
        </button>
        <div className={`w-px h-6 ${theme.divider}`} />

        {/* Edit Mode Toggle */}
        {form ? (
          <div className={`flex items-center rounded-lg p-0.5 ${isDark ? 'bg-slate-800/80' : 'bg-gray-100'}`} data-testid="edit-mode-toggle">
            <button
              onClick={() => setEditMode('visual')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${editMode === 'visual' ? 'bg-[#00A1B2] text-white shadow-sm' : `${theme.textMuted} ${theme.hoverText}`}`}
              data-testid="visual-edit-toggle"
            >
              Visual Edit
            </button>
            <button
              onClick={() => setEditMode('markdown')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${editMode === 'markdown' ? 'bg-[#00A1B2] text-white shadow-sm' : `${theme.textMuted} ${theme.hoverText}`}`}
              data-testid="markdown-edit-toggle"
            >
              Markdown
            </button>
          </div>
        ) : (
          <span className={`text-sm font-medium ${theme.text} truncate`}>Knowledge Base Editor</span>
        )}

        <div className="flex items-center gap-2 ml-auto flex-shrink-0">
          <button onClick={toggleTheme} className={`p-2 rounded-lg ${theme.textMuted} ${theme.hoverText} ${theme.hover} transition-colors`} title={isDark ? 'Switch to light mode' : 'Switch to dark mode'} data-testid="kb-editor-theme-toggle">
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <button onClick={() => setSocialLinksOpen(!socialLinksOpen)} className={`p-2 rounded-lg transition-colors ${socialLinksOpen ? 'bg-[#00A1B2] text-white' : `${theme.textMuted} ${theme.hoverText} ${theme.hover}`}`} title="Social Links" data-testid="social-links-toggle">
            <Share2 className="w-4 h-4" />
          </button>
          <button onClick={() => setGlobalSettingsOpen(true)} className={`p-2 rounded-lg transition-colors ${globalSettingsOpen ? 'bg-[#00A1B2] text-white' : `${theme.textMuted} ${theme.hoverText} ${theme.hover}`}`} title="Global Docs Settings" data-testid="global-settings-toggle">
            <Settings className="w-4 h-4" />
          </button>
          {form && (
            <button
              onClick={() => setShowPreview(true)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isDark ? 'bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700' : 'bg-gray-100 text-gray-600 hover:text-gray-900 hover:bg-gray-200'}`}
              title="Preview article"
              data-testid="preview-btn"
            >
              <Eye className="w-4 h-4" />
              <span className="hidden sm:inline">Preview</span>
            </button>
          )}
          <div className={`w-px h-6 ${theme.divider}`} />
          {lastSaved && <span className={`text-xs ${theme.textSecondary} hidden sm:block`}>Saved {lastSaved.toLocaleTimeString()}</span>}
          <button onClick={handleSave} disabled={saving || !canSave}
            className="flex items-center gap-2 px-4 py-2 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-opacity"
            data-testid="save-btn">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            <span className="hidden sm:inline">Save</span>
          </button>
        </div>
      </header>

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Sidebar */}
        <ArticleSidebar tree={tree} selectedSlug={paramSlug} onSelect={(slug) => navigate(`/dashboard/kb-editor/${slug}`)} onDelete={handleDelete} deleting={deleting} expanded={expanded} setExpanded={setExpanded} onNewArticle={() => navigate('/dashboard/kb-editor/new')} onManageNav={() => setNavManagerOpen(true)} theme={theme} />

        {/* Main Content — Single Scrollable Page */}
        <div className="flex-1 overflow-y-auto" data-testid="editor-main-area">
          {form ? (
            <div className="max-w-3xl mx-auto px-6 py-8 space-y-8">

              {/* === Document Section (Meta) === */}
              <section data-testid="document-section">
                <h2 className={`text-xs font-semibold uppercase tracking-wider ${theme.textSecondary} mb-4`}>Document</h2>

                {/* Meta Title */}
                <div className="mb-4">
                  <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>Meta Title <span className="text-red-400">*</span></label>
                  <input
                    value={form.title || ''}
                    onChange={e => {
                      const title = e.target.value;
                      setForm(f => ({
                        ...f, title,
                        slug: isNew || f.slug === slugify(f.title || '') ? slugify(title) : f.slug
                      }));
                    }}
                    placeholder="Article meta title..."
                    className={`w-full px-3 py-2.5 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors`}
                    style={theme.inputBgStyle}
                    data-testid="editor-title-input"
                  />
                </div>

                {/* Meta Description */}
                <div className="mb-4">
                  <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>Meta Description</label>
                  <input
                    value={form.description || ''}
                    onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                    placeholder="Brief meta description for SEO..."
                    className={`w-full px-3 py-2.5 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors`}
                    style={theme.inputBgStyle}
                    data-testid="editor-description-input"
                  />
                </div>

                {/* Slug */}
                <div className="mb-1">
                  <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>Slug <span className="text-red-400">*</span></label>
                  <input
                    value={form.slug || ''}
                    onChange={e => setForm(f => ({ ...f, slug: e.target.value }))}
                    placeholder="article-slug"
                    className={`w-full px-3 py-2.5 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} font-mono ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors`}
                    style={theme.inputBgStyle}
                    data-testid="editor-slug-input"
                  />
                </div>
                {form.slug && (
                  <div className={`flex items-center gap-2 text-xs ${theme.textSecondary} mt-1.5 mb-4`} data-testid="slug-preview">
                    <Globe className="w-3.5 h-3.5" />
                    <span className="font-mono">{docsBaseUrl}{form.slug}</span>
                  </div>
                )}

                {/* Category */}
                <div className="mb-4">
                  <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>Category</label>
                  <select
                    value={form.nav_group_key || ''}
                    onChange={e => {
                      const groupKey = e.target.value;
                      const g = navGroups.find(g => g.key === groupKey);
                      setForm(f => ({
                        ...f,
                        nav_group_key: groupKey,
                        nav_group_label: g?.label || '',
                        section_key: '',
                        section_label: '',
                      }));
                    }}
                    className={`w-full px-3 py-2.5 ${theme.selectBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} focus:border-[#00A1B2] focus:outline-none transition-colors`}
                    data-testid="editor-category-select"
                  >
                    <option value="">No category</option>
                    {navGroups.map(g => <option key={g.key} value={g.key}>{g.label}</option>)}
                  </select>
                </div>

                {/* Subcategory (Section) — optional */}
                {form.nav_group_key && (
                  <div className="mb-4">
                    <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>Subcategory <span className={`${theme.textSecondary} font-normal`}>(optional)</span></label>
                    <select
                      value={form.section_key || ''}
                      onChange={e => {
                        const sectionKey = e.target.value;
                        const g = navGroups.find(g => g.key === form.nav_group_key);
                        const s = g?.sections?.find(s => s.key === sectionKey);
                        setForm(f => ({
                          ...f,
                          section_key: sectionKey,
                          section_label: s?.label || '',
                        }));
                      }}
                      className={`w-full px-3 py-2.5 ${theme.selectBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} focus:border-[#00A1B2] focus:outline-none transition-colors`}
                      data-testid="editor-subcategory-select"
                    >
                      <option value="">None (directly under category)</option>
                      {(navGroups.find(g => g.key === form.nav_group_key)?.sections || []).map(s => (
                        <option key={s.key} value={s.key}>{s.label}</option>
                      ))}
                    </select>
                  </div>
                )}
              </section>

              {/* === Draft Section === */}
              <section className={`border-t ${theme.border} pt-6`} data-testid="draft-section">
                <h2 className={`text-xs font-semibold uppercase tracking-wider ${theme.textSecondary} mb-4`}>Publishing</h2>
                <div className="flex items-center justify-between">
                  <div>
                    <p className={`text-sm font-medium ${theme.text}`}>
                      {form.published ? 'Published' : 'Draft'}
                    </p>
                    <p className={`text-xs ${theme.textSecondary} mt-0.5`}>
                      {form.published ? 'This article is visible to the public.' : 'This article is saved as a draft and not visible to the public.'}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setForm(f => ({ ...f, published: !f.published }))}
                    className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${form.published ? 'bg-[#00A1B2]' : isDark ? 'bg-slate-700' : 'bg-gray-300'}`}
                    role="switch"
                    aria-checked={form.published}
                    data-testid="publish-toggle"
                  >
                    <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${form.published ? 'translate-x-5' : 'translate-x-0'}`} />
                  </button>
                </div>
              </section>

              {/* === Content Section === */}
              <section className={`border-t ${theme.border} pt-6`} data-testid="content-section">
                <h2 className={`text-xs font-semibold uppercase tracking-wider ${theme.textSecondary} mb-4`}>Content</h2>
                {editMode === 'visual' ? (
                  <EditorThemeProvider value={editorTheme}>
                    <RichTextEditor
                      content={form.content_markdown || ''}
                      onChange={(md) => setForm(f => ({ ...f, content_markdown: md }))}
                      theme={theme}
                      onUploadImage={uploadImage}
                    />
                  </EditorThemeProvider>
                ) : (
                  <textarea
                    value={form.content_markdown || ''}
                    onChange={(e) => setForm(f => ({ ...f, content_markdown: e.target.value }))}
                    className={`w-full min-h-[500px] px-4 py-3 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm font-mono ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors resize-y leading-relaxed`}
                    style={theme.inputBgStyle}
                    placeholder="Write your article content in Markdown..."
                    data-testid="markdown-textarea"
                  />
                )}
              </section>

            </div>
          ) : (
            <div className={`flex-1 flex items-center justify-center h-full ${theme.textSecondary}`}>
              <div className="text-center">
                <p className="text-lg mb-2">Select an article or create a new one</p>
                <p className="text-sm">Use the sidebar to navigate your articles</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Preview Overlay */}
      {showPreview && (
        <ArticlePreview
          form={form}
          isDark={isDark}
          onBack={() => setShowPreview(false)}
        />
      )}

      {/* Modals */}
      {navManagerOpen && <NavManager navGroups={navGroups} onSave={saveNavigation} onBulkMove={bulkMoveArticles} onClose={() => setNavManagerOpen(false)} theme={theme} />}
      {socialLinksOpen && <SocialLinksPanel onClose={() => setSocialLinksOpen(false)} theme={theme} />}
      {globalSettingsOpen && <GlobalSettingsModal onClose={() => setGlobalSettingsOpen(false)} theme={theme} />}
    </div>
  );
};

export default KBEditor;
