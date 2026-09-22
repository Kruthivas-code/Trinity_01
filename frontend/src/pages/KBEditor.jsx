/**
 * KBEditor — Knowledge Base article editor
 * Single-page layout: sidebar + content editor.
 * Page settings moved to a separate slider (accessed via sidebar hover gear icon).
 * Draft tag shown in header when page is unpublished.
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronLeft, Save, Loader2, Settings,
  Sun, Moon, Eye, History
} from 'lucide-react';
import { ArticleSidebar } from './kb-editor/ArticleSidebar';
import { RichTextEditor } from './kb-editor/RichTextEditor';
import { EDITOR_THEMES } from './kb-editor/editorTheme';
import { EditorThemeProvider } from './kb-editor/EditorThemeContext';
import { ArticlePreview } from './kb-editor/ArticlePreview';
import { UnifiedSettings } from './kb-editor/UnifiedSettings';
import { PageSettingsSlider } from './kb-editor/PageSettingsSlider';
import { PageMetaDialog } from './kb-editor/PageMetaDialog';
import { VersionHistoryPanel } from './kb-editor/VersionHistoryPanel';
import { WritingAssistant, WritingAssistantTrigger } from './kb-editor/WritingAssistant';
import { AnchorsMenu } from './kb-editor/AnchorsMenu';

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
  const [showSettings, setShowSettings] = useState(false);
  const [editMode, setEditMode] = useState('visual');
  const [showPreview, setShowPreview] = useState(false);
  const [showPageSettings, setShowPageSettings] = useState(false);
  const [showPageMeta, setShowPageMeta] = useState(false);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [showAssistant, setShowAssistant] = useState(false);
  // Tracks the markdown textarea's current text selection so Tweak mode can
  // offer "rewrite just this" instead of always targeting the whole
  // document. Only meaningful in Markdown edit mode -- the visual (TipTap)
  // editor doesn't expose a plain-text offset selection, so Tweak always
  // targets the whole document there.
  const [mdSelection, setMdSelection] = useState(null);
  const pendingNewForm = useRef(null);

  // Owner-gating (Phase 1): structural controls (delete a page, edit the nav
  // tree, edit global docs settings/design config) are owner-only server
  // side now — mirror that here so the UI doesn't show controls that would
  // just 403. Same endpoint ReviewConsole.jsx already uses for this.
  // Defaults to false (hide owner-only controls) until the check resolves,
  // so a non-owner never sees a flash of controls they can't use.
  const [isOwner, setIsOwner] = useState(false);
  useEffect(() => {
    fetch(`${API}/api/review/roles/me`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setIsOwner(!!d.is_owner); })
      .catch(() => {});
  }, []);

  // Theme — follow system preference if no stored preference
  const [editorTheme, setEditorTheme] = useState(() => {
    const stored = localStorage.getItem('kb-editor-theme');
    if (stored) return stored;
    if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches) return 'dark';
    return 'light';
  });
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
        setNavGroups(data.groups || []);
        return data;
      }
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
    return null;
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Auto-select first article when no slug is specified
  useEffect(() => {
    if (!paramSlug && !form && articles.length > 0) {
      navigate(`/dashboard/kb-editor/${articles[0].slug}`, { replace: true });
    }
  }, [paramSlug, articles, form, navigate]);

  // Load article when slug changes
  useEffect(() => {
    if (!paramSlug) return;
    if (paramSlug === 'new') {
      setIsNew(true);
      setOriginalSlug(null);
      // Use pre-filled form from handleCreateInSection/Group if available
      if (pendingNewForm.current) {
        setForm(pendingNewForm.current);
        pendingNewForm.current = null;
      } else {
        setForm({
          title: '', slug: '', description: '', content_markdown: '',
          nav_group_key: '', nav_group_label: '',
          section_key: '', section_label: '',
          published: false, order: 0,
          sidebar_title: '', keywords: [], tags: []
        });
      }
      return;
    }
    const loadArticle = async () => {
      try {
        const res = await fetch(`${API}/api/kb/admin/articles/${paramSlug}`, { credentials: 'include' });
        if (res.ok) {
          const art = await res.json();
          setIsNew(false);
          setOriginalSlug(art.slug);
          setForm({ ...art, keywords: art.keywords || [], tags: art.tags || [], sidebar_title: art.sidebar_title || '' });
        }
      } catch (e) { console.error('Failed to load article:', e); }
    };
    loadArticle();
  }, [paramSlug]); // eslint-disable-line react-hooks/exhaustive-deps

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
      // Phase 4: for an EXISTING article, a slug change goes exclusively
      // through the guarded PageMetaDialog flow (redirect + internal-link
      // rewrite + owner gate + explicit confirmation) — never as a silent
      // side effect of the regular Save button. Strip slug from this
      // payload entirely so a stray local form.slug (there shouldn't be
      // one now that PageSettingsSlider no longer edits it directly, but
      // better to guard the payload itself than rely on that) can never
      // trigger update_article's slug-change path from here. New articles
      // are unaffected — slug is part of the initial POST, no redirect
      // needed for a page that doesn't exist yet.
      if (!isNew) delete payload.slug;
      const url = isNew ? `${API}/api/kb/admin/articles` : `${API}/api/kb/admin/articles/${originalSlug}`;
      const method = isNew ? 'POST' : 'PUT';
      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify(payload) });
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || `Save failed (${res.status})`); }
      setLastSaved(new Date());
      if (isNew) {
        setIsNew(false);
        setOriginalSlug(slug);
        navigate(`/dashboard/kb-editor/${slug}`, { replace: true });
      }
      await fetchAll();
    } catch (e) { console.error(e); alert(e.message); }
    finally { setSaving(false); }
  }, [form, isNew, originalSlug, navigate, fetchAll, canSave]);

  // Page Meta Dialog (Phase 4) — the ONLY path that can change an existing
  // article's slug. Merges the server's response (which may include title/
  // icon/description AND, on a slug change, the new slug + a slug_change
  // summary) back into local form state and, if the slug moved, updates
  // originalSlug and the URL to match.
  const handleMetaSaved = useCallback((updated) => {
    setForm(f => (f ? { ...f, ...updated } : f));
    if (updated.slug_change) {
      const { new_slug, pages_touched, links_updated } = updated.slug_change;
      setOriginalSlug(new_slug);
      navigate(`/dashboard/kb-editor/${new_slug}`, { replace: true });
      if (links_updated > 0) {
        alert(`Slug changed. ${links_updated} internal link${links_updated === 1 ? '' : 's'} updated across ${pages_touched} page${pages_touched === 1 ? '' : 's'}, and a redirect from the old URL was created.`);
      }
    }
    setLastSaved(new Date());
    fetchAll();
  }, [fetchAll, navigate]);

  // Cmd+S
  useEffect(() => {
    const handler = (e) => { if ((e.metaKey || e.ctrlKey) && e.key === 's') { e.preventDefault(); handleSave(); } };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleSave]);

  const handleDelete = async (slug) => {
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

  // Image upload
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
      const res = await fetch(`${API}/api/kb/admin/navigation`, { method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ groups: newGroups }) });
      if (!res.ok) throw new Error('Failed to save');
      await fetchAll();
    } catch (e) { alert('Failed to save navigation: ' + e.message); }
  };

  // Build the sidebar's display tree: the raw nav tree (groups referencing
  // pages by slug) annotated with each page's resolved article, recursively.
  const articlesBySlug = useMemo(() => new Map(articles.map(a => [a.slug, a])), [articles]);
  const buildDisplayTree = useCallback((nodes) => (nodes || []).map(node => (
    node.type === 'page'
      ? { type: 'page', slug: node.slug, article: articlesBySlug.get(node.slug) || null }
      : { type: 'group', key: node.key, label: node.label, icon: node.icon, published: node.published, children: buildDisplayTree(node.children || []) }
  )), [articlesBySlug]);
  const tree = useMemo(() => buildDisplayTree(navGroups), [navGroups, buildDisplayTree]);

  // Open settings slider for a specific article
  const handleOpenSettings = useCallback((article) => {
    if (article.slug !== paramSlug) {
      navigate(`/dashboard/kb-editor/${article.slug}`);
    }
    // Small delay to let form load if navigating
    setTimeout(() => setShowPageSettings(true), article.slug !== paramSlug ? 200 : 0);
  }, [paramSlug, navigate]);

  // Create a page directly inside a specific nav-tree group, wherever it
  // lives in the tree. `topGroupKey` is the top-level ancestor group's key
  // (nav_group_key); `group` is the exact group node the "+" was clicked on
  // (section_key) — which may be that same top-level group itself.
  const handleCreatePage = useCallback((topGroupKey, group) => {
    const topGroup = navGroups.find(g => g.key === topGroupKey);
    setIsNew(true);
    setOriginalSlug(null);
    const newForm = {
      title: '', slug: '', description: '', content_markdown: '',
      nav_group_key: topGroupKey, nav_group_label: topGroup?.label || '',
      section_key: group.key, section_label: group.label,
      published: false, order: articles.length,
      sidebar_title: '', keywords: [], tags: []
    };
    pendingNewForm.current = newForm;
    setForm(newForm);
    navigate('/dashboard/kb-editor/new', { replace: true });
  }, [articles, navGroups, navigate]);

  // Create new top-level group — done from Settings > Navigation (NavManager)
  const handleNewCategory = useCallback(() => {
    setShowSettings(true);
  }, []);

  // Writing Assistant — Tweak mode applies its proposal straight onto the
  // in-memory form; nothing is saved until the existing Save button is
  // pressed, same as any other content edit.
  const applyAssistantContent = useCallback((markdown) => {
    setForm((f) => (f ? { ...f, content_markdown: markdown } : f));
  }, []);
  const applyAssistantSelection = useCallback((replacement, start, end) => {
    setForm((f) => {
      if (!f) return f;
      const cm = f.content_markdown || '';
      return { ...f, content_markdown: cm.slice(0, start) + replacement + cm.slice(end) };
    });
    setMdSelection(null);
  }, []);

  // Writing Assistant — New Page mode never creates a page itself (see
  // WritingAssistant.jsx's header comment). It hands back a fully-formed
  // draft, and this does exactly what handleCreatePage above does for the
  // sidebar's own "+" button: pre-fill the new-page form and route to
  // /dashboard/kb-editor/new. Saving from there is the same, unmodified,
  // owner-gated POST /api/kb/admin/articles.
  const handleAssistantNewPage = useCallback((draft) => {
    setIsNew(true);
    setOriginalSlug(null);
    const newForm = {
      title: draft.title, slug: draft.slug, description: '', content_markdown: draft.content_markdown,
      nav_group_key: draft.nav_group_key, nav_group_label: draft.nav_group_label,
      section_key: draft.section_key, section_label: draft.section_label,
      published: false, order: articles.length,
      sidebar_title: '', keywords: [], tags: []
    };
    pendingNewForm.current = newForm;
    setForm(newForm);
    navigate('/dashboard/kb-editor/new', { replace: true });
  }, [articles, navigate]);

  if (loading) {
    return <div className={`h-screen flex items-center justify-center ${theme.bg}`}><Loader2 className="w-6 h-6 animate-spin text-[#00A1B2]" /></div>;
  }

  const bgStyle = isDark ? {} : { backgroundColor: '#ffffff' };
  const panelBgStyle = isDark ? {} : { backgroundColor: '#f9fafb' };

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
          <button onClick={() => setShowSettings(true)} className={`p-2 rounded-lg transition-colors ${theme.textMuted} ${theme.hoverText} ${theme.hover}`} title="Settings" data-testid="settings-toggle">
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
          {/* Anchors Menu (Phase 4) — deep-link headings/anchors, content-level
              like the writing assistant, not owner-gated. */}
          {form && !isNew && (
            <AnchorsMenu
              content={form.content_markdown || ''}
              onContentChange={(md) => setForm(f => ({ ...f, content_markdown: md }))}
              slug={originalSlug || form.slug}
              theme={theme}
            />
          )}
          {/* AI Writing Assistant (Phase 3) — content-level AI help stays
              open to any signed-in user, same as content edits themselves
              (Phase 1 philosophy). Not owner-gated. */}
          {form && (
            <WritingAssistantTrigger onOpen={() => setShowAssistant(true)} isDark={isDark} />
          )}
          {/* Version History — owner-only (Phase 2), matches the backend's
              owner-gated GET/POST/DELETE /api/kb/admin/articles/{slug}/versions... */}
          {form && !isNew && isOwner && (
            <button
              onClick={() => setShowVersionHistory(true)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isDark ? 'bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700' : 'bg-gray-100 text-gray-600 hover:text-gray-900 hover:bg-gray-200'}`}
              title="Version history"
              data-testid="version-history-btn"
            >
              <History className="w-4 h-4" />
              <span className="hidden sm:inline">History</span>
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
        <ArticleSidebar
          tree={tree}
          selectedSlug={paramSlug}
          onSelect={(slug) => navigate(`/dashboard/kb-editor/${slug}`)}
          expanded={expanded}
          setExpanded={setExpanded}
          onNewCategory={handleNewCategory}
          onOpenSettings={handleOpenSettings}
          onCreatePage={handleCreatePage}
          theme={theme}
          isOwner={isOwner}
        />

        {/* Main Content — Editor Only */}
        <div className="flex-1 overflow-y-auto" data-testid="editor-main-area">
          {form ? (
            <div className="max-w-[800px] mx-auto px-6 py-8 flex flex-col" style={{ minHeight: 'calc(100vh - 56px)' }}>
              {/* Editable title inline */}
              <div className="mb-6">
                <input
                  value={form.title || ''}
                  onChange={e => {
                    const title = e.target.value;
                    setForm(f => ({
                      ...f, title,
                      // Phase 4: only auto-derive the slug from the title for
                      // a brand-new, unsaved page. For an EXISTING article,
                      // form.slug must stay pinned to originalSlug between
                      // saves — the guarded PageMetaDialog flow (redirect +
                      // link rewrite + confirmation) is the only way its
                      // slug is allowed to change, and handleSave() also
                      // strips slug from the save payload as a second guard.
                      slug: isNew ? slugify(title) : f.slug
                    }));
                  }}
                  placeholder="Untitled page"
                  className={`w-full text-3xl font-bold bg-transparent border-none outline-none ${theme.text} ${theme.placeholder}`}
                  data-testid="editor-title-input"
                />
              </div>

              {/* Content Section */}
              <section data-testid="content-section" className="flex-1 flex flex-col">
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
                    onSelect={(e) => {
                      const { selectionStart, selectionEnd } = e.target;
                      if (selectionEnd > selectionStart) {
                        setMdSelection({
                          text: (form.content_markdown || '').slice(selectionStart, selectionEnd),
                          start: selectionStart, end: selectionEnd,
                        });
                      } else {
                        setMdSelection(null);
                      }
                    }}
                    className={`w-full flex-1 px-4 py-3 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm font-mono ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors resize-none leading-relaxed`}
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

      {/* Unified Settings */}
      {showSettings && (
        <UnifiedSettings
          navGroups={navGroups}
          articles={articles}
          onSaveNav={saveNavigation}
          onClose={() => setShowSettings(false)}
          theme={theme}
          isDark={isDark}
          isOwner={isOwner}
          onRefresh={fetchAll}
        />
      )}

      {/* Version History Panel */}
      {showVersionHistory && form && !isNew && (
        <VersionHistoryPanel
          slug={originalSlug || form.slug}
          articleTitle={form.title}
          isDark={isDark}
          onClose={() => setShowVersionHistory(false)}
          onRestore={(restoredArticle) => {
            if (restoredArticle) {
              setForm(f => ({ ...f, ...restoredArticle, keywords: restoredArticle.keywords || [], tags: restoredArticle.tags || [] }));
            }
            fetchAll();
          }}
        />
      )}

      {/* AI Writing Assistant (Phase 3) */}
      {showAssistant && form && (
        <WritingAssistant
          open={showAssistant}
          onClose={() => setShowAssistant(false)}
          isDark={isDark}
          content={form.content_markdown || ''}
          selection={editMode === 'markdown' ? mdSelection : null}
          onApplyContent={applyAssistantContent}
          onApplySelection={applyAssistantSelection}
          navGroups={navGroups}
          articlesCount={articles.length}
          onDraftNewPage={handleAssistantNewPage}
        />
      )}

      {/* Page Settings Slider */}
      {showPageSettings && form && (
        <PageSettingsSlider
          form={form}
          setForm={setForm}
          onSave={handleSave}
          onDelete={handleDelete}
          onClose={() => setShowPageSettings(false)}
          isDark={isDark}
          isOwner={isOwner}
          onOpenMeta={!isNew ? () => setShowPageMeta(true) : undefined}
        />
      )}

      {/* Page Meta Dialog (Phase 4) — title/slug/icon/description, guarded
          slug change. Only meaningful for an already-saved article. */}
      {showPageMeta && form && !isNew && (
        <PageMetaDialog
          open={showPageMeta}
          article={{ slug: originalSlug, title: form.title, icon: form.icon, description: form.description }}
          isOwner={isOwner}
          isDark={isDark}
          onClose={() => setShowPageMeta(false)}
          onSaved={handleMetaSaved}
        />
      )}
    </div>
  );
};

export default KBEditor;
