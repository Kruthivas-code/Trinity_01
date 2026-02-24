/**
 * KBEditor — Knowledge Base article editor
 * Refactored: Components split into kb-editor/ directory
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronLeft, Save, Eye, Code2, Loader2, FileText, Settings,
  Monitor, Smartphone, Tablet, SplitSquareVertical, ExternalLink,
  Image as ImageIcon, Sun, Moon
} from 'lucide-react';
import { DocContent } from '../components/docs/DocContent';
import { EditorToolbar } from './kb-editor/EditorToolbar';
import { ArticleSidebar } from './kb-editor/ArticleSidebar';
import { ConfigPanel } from './kb-editor/ConfigPanel';
import { NavManager } from './kb-editor/NavManager';
import { EDITOR_THEMES } from './kb-editor/editorTheme';

const API = process.env.REACT_APP_BACKEND_URL;

const KBEditor = () => {
  const { slug: paramSlug } = useParams();
  const navigate = useNavigate();
  const textareaRef = useRef(null);

  const [articles, setArticles] = useState([]);
  const [navGroups, setNavGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(null);
  const [originalSlug, setOriginalSlug] = useState(null);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [isNew, setIsNew] = useState(false);
  const [viewMode, setViewMode] = useState('split');
  const [configOpen, setConfigOpen] = useState(false);
  const [expanded, setExpanded] = useState({});
  const [previewDevice, setPreviewDevice] = useState('desktop');
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [navManagerOpen, setNavManagerOpen] = useState(false);

  // Theme state — persisted to localStorage
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

  // Load article when slug changes
  useEffect(() => {
    if (!paramSlug || paramSlug === 'new') {
      if (paramSlug === 'new') {
        setIsNew(true);
        setOriginalSlug(null);
        setForm({ title: '', slug: '', content_markdown: '', nav_group_key: navGroups[0]?.key || '', nav_group_label: navGroups[0]?.label || '', section_key: navGroups[0]?.sections?.[0]?.key || '', section_label: navGroups[0]?.sections?.[0]?.label || '', published: true, order: articles.length });
      } else if (articles.length > 0 && !form) {
        navigate(`/dashboard/kb-editor/${articles[0].slug}`, { replace: true });
      }
      return;
    }
    const art = articles.find(a => a.slug === paramSlug);
    if (art) {
      setIsNew(false);
      setOriginalSlug(art.slug);
      setForm({ ...art });
    }
  }, [paramSlug, articles, navGroups, navigate]);

  // Save
  const handleSave = useCallback(async () => {
    if (!form || !form.title?.trim()) return;
    setSaving(true);
    try {
      const slug = form.slug?.trim() || slugify(form.title);
      const payload = { ...form, slug };
      delete payload.created_at; delete payload.updated_at; delete payload.source_url;
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
  }, [form, isNew, originalSlug, navigate, fetchAll]);

  // Cmd+S
  useEffect(() => {
    const handler = (e) => { if ((e.metaKey || e.ctrlKey) && e.key === 's') { e.preventDefault(); handleSave(); } };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleSave]);

  // Cmd+B / Cmd+I formatting
  useEffect(() => {
    const handler = (e) => {
      if (!textareaRef.current || document.activeElement !== textareaRef.current) return;
      if (e.metaKey || e.ctrlKey) {
        const ta = textareaRef.current;
        const start = ta.selectionStart, end = ta.selectionEnd;
        const selected = form?.content_markdown?.substring(start, end) || '';
        const before = form?.content_markdown?.substring(0, start) || '';
        const after = form?.content_markdown?.substring(end) || '';
        let prefix, suffix;
        if (e.key === 'b') { prefix = '**'; suffix = '**'; }
        else if (e.key === 'i') { prefix = '*'; suffix = '*'; }
        else return;
        e.preventDefault();
        setForm(f => ({ ...f, content_markdown: `${before}${prefix}${selected || 'text'}${suffix}${after}` }));
        setTimeout(() => { ta.focus(); ta.setSelectionRange(start + prefix.length, start + prefix.length + (selected || 'text').length); }, 0);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [form?.content_markdown]);

  const handleDelete = async (slug) => {
    if (!window.confirm('Delete this article permanently?')) return;
    setDeleting(slug);
    try {
      await fetch(`${API}/api/kb/admin/articles/${slug}`, { method: 'DELETE', credentials: 'include' });
      if (paramSlug === slug) navigate('/dashboard/kb-editor', { replace: true });
      await fetchAll();
    } catch (e) { console.error(e); }
    finally { setDeleting(null); }
  };

  // Image upload
  const uploadImage = useCallback(async (file) => {
    if (!file || !file.type.startsWith('image/')) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API}/api/kb/admin/images`, { method: 'POST', credentials: 'include', body: formData });
      if (!res.ok) throw new Error('Upload failed');
      const { url } = await res.json();
      const altText = file.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ');
      const markdown = `![${altText}](${url})`;
      const ta = textareaRef.current;
      if (ta && form) {
        const pos = ta.selectionStart;
        const before = (form.content_markdown || '').substring(0, pos);
        const after = (form.content_markdown || '').substring(pos);
        const nl = before.length > 0 && !before.endsWith('\n') ? '\n' : '';
        setForm(f => ({ ...f, content_markdown: `${before}${nl}${markdown}\n${after}` }));
        setTimeout(() => { ta.focus(); }, 0);
      } else {
        setForm(f => ({ ...f, content_markdown: (f?.content_markdown || '') + `\n${markdown}\n` }));
      }
    } catch (e) { console.error(e); alert(`Image upload failed: ${e.message}`); }
    finally { setUploading(false); }
  }, [form]);

  const handleDrop = useCallback((e) => { e.preventDefault(); setDragOver(false); const file = e.dataTransfer?.files?.[0]; if (file?.type.startsWith('image/')) uploadImage(file); }, [uploadImage]);
  const handlePaste = useCallback((e) => { const items = e.clipboardData?.items; if (!items) return; for (const item of items) { if (item.type.startsWith('image/')) { e.preventDefault(); uploadImage(item.getAsFile()); return; } } }, [uploadImage]);

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

  const previewWidth = previewDevice === 'mobile' ? 'max-w-[375px]' : previewDevice === 'tablet' ? 'max-w-[768px]' : 'max-w-none';

  if (loading) {
    return <div className={`min-h-screen flex items-center justify-center ${theme.bg}`}><Loader2 className="w-6 h-6 animate-spin text-[#00A1B2]" /></div>;
  }

  // Inline background styles for light theme to override app's CSS variable system
  const bgStyle = isDark ? {} : { backgroundColor: '#ffffff' };
  const panelBgStyle = isDark ? {} : { backgroundColor: '#f9fafb' };

  return (
    <div className={`min-h-screen ${theme.bg} flex flex-col`} style={bgStyle} data-testid="kb-editor-page">
      {/* Header */}
      <header className={`h-14 flex items-center px-4 border-b ${theme.border} ${theme.panelBg} flex-shrink-0 gap-3 z-30`} style={panelBgStyle} data-testid="editor-header">
        <button onClick={() => navigate('/dashboard/settings')} className={`flex items-center gap-2 ${theme.textMuted} ${theme.hoverText} transition-colors`} data-testid="back-to-dashboard">
          <ChevronLeft className="w-4 h-4" /><span className="text-sm">Dashboard</span>
        </button>
        <div className={`w-px h-6 ${theme.divider}`} />
        {form && (
          <input value={form.title || ''} onChange={e => {
            const title = e.target.value;
            setForm(f => ({ ...f, title, slug: isNew || f.slug === slugify(f.title || '') ? slugify(title) : f.slug }));
          }} placeholder="Article title..." className={`flex-1 bg-transparent ${theme.text} text-lg font-medium ${theme.placeholder} outline-none min-w-0`} data-testid="editor-title-input" />
        )}
        <div className="flex items-center gap-2 ml-auto flex-shrink-0">
          <div className={`flex items-center ${isDark ? 'bg-slate-800/60' : 'bg-gray-200/60'} rounded-lg p-0.5`} data-testid="view-mode-toggle">
            {[
              { mode: 'markdown', icon: <Code2 className="w-4 h-4" />, label: 'Code' },
              { mode: 'split', icon: <SplitSquareVertical className="w-4 h-4" />, label: 'Split' },
              { mode: 'preview', icon: <Eye className="w-4 h-4" />, label: 'Preview' },
            ].map(v => (
              <button key={v.mode} onClick={() => setViewMode(v.mode)} title={v.label}
                className={`p-1.5 rounded-md transition-all ${viewMode === v.mode ? 'bg-[#00A1B2] text-white' : `${theme.textMuted} ${theme.hoverText}`}`}
                data-testid={`view-${v.mode}`}>
                {v.icon}
              </button>
            ))}
          </div>
          {viewMode === 'preview' && (
            <div className={`flex items-center ${isDark ? 'bg-slate-800/60' : 'bg-gray-200/60'} rounded-lg p-0.5`}>
              {[
                { d: 'desktop', icon: <Monitor className="w-4 h-4" /> },
                { d: 'tablet', icon: <Tablet className="w-4 h-4" /> },
                { d: 'mobile', icon: <Smartphone className="w-4 h-4" /> },
              ].map(v => (
                <button key={v.d} onClick={() => setPreviewDevice(v.d)}
                  className={`p-1.5 rounded-md transition-all ${previewDevice === v.d ? (isDark ? 'bg-slate-700 text-white' : 'bg-gray-300 text-gray-900') : `${theme.textSecondary} ${theme.hoverText}`}`}>
                  {v.icon}
                </button>
              ))}
            </div>
          )}
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className={`p-2 rounded-lg ${theme.textMuted} ${theme.hoverText} ${theme.hover} transition-colors`}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            data-testid="kb-editor-theme-toggle"
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <button onClick={() => setConfigOpen(!configOpen)} className={`p-2 rounded-lg transition-colors ${configOpen ? 'bg-[#00A1B2] text-white' : `${theme.textMuted} ${theme.hoverText} ${theme.hover}`}`} title="Settings" data-testid="config-toggle">
            <Settings className="w-4 h-4" />
          </button>
          {form?.slug && (
            <a href={`/docs/${form.slug}`} target="_blank" rel="noopener noreferrer" className={`p-2 ${theme.textMuted} ${theme.hoverText} rounded-lg ${theme.hover} transition-colors`} title="Preview live" data-testid="live-preview-link">
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
          <div className={`w-px h-6 ${theme.divider}`} />
          {lastSaved && <span className={`text-xs ${theme.textSecondary} hidden sm:block`}>Saved {lastSaved.toLocaleTimeString()}</span>}
          <button onClick={handleSave} disabled={saving || !form?.title?.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-opacity"
            data-testid="save-btn">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            <span className="hidden sm:inline">Save</span>
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <ArticleSidebar tree={tree} selectedSlug={paramSlug} onSelect={(slug) => navigate(`/dashboard/kb-editor/${slug}`)} onDelete={handleDelete} deleting={deleting} expanded={expanded} setExpanded={setExpanded} onNewArticle={() => navigate('/dashboard/kb-editor/new')} onManageNav={() => setNavManagerOpen(true)} theme={theme} />

        {/* Editor Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {form && viewMode !== 'preview' && (
            <EditorToolbar textareaRef={textareaRef} content={form.content_markdown || ''} setContent={v => setForm(f => ({ ...f, content_markdown: v }))} onUploadImage={uploadImage} theme={theme} />
          )}
          <div className="flex-1 flex overflow-hidden">
            {(viewMode === 'markdown' || viewMode === 'split') && (
              <div className={`${viewMode === 'split' ? `w-1/2 border-r ${theme.border}` : 'w-full'} flex flex-col overflow-hidden relative`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}>
                {dragOver && (
                  <div className="absolute inset-0 z-20 bg-[#00A1B2]/10 border-2 border-dashed border-[#00A1B2] rounded-lg flex items-center justify-center pointer-events-none">
                    <div className="text-[#00A1B2] text-sm font-medium flex items-center gap-2"><ImageIcon className="w-5 h-5" /> Drop image to upload</div>
                  </div>
                )}
                {uploading && (
                  <div className="absolute inset-0 z-20 bg-black/40 flex items-center justify-center">
                    <div className="flex items-center gap-2 text-[#00A1B2] text-sm bg-slate-900 px-4 py-2 rounded-lg border border-slate-700"><Loader2 className="w-4 h-4 animate-spin" /> Uploading...</div>
                  </div>
                )}
                {form ? (
                  <textarea ref={textareaRef} value={form.content_markdown || ''} onChange={e => setForm(f => ({ ...f, content_markdown: e.target.value }))}
                    onPaste={handlePaste}
                    className={`flex-1 w-full px-6 py-6 bg-transparent ${theme.editorText} text-sm font-mono leading-relaxed resize-none outline-none`}
                    style={{ tabSize: 2 }} placeholder="Start writing markdown... (Drag, drop or paste images)" spellCheck={false} data-testid="markdown-editor" />
                ) : (
                  <div className={`flex-1 flex items-center justify-center ${theme.textSecondary}`}>
                    <div className="text-center"><FileText className="w-8 h-8 mx-auto mb-3 opacity-50" /><p>Select an article or create new</p></div>
                  </div>
                )}
              </div>
            )}
            {(viewMode === 'preview' || viewMode === 'split') && (
              <div className={`${viewMode === 'split' ? 'w-1/2' : 'w-full'} overflow-y-auto ${theme.bg}`} data-testid="live-preview">
                <div className={`${previewWidth} mx-auto px-6 py-8`}>
                  {form ? (
                    <div className={`prose ${theme.proseClass} max-w-none`}>
                      <h1 className={`text-3xl font-bold ${theme.text} mb-6`}>{form.title || 'Untitled'}</h1>
                      <DocContent content={form.content_markdown || ''} />
                    </div>
                  ) : (
                    <div className={`${theme.textSecondary} text-center py-20`}>No content to preview</div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {configOpen && form && <ConfigPanel form={form} setForm={setForm} navGroups={navGroups} onClose={() => setConfigOpen(false)} theme={theme} />}
      </div>

      {navManagerOpen && <NavManager navGroups={navGroups} onSave={saveNavigation} onBulkMove={bulkMoveArticles} onClose={() => setNavManagerOpen(false)} theme={theme} />}
    </div>
  );
};

export default KBEditor;
