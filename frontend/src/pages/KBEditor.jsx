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
  Sun, Moon, Eye
} from 'lucide-react';
import { ArticleSidebar } from './kb-editor/ArticleSidebar';
import { RichTextEditor } from './kb-editor/RichTextEditor';
import { EDITOR_THEMES } from './kb-editor/editorTheme';
import { EditorThemeProvider } from './kb-editor/EditorThemeContext';
import { ArticlePreview } from './kb-editor/ArticlePreview';
import { UnifiedSettings } from './kb-editor/UnifiedSettings';
import { PageSettingsSlider } from './kb-editor/PageSettingsSlider';

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
  const pendingNewForm = useRef(null);

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
        (data.nav_groups || []).forEach(g => {
          exp[`group-${g.key}`] = true;
          g.sections?.forEach(s => { exp[`${g.key}-${s.key}`] = true; });
        });
        setExpanded(prev => ({ ...exp, ...prev }));
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
      const res = await fetch(`${API}/api/kb/admin/navigation`, { method: 'PUT', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nav_groups: newGroups }) });
      if (!res.ok) throw new Error('Failed to save');
      await fetchAll();
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

  // Open settings slider for a specific article
  const handleOpenSettings = useCallback((article) => {
    if (article.slug !== paramSlug) {
      navigate(`/dashboard/kb-editor/${article.slug}`);
    }
    // Small delay to let form load if navigating
    setTimeout(() => setShowPageSettings(true), article.slug !== paramSlug ? 200 : 0);
  }, [paramSlug, navigate]);

  // Create page under a specific group (first section)
  const handleCreateInGroup = useCallback((group) => {
    const firstSection = group.sections?.[0];
    setIsNew(true);
    setOriginalSlug(null);
    const newForm = {
      title: '', slug: '', description: '', content_markdown: '',
      nav_group_key: group.key, nav_group_label: group.label,
      section_key: firstSection?.key || '', section_label: firstSection?.label || '',
      published: false, order: articles.length,
      sidebar_title: '', keywords: [], tags: []
    };
    pendingNewForm.current = newForm;
    setForm(newForm);
    navigate('/dashboard/kb-editor/new', { replace: true });
  }, [articles, navigate]);

  // Create page under a specific section
  const handleCreateInSection = useCallback((groupKey, section) => {
    const group = navGroups.find(g => g.key === groupKey);
    setIsNew(true);
    setOriginalSlug(null);
    const newForm = {
      title: '', slug: '', description: '', content_markdown: '',
      nav_group_key: groupKey, nav_group_label: group?.label || '',
      section_key: section.key, section_label: section.label,
      published: false, order: articles.length,
      sidebar_title: '', keywords: [], tags: []
    };
    pendingNewForm.current = newForm;
    setForm(newForm);
    navigate('/dashboard/kb-editor/new', { replace: true });
  }, [articles, navGroups, navigate]);

  // Create new category (tab) via NavManager/UnifiedSettings
  const handleNewCategory = useCallback(() => {
    setShowSettings(true);
  }, []);

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
          onCreateInSection={handleCreateInSection}
          onCreateInGroup={handleCreateInGroup}
          theme={theme}
        />

        {/* Main Content — Editor Only */}
        <div className="flex-1 overflow-y-auto" data-testid="editor-main-area">
          {form ? (
            <div className="max-w-[800px] mx-auto px-6 py-8">
              {/* Editable title inline */}
              <div className="mb-6">
                <input
                  value={form.title || ''}
                  onChange={e => {
                    const title = e.target.value;
                    setForm(f => ({
                      ...f, title,
                      slug: isNew || f.slug === slugify(f.title || '') ? slugify(title) : f.slug
                    }));
                  }}
                  placeholder="Untitled page"
                  className={`w-full text-3xl font-bold bg-transparent border-none outline-none ${theme.text} ${theme.placeholder}`}
                  data-testid="editor-title-input"
                />
              </div>

              {/* Content Section */}
              <section data-testid="content-section">
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

      {/* Unified Settings */}
      {showSettings && (
        <UnifiedSettings
          navGroups={navGroups}
          onSaveNav={saveNavigation}
          onBulkMove={bulkMoveArticles}
          onClose={() => setShowSettings(false)}
          theme={theme}
          isDark={isDark}
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
        />
      )}
    </div>
  );
};

export default KBEditor;
