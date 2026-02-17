/**
 * KBEditor - Full-page Knowledge Base article editor
 * Ported from help.emergent.sh Editor.jsx reference
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronLeft, ChevronDown, ChevronRight, Save, Eye, Code2,
  Loader2, FileText, FolderOpen, Plus, Settings, Trash2, X,
  Monitor, Smartphone, Tablet, Bold, Italic, Heading1, Heading2, Heading3,
  List, ListOrdered, Quote, Code, Link as LinkIcon, Image as ImageIcon,
  Info, AlertTriangle, Lightbulb, CheckCircle, Columns,
  SplitSquareVertical, ExternalLink, Search, MoreHorizontal,
  Youtube
} from 'lucide-react';
import { DocContent } from '../../components/docs/DocContent';
import { getIcon } from '../../components/docs/IconPicker';

const API = process.env.REACT_APP_BACKEND_URL;

// ===== Formatting Toolbar =====
const ToolBtn = ({ onClick, active, disabled, children, title }) => (
  <button onClick={onClick} disabled={disabled} title={title}
    className={`p-1.5 rounded transition-all ${active ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'} ${disabled ? 'opacity-30 cursor-not-allowed' : ''}`}>
    {children}
  </button>
);
const Divider = () => <div className="w-px h-5 bg-slate-700/50 mx-1" />;

const SNIPPET_MAP = {
  callout_note: '<Callout type="NOTE" title="Note">\nYour content here\n</Callout>',
  callout_tip: '<Callout type="TIP" title="Tip">\nYour content here\n</Callout>',
  callout_warning: '<Callout type="WARNING" title="Warning">\nYour content here\n</Callout>',
  steps: '<Steps>\n<Step title="Step 1">\nDescription\n</Step>\n<Step title="Step 2">\nDescription\n</Step>\n</Steps>',
  card_group: '<CardGroup>\n<Card title="Card 1" icon="rocket">\nDescription\n</Card>\n<Card title="Card 2" icon="code">\nDescription\n</Card>\n</CardGroup>',
  tabs: '<Tabs>\n<Tab label="Tab 1">\nContent\n</Tab>\n<Tab label="Tab 2">\nContent\n</Tab>\n</Tabs>',
  accordion: '<Accordion>\n<AccordionItem title="Item 1">\nContent\n</AccordionItem>\n</Accordion>',
  youtube: '<YouTube id="VIDEO_ID" title="Video Title" />',
  columns: '<Columns cols={2}>\n<Card title="Left" icon="zap">\nContent\n</Card>\n<Card title="Right" icon="code">\nContent\n</Card>\n</Columns>',
};

const EditorToolbar = ({ textareaRef, content, setContent }) => {
  const [showInsert, setShowInsert] = useState(false);

  const wrap = (prefix, suffix = prefix) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const selected = content.substring(start, end);
    const before = content.substring(0, start);
    const after = content.substring(end);
    const newText = `${before}${prefix}${selected || 'text'}${suffix}${after}`;
    setContent(newText);
    setTimeout(() => { ta.focus(); ta.setSelectionRange(start + prefix.length, start + prefix.length + (selected || 'text').length); }, 0);
  };

  const insertLine = (prefix) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const pos = ta.selectionStart;
    const before = content.substring(0, pos);
    const after = content.substring(pos);
    const needsNewline = before.length > 0 && !before.endsWith('\n') ? '\n' : '';
    const text = `${before}${needsNewline}${prefix}`;
    setContent(text + after);
    setTimeout(() => { ta.focus(); ta.setSelectionRange(text.length, text.length); }, 0);
  };

  const insertSnippet = (key) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const pos = ta.selectionStart;
    const before = content.substring(0, pos);
    const after = content.substring(pos);
    const needsNewline = before.length > 0 && !before.endsWith('\n') ? '\n\n' : '';
    const text = `${before}${needsNewline}${SNIPPET_MAP[key]}\n`;
    setContent(text + after);
    setShowInsert(false);
    setTimeout(() => { ta.focus(); ta.setSelectionRange(text.length, text.length); }, 0);
  };

  return (
    <div className="flex items-center gap-0.5 px-3 py-2 border-b border-slate-800 bg-slate-900/50 flex-wrap" data-testid="editor-toolbar">
      <ToolBtn onClick={() => insertLine('# ')} title="Heading 1"><Heading1 className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => insertLine('## ')} title="Heading 2"><Heading2 className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => insertLine('### ')} title="Heading 3"><Heading3 className="w-4 h-4" /></ToolBtn>
      <Divider />
      <ToolBtn onClick={() => wrap('**')} title="Bold (Cmd+B)"><Bold className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => wrap('*')} title="Italic (Cmd+I)"><Italic className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => wrap('`')} title="Inline Code"><Code className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => wrap('\n```\n', '\n```\n')} title="Code Block"><Code2 className="w-4 h-4" /></ToolBtn>
      <Divider />
      <ToolBtn onClick={() => insertLine('- ')} title="Bullet List"><List className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => insertLine('1. ')} title="Numbered List"><ListOrdered className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => insertLine('> ')} title="Blockquote"><Quote className="w-4 h-4" /></ToolBtn>
      <Divider />
      <ToolBtn onClick={() => wrap('[', '](url)')} title="Link"><LinkIcon className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => insertLine('![Alt text](image-url)')} title="Image"><ImageIcon className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => insertLine('---\n')} title="Horizontal Rule"><MoreHorizontal className="w-4 h-4" /></ToolBtn>
      <Divider />
      <div className="relative">
        <ToolBtn onClick={() => setShowInsert(!showInsert)} title="Insert Component">
          <Plus className="w-4 h-4" />
        </ToolBtn>
        {showInsert && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setShowInsert(false)} />
            <div className="absolute top-full left-0 mt-1 z-50 w-56 bg-slate-900 border border-slate-700 rounded-lg shadow-xl py-1" data-testid="insert-menu">
              {[
                { key: 'callout_note', label: 'Note Callout', icon: <Info className="w-4 h-4 text-blue-400" /> },
                { key: 'callout_tip', label: 'Tip Callout', icon: <Lightbulb className="w-4 h-4 text-emerald-400" /> },
                { key: 'callout_warning', label: 'Warning Callout', icon: <AlertTriangle className="w-4 h-4 text-amber-400" /> },
                { key: 'steps', label: 'Steps', icon: <ListOrdered className="w-4 h-4 text-purple-400" /> },
                { key: 'card_group', label: 'Card Group', icon: <Columns className="w-4 h-4 text-cyan-400" /> },
                { key: 'tabs', label: 'Tabs', icon: <SplitSquareVertical className="w-4 h-4 text-indigo-400" /> },
                { key: 'accordion', label: 'Accordion', icon: <ChevronDown className="w-4 h-4 text-orange-400" /> },
                { key: 'youtube', label: 'YouTube Embed', icon: <Youtube className="w-4 h-4 text-red-400" /> },
                { key: 'columns', label: 'Columns Layout', icon: <Columns className="w-4 h-4 text-teal-400" /> },
              ].map(item => (
                <button key={item.key} onClick={() => insertSnippet(item.key)}
                  className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
                  data-testid={`insert-${item.key}`}>
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// ===== Document Nav Sidebar =====
const NavGroup = ({ group, groupKey, articles, selectedSlug, onSelect, expanded, setExpanded, onDelete, deleting }) => {
  const isExpanded = expanded[groupKey] !== false;

  return (
    <div>
      <button onClick={() => setExpanded(prev => ({ ...prev, [groupKey]: !prev[groupKey] }))}
        className="w-full flex items-center gap-2 px-2 py-1.5 text-slate-400 hover:text-white transition-colors">
        {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        <FolderOpen className="w-3.5 h-3.5 text-slate-500" />
        <span className="text-xs font-medium truncate">{group.group || group.label}</span>
        <span className="text-[10px] text-slate-600 ml-auto">{articles.length}</span>
      </button>
      {isExpanded && (
        <div className="ml-5 space-y-0.5">
          {articles.map(art => {
            const isActive = art.slug === selectedSlug;
            return (
              <div key={art.slug} className={`group flex items-center gap-1 rounded-lg transition-colors ${isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:bg-slate-800/50 hover:text-white'}`}>
                <button onClick={() => onSelect(art.slug)} className="flex-1 flex items-center gap-2 px-2 py-1.5 text-left min-w-0" data-testid={`nav-article-${art.slug}`}>
                  <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                  <span className="text-sm truncate">{art.title}</span>
                </button>
                {!art.published && <span className="text-[9px] px-1 py-0.5 rounded bg-amber-500/20 text-amber-400">draft</span>}
                <button onClick={() => onDelete(art.slug)} disabled={deleting === art.slug}
                  className="p-1 opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 rounded transition-all flex-shrink-0">
                  {deleting === art.slug ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// ===== Config Panel =====
const ConfigPanel = ({ form, setForm, navGroups, onClose }) => (
  <div className="w-72 border-l border-slate-800 bg-[#0f0f0f] flex flex-col h-full overflow-y-auto" data-testid="config-panel">
    <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
      <h3 className="text-sm font-semibold text-white">Document Settings</h3>
      <button onClick={onClose} className="text-slate-400 hover:text-white"><X className="w-4 h-4" /></button>
    </div>
    <div className="p-4 space-y-4">
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1.5">Slug</label>
        <input value={form.slug || ''} onChange={e => setForm(f => ({ ...f, slug: e.target.value }))}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white font-mono" data-testid="config-slug" />
      </div>
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1.5">Nav Group</label>
        <select value={form.nav_group_key || ''} onChange={e => {
          const g = navGroups.find(g => g.key === e.target.value);
          setForm(f => ({ ...f, nav_group_key: e.target.value, nav_group_label: g?.label || '', section_key: g?.sections?.[0]?.key || '', section_label: g?.sections?.[0]?.label || '' }));
        }} className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white" data-testid="config-nav-group">
          {navGroups.map(g => <option key={g.key} value={g.key}>{g.label}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1.5">Section</label>
        <select value={form.section_key || ''} onChange={e => {
          const g = navGroups.find(g => g.key === form.nav_group_key);
          const s = g?.sections?.find(s => s.key === e.target.value);
          setForm(f => ({ ...f, section_key: e.target.value, section_label: s?.label || '' }));
        }} className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white" data-testid="config-section">
          {(navGroups.find(g => g.key === form.nav_group_key)?.sections || []).map(s => <option key={s.key} value={s.key}>{s.label}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1.5">Order</label>
        <input type="number" value={form.order ?? 0} onChange={e => setForm(f => ({ ...f, order: parseInt(e.target.value) || 0 }))}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white" data-testid="config-order" />
      </div>
      <div className="flex items-center gap-3 pt-2">
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={form.published !== false} onChange={e => setForm(f => ({ ...f, published: e.target.checked }))}
            className="rounded border-slate-600 bg-slate-800 text-emerald-500" data-testid="config-published" />
          <span className="text-sm text-slate-300">Published</span>
        </label>
      </div>
    </div>
  </div>
);

// ===== MAIN EDITOR =====
const KBEditor = () => {
  const { slug: paramSlug } = useParams();
  const navigate = useNavigate();
  const textareaRef = useRef(null);

  // Data
  const [articles, setArticles] = useState([]);
  const [navGroups, setNavGroups] = useState([]);
  const [loading, setLoading] = useState(true);

  // Editor state
  const [form, setForm] = useState(null);
  const [originalSlug, setOriginalSlug] = useState(null);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [isNew, setIsNew] = useState(false);

  // UI state
  const [viewMode, setViewMode] = useState('split'); // 'markdown' | 'split' | 'preview'
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [configOpen, setConfigOpen] = useState(false);
  const [expanded, setExpanded] = useState({});
  const [previewDevice, setPreviewDevice] = useState('desktop');

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
  }, [paramSlug, articles, navGroups, navigate, form]);

  // Save handler
  const handleSave = useCallback(async () => {
    if (!form || !form.title?.trim()) return;
    setSaving(true);
    try {
      const slug = form.slug?.trim() || slugify(form.title);
      const payload = { ...form, slug };
      delete payload.created_at;
      delete payload.updated_at;
      delete payload.source_url;

      const url = isNew ? `${API}/api/kb/admin/articles` : `${API}/api/kb/admin/articles/${originalSlug}`;
      const method = isNew ? 'POST' : 'PUT';

      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify(payload) });
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'Save failed'); }

      setLastSaved(new Date());
      if (isNew) {
        setIsNew(false);
        setOriginalSlug(slug);
        navigate(`/dashboard/kb-editor/${slug}`, { replace: true });
      } else if (slug !== originalSlug) {
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

  // Keyboard shortcuts for formatting
  useEffect(() => {
    const handler = (e) => {
      if (!textareaRef.current || document.activeElement !== textareaRef.current) return;
      if (e.metaKey || e.ctrlKey) {
        const ta = textareaRef.current;
        const start = ta.selectionStart;
        const end = ta.selectionEnd;
        const selected = form?.content_markdown?.substring(start, end) || '';
        const before = form?.content_markdown?.substring(0, start) || '';
        const after = form?.content_markdown?.substring(end) || '';
        let prefix, suffix;
        if (e.key === 'b') { prefix = '**'; suffix = '**'; }
        else if (e.key === 'i') { prefix = '*'; suffix = '*'; }
        else return;
        e.preventDefault();
        const newText = `${before}${prefix}${selected || 'text'}${suffix}${after}`;
        setForm(f => ({ ...f, content_markdown: newText }));
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

  const handleDocSelect = (slug) => navigate(`/dashboard/kb-editor/${slug}`);

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
    return <div className="min-h-screen flex items-center justify-center bg-[#0a0a0a]"><Loader2 className="w-6 h-6 animate-spin text-emerald-500" /></div>;
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col" data-testid="kb-editor-page">
      {/* Top bar */}
      <header className="h-14 flex items-center px-4 border-b border-slate-800 bg-[#0f0f0f] flex-shrink-0 gap-3 z-30" data-testid="editor-header">
        <button onClick={() => navigate('/dashboard/settings')} className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors" data-testid="back-to-dashboard">
          <ChevronLeft className="w-4 h-4" /><span className="text-sm">Dashboard</span>
        </button>
        <div className="w-px h-6 bg-slate-800" />
        {form && (
          <input value={form.title || ''} onChange={e => {
            const title = e.target.value;
            setForm(f => ({ ...f, title, slug: isNew || f.slug === slugify(f.title || '') ? slugify(title) : f.slug }));
          }} placeholder="Article title..." className="flex-1 bg-transparent text-white text-lg font-medium placeholder:text-slate-600 outline-none min-w-0" data-testid="editor-title-input" />
        )}
        <div className="flex items-center gap-2 ml-auto flex-shrink-0">
          {/* View mode toggles */}
          <div className="flex items-center bg-slate-800 rounded-lg p-0.5" data-testid="view-mode-toggle">
            {[
              { mode: 'markdown', icon: <Code2 className="w-4 h-4" />, label: 'Code' },
              { mode: 'split', icon: <SplitSquareVertical className="w-4 h-4" />, label: 'Split' },
              { mode: 'preview', icon: <Eye className="w-4 h-4" />, label: 'Preview' },
            ].map(v => (
              <button key={v.mode} onClick={() => setViewMode(v.mode)} title={v.label}
                className={`p-1.5 rounded-md transition-all ${viewMode === v.mode ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'}`}
                data-testid={`view-${v.mode}`}>
                {v.icon}
              </button>
            ))}
          </div>
          {viewMode === 'preview' && (
            <div className="flex items-center bg-slate-800 rounded-lg p-0.5">
              {[
                { d: 'desktop', icon: <Monitor className="w-4 h-4" /> },
                { d: 'tablet', icon: <Tablet className="w-4 h-4" /> },
                { d: 'mobile', icon: <Smartphone className="w-4 h-4" /> },
              ].map(v => (
                <button key={v.d} onClick={() => setPreviewDevice(v.d)}
                  className={`p-1.5 rounded-md transition-all ${previewDevice === v.d ? 'bg-slate-700 text-white' : 'text-slate-500 hover:text-white'}`}>
                  {v.icon}
                </button>
              ))}
            </div>
          )}
          <button onClick={() => setConfigOpen(!configOpen)} className={`p-2 rounded-lg transition-colors ${configOpen ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`} title="Settings" data-testid="config-toggle">
            <Settings className="w-4 h-4" />
          </button>
          {form?.slug && (
            <a href={`/docs/${form.slug}`} target="_blank" rel="noopener noreferrer" className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors" title="Preview live" data-testid="live-preview-link">
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
          <div className="w-px h-6 bg-slate-800" />
          {lastSaved && <span className="text-xs text-slate-500 hidden sm:block">Saved {lastSaved.toLocaleTimeString()}</span>}
          <button onClick={handleSave} disabled={saving || !form?.title?.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            data-testid="save-btn">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            <span className="hidden sm:inline">Save</span>
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        {sidebarOpen && (
          <aside className="w-64 flex-shrink-0 border-r border-slate-800 bg-[#0f0f0f] flex flex-col overflow-hidden" data-testid="editor-sidebar">
            <div className="px-3 py-3 flex items-center justify-between border-b border-slate-800">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Articles</span>
              <button onClick={() => navigate('/dashboard/kb-editor/new')} className="p-1 text-slate-500 hover:text-emerald-400 rounded transition-colors" title="New article" data-testid="new-article-btn">
                <Plus className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-2 py-2">
              {tree.map(group => (
                <div key={group.key} className="mb-3">
                  <div className="px-2 py-1 text-[10px] font-semibold text-emerald-500/70 uppercase tracking-wider">{group.label}</div>
                  {group.sections.map(sec => (
                    <NavGroup key={sec.key} group={sec} groupKey={`${group.key}-${sec.key}`} articles={sec.articles} selectedSlug={paramSlug} onSelect={handleDocSelect} expanded={expanded} setExpanded={setExpanded} onDelete={handleDelete} deleting={deleting} />
                  ))}
                </div>
              ))}
            </div>
          </aside>
        )}

        {/* Main Editor Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {form && viewMode !== 'preview' && (
            <EditorToolbar textareaRef={textareaRef} content={form.content_markdown || ''} setContent={v => setForm(f => ({ ...f, content_markdown: v }))} />
          )}
          <div className="flex-1 flex overflow-hidden">
            {/* Markdown Editor */}
            {(viewMode === 'markdown' || viewMode === 'split') && (
              <div className={`${viewMode === 'split' ? 'w-1/2 border-r border-slate-800' : 'w-full'} flex flex-col overflow-hidden`}>
                {form ? (
                  <textarea ref={textareaRef} value={form.content_markdown || ''} onChange={e => setForm(f => ({ ...f, content_markdown: e.target.value }))}
                    className="flex-1 w-full px-6 py-6 bg-transparent text-slate-200 text-sm font-mono leading-relaxed resize-none outline-none"
                    style={{ tabSize: 2 }} placeholder="Start writing markdown..." spellCheck={false} data-testid="markdown-editor" />
                ) : (
                  <div className="flex-1 flex items-center justify-center text-slate-500">
                    <div className="text-center"><FileText className="w-8 h-8 mx-auto mb-3 opacity-50" /><p>Select an article or create new</p></div>
                  </div>
                )}
              </div>
            )}
            {/* Live Preview */}
            {(viewMode === 'preview' || viewMode === 'split') && (
              <div className={`${viewMode === 'split' ? 'w-1/2' : 'w-full'} overflow-y-auto bg-[#0a0a0a]`} data-testid="live-preview">
                <div className={`${previewWidth} mx-auto px-6 py-8`}>
                  {form ? (
                    <div className="prose prose-invert max-w-none prose-headings:font-semibold prose-h2:text-2xl prose-h2:mt-10 prose-h2:mb-4 prose-h3:text-xl prose-h3:mt-8 prose-h3:mb-3 prose-p:leading-7 prose-a:text-[#188455] prose-code:text-[#188455] prose-code:bg-[#188455]/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-pre:bg-slate-900 prose-pre:border prose-pre:border-white/10 prose-pre:rounded-xl">
                      <h1 className="text-3xl font-bold text-white mb-6">{form.title || 'Untitled'}</h1>
                      <DocContent content={form.content_markdown || ''} />
                    </div>
                  ) : (
                    <div className="text-slate-500 text-center py-20">No content to preview</div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Config Panel */}
        {configOpen && form && <ConfigPanel form={form} setForm={setForm} navGroups={navGroups} onClose={() => setConfigOpen(false)} />}
      </div>
    </div>
  );
};

export default KBEditor;
