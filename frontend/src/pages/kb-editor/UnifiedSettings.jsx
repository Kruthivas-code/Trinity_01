/**
 * UnifiedSettings — Full-page settings panel with sidebar categories
 * Categories: Global, Navigation, Design Configuration, Social Links
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  ArrowLeft, Save, Loader2, Globe, Map, Palette, Share2,
  Image as ImageIcon, ExternalLink, Trash2, Upload
} from 'lucide-react';
import { NavManager } from './NavManager';
import { TrashPanel } from './TrashPanel';

const API = process.env.REACT_APP_BACKEND_URL;

const TABS = [
  { key: 'global', label: 'Global', icon: Globe },
  { key: 'navigation', label: 'Navigation', icon: Map },
  { key: 'trash', label: 'Trash', icon: Trash2 },
  { key: 'design', label: 'Design Configuration', icon: Palette },
  { key: 'social', label: 'Social Links', icon: Share2 },
];

// ── Global Settings Section ──────────────────────────────
const GLOBAL_FIELDS = [
  { key: 'meta_title', label: 'Meta Title', placeholder: 'Emergent Docs', type: 'text' },
  { key: 'meta_description', label: 'Meta Description', placeholder: 'Documentation and guides', type: 'textarea' },
  { key: 'favicon_url', label: 'Favicon URL', placeholder: '/favicon.ico', type: 'text' },
  { key: 'og_image_url', label: 'Thumbnail / OG Image URL', placeholder: 'https://example.com/og.png', type: 'text' },
  { key: 'logo_url', label: 'Logo URL', placeholder: 'https://example.com/logo.svg', type: 'text' },
  { key: 'footer_text', label: 'Footer Text', placeholder: 'Built with Emergent', type: 'text' },
  { key: 'custom_domain', label: 'Custom Domain', placeholder: 'docs.yourcompany.com', type: 'text' },
];

// Phase 4 (help-doc-v3 port, Configurations Panel gap): the three branding
// fields that are image URLs. help-doc-v3's ConfigurationsPanel lets you
// upload a logo/favicon/OG-image straight into these fields instead of only
// pasting a URL — Trinity's docs-settings endpoints already HAD these
// fields (meta_title/meta_description/favicon_url/og_image_url/logo_url/
// footer_text/custom_domain, confirmed by reading get_docs_settings), the
// genuine gap was only the upload affordance. Reuses the existing
// POST /api/kb/admin/images endpoint (same one RichTextEditor's toolbar and
// the Image Picker's Upload tab use) rather than adding a second upload path.
const IMAGE_URL_FIELDS = new Set(['favicon_url', 'og_image_url', 'logo_url']);

const OwnerOnlyNote = ({ theme }) => (
  <p className={`text-xs ${theme.textMuted} mb-4 px-3 py-2 rounded-lg border ${theme.border} bg-amber-500/5`} data-testid="owner-only-note">
    Only an owner (admin) can change this. You can look, but Save is disabled.
  </p>
);

const UploadableUrlField = ({ value, onChange, placeholder, theme, disabled, testId }) => {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API}/api/kb/admin/images`, { method: 'POST', credentials: 'include', body: formData });
      if (!res.ok) throw new Error('Upload failed');
      const { url } = await res.json();
      onChange(url);
    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      {value && (
        <img src={value} alt="" className={`w-9 h-9 object-contain rounded border flex-shrink-0 ${theme.inputBg} ${theme.inputBorder}`} style={theme.inputBgStyle} />
      )}
      <input
        value={value || ''}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className={`flex-1 px-3 py-2.5 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors disabled:opacity-50`}
        style={theme.inputBgStyle} data-testid={testId} />
      <button type="button" onClick={() => fileInputRef.current?.click()} disabled={disabled || uploading}
        title="Upload image"
        className={`p-2.5 rounded-lg border transition-colors flex-shrink-0 disabled:opacity-50 ${theme.inputBg} ${theme.inputBorder} ${theme.textMuted} ${theme.hoverText}`}
        data-testid={`${testId}-upload-btn`}>
        {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
      </button>
      <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFile} className="hidden" />
    </div>
  );
};

const GlobalSection = ({ theme, isDark, isOwner }) => {
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/kb/admin/docs-settings`, { credentials: 'include' })
      .then(r => r.json()).then(d => { setData(d || {}); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/kb/admin/docs-settings`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        credentials: 'include', body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error('Save failed');
      setData(await res.json());
      setSaved(true); setTimeout(() => setSaved(false), 2000);
    } catch (e) { alert('Failed to save: ' + e.message); }
    finally { setSaving(false); }
  };

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="w-5 h-5 animate-spin text-[#00A1B2]" /></div>;

  return (
    <div className="space-y-5" data-testid="settings-global">
      {!isOwner && <OwnerOnlyNote theme={theme} />}
      {GLOBAL_FIELDS.map(({ key, label, placeholder, type }) => (
        <div key={key}>
          <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>{label}</label>
          {type === 'textarea' ? (
            <textarea value={data[key] || ''} onChange={e => setData(p => ({ ...p, [key]: e.target.value }))}
              placeholder={placeholder} rows={3}
              className={`w-full px-3 py-2.5 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors resize-none`}
              style={theme.inputBgStyle} data-testid={`settings-${key}`} />
          ) : IMAGE_URL_FIELDS.has(key) ? (
            <UploadableUrlField
              value={data[key]} onChange={v => setData(p => ({ ...p, [key]: v }))}
              placeholder={placeholder} theme={theme} disabled={!isOwner} testId={`settings-${key}`} />
          ) : (
            <input value={data[key] || ''} onChange={e => setData(p => ({ ...p, [key]: e.target.value }))}
              placeholder={placeholder}
              className={`w-full px-3 py-2.5 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors`}
              style={theme.inputBgStyle} data-testid={`settings-${key}`} />
          )}
        </div>
      ))}
      <div className={`flex items-center justify-between gap-4 p-3 border ${theme.inputBorder} rounded-lg`} data-testid="settings-tabs-enabled-row">
        <div>
          <label className={`block text-sm font-medium ${theme.inputText}`}>Horizontal tab switcher</label>
          <p className={`text-xs ${theme.textMuted} mt-0.5`}>Show nav groups as a horizontal tab bar (desktop) / dropdown (mobile) instead of stacking them. Needs 2+ nav groups.</p>
        </div>
        <label className="flex items-center gap-2 cursor-pointer flex-shrink-0">
          <input type="checkbox" checked={data.tabs_enabled === true}
            onChange={e => setData(p => ({ ...p, tabs_enabled: e.target.checked }))}
            className="w-4 h-4 accent-[#00A1B2]" data-testid="settings-tabs-enabled" />
          <span className={`text-xs ${theme.textMuted}`}>{data.tabs_enabled === true ? 'On' : 'Off'}</span>
        </label>
      </div>
      <div className="flex justify-end pt-2">
        <button onClick={handleSave} disabled={saving || !isOwner}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-opacity"
          data-testid="save-global-settings">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saved ? 'Saved!' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
};

// ── Navigation Section ───────────────────────────────────
// The recursive drag-and-drop tree editor lives in NavManager — this section
// just supplies the tree, the article list (for page titles) and the save
// callback used by the whole nav-editing surface of the KB editor.
// Editing the nav tree is owner-only (Phase 1): a non-owner gets a read-only
// view (browse the structure) instead of the interactive editor, since
// NavManager's every action (rename/reorder/move/delete) ends in the same
// owner-gated PUT /api/kb/admin/navigation.
const NavigationSection = ({ navGroups, articles, onSaveNav, theme, isOwner }) => (
  <div data-testid="settings-navigation">
    {!isOwner && <OwnerOnlyNote theme={theme} />}
    {isOwner ? (
      <NavManager groups={navGroups} articles={articles} onSave={onSaveNav} theme={theme} />
    ) : (
      <div className={`text-sm ${theme.textSecondary}`} data-testid="navigation-readonly">
        Navigation editing is owner-only.
      </div>
    )}
  </div>
);

// ── Trash Section ─────────────────────────────────────────
// Phase 2 (help-doc-v3 port): soft-deleted pages. Owner-only server side
// (GET/POST/DELETE /api/kb/admin/trash...), same as Navigation — a non-owner
// gets the same read-only notice used there instead of the panel.
const TrashSection = ({ theme, isOwner, onRefresh }) => (
  <div data-testid="settings-trash">
    {!isOwner && <OwnerOnlyNote theme={theme} />}
    {isOwner ? (
      <TrashPanel theme={theme} onRestored={onRefresh} />
    ) : (
      <div className={`text-sm ${theme.textSecondary}`} data-testid="trash-readonly">
        Trash is owner-only.
      </div>
    )}
  </div>
);

// ── Design Configuration Section ─────────────────────────
const ACCENT_PRESETS = [
  { color: '#00A1B2', label: 'Teal' },
  { color: '#6366F1', label: 'Indigo' },
  { color: '#EC4899', label: 'Pink' },
  { color: '#F59E0B', label: 'Amber' },
  { color: '#10B981', label: 'Emerald' },
  { color: '#8B5CF6', label: 'Violet' },
  { color: '#EF4444', label: 'Red' },
  { color: '#3B82F6', label: 'Blue' },
];

const FONT_OPTIONS = [
  { key: 'system', label: 'System Default' },
  { key: 'inter', label: 'Inter' },
  { key: 'geist', label: 'Geist Sans' },
  { key: 'jetbrains', label: 'JetBrains Mono' },
];

const RADIUS_OPTIONS = [
  { key: 'none', label: 'Sharp (0px)' },
  { key: 'small', label: 'Small (4px)' },
  { key: 'rounded', label: 'Rounded (8px)' },
  { key: 'full', label: 'Pill (16px)' },
];

const CODE_THEMES = [
  { key: 'github-dark', label: 'GitHub Dark' },
  { key: 'github-light', label: 'GitHub Light' },
  { key: 'monokai', label: 'Monokai' },
  { key: 'nord', label: 'Nord' },
];

const DesignSection = ({ theme, isDark, isOwner }) => {
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/kb/admin/design-config`, { credentials: 'include' })
      .then(r => r.json()).then(d => { setConfig(d || {}); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/kb/admin/design-config`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        credentials: 'include', body: JSON.stringify(config),
      });
      if (!res.ok) throw new Error('Save failed');
      setConfig(await res.json());
      setSaved(true); setTimeout(() => setSaved(false), 2000);
    } catch (e) { alert('Failed to save: ' + e.message); }
    finally { setSaving(false); }
  };

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="w-5 h-5 animate-spin text-[#00A1B2]" /></div>;

  return (
    <div className="space-y-6" data-testid="settings-design">
      {!isOwner && <OwnerOnlyNote theme={theme} />}
      {/* Accent Color */}
      <div>
        <label className={`block text-xs font-medium ${theme.textMuted} mb-2`}>Accent Color</label>
        <div className="flex flex-wrap gap-2 mb-2">
          {ACCENT_PRESETS.map(p => (
            <button key={p.color} onClick={() => setConfig(c => ({ ...c, accent_color: p.color }))}
              className={`w-8 h-8 rounded-lg border-2 transition-all ${config.accent_color === p.color ? 'border-white shadow-lg scale-110' : 'border-transparent hover:scale-105'}`}
              style={{ backgroundColor: p.color }} title={p.label} data-testid={`accent-${p.label.toLowerCase()}`} />
          ))}
        </div>
        <div className="flex items-center gap-2">
          <input type="color" value={config.accent_color || '#00A1B2'}
            onChange={e => setConfig(c => ({ ...c, accent_color: e.target.value }))}
            className="w-8 h-8 rounded cursor-pointer border-none" data-testid="accent-color-picker" />
          <input value={config.accent_color || '#00A1B2'}
            onChange={e => setConfig(c => ({ ...c, accent_color: e.target.value }))}
            className={`w-28 px-2 py-1.5 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-xs font-mono ${theme.inputText} focus:border-[#00A1B2] focus:outline-none`}
            style={theme.inputBgStyle} data-testid="accent-color-hex" />
        </div>
      </div>

      {/* Default Theme */}
      <div>
        <label className={`block text-xs font-medium ${theme.textMuted} mb-2`}>Default Theme</label>
        <div className="flex gap-2">
          {['light', 'dark'].map(t => (
            <button key={t} onClick={() => setConfig(c => ({ ...c, default_theme: t }))}
              className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-medium border transition-all capitalize ${
                config.default_theme === t
                  ? 'border-[#00A1B2] bg-[#00A1B2]/10 text-[#00A1B2]'
                  : `${theme.border} ${isDark ? 'bg-white/[0.02] text-slate-400 hover:text-white' : 'bg-gray-50 text-gray-500 hover:text-gray-900'}`
              }`}
              data-testid={`theme-${t}`}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Font Family */}
      <div>
        <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>Font Family</label>
        <select value={config.font_family || 'system'}
          onChange={e => setConfig(c => ({ ...c, font_family: e.target.value }))}
          className={`w-full px-3 py-2.5 ${theme.selectBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} focus:border-[#00A1B2] focus:outline-none`}
          data-testid="font-family-select">
          {FONT_OPTIONS.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
        </select>
      </div>

      {/* Border Radius */}
      <div>
        <label className={`block text-xs font-medium ${theme.textMuted} mb-2`}>Border Radius</label>
        <div className="grid grid-cols-2 gap-2">
          {RADIUS_OPTIONS.map(r => (
            <button key={r.key} onClick={() => setConfig(c => ({ ...c, border_radius: r.key }))}
              className={`px-3 py-2 rounded-lg text-sm border transition-all ${
                config.border_radius === r.key
                  ? 'border-[#00A1B2] bg-[#00A1B2]/10 text-[#00A1B2]'
                  : `${theme.border} ${isDark ? 'bg-white/[0.02] text-slate-400 hover:text-white' : 'bg-gray-50 text-gray-500 hover:text-gray-900'}`
              }`}
              data-testid={`radius-${r.key}`}>
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Code Block Theme */}
      <div>
        <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>Code Block Theme</label>
        <select value={config.code_theme || 'github-dark'}
          onChange={e => setConfig(c => ({ ...c, code_theme: e.target.value }))}
          className={`w-full px-3 py-2.5 ${theme.selectBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} focus:border-[#00A1B2] focus:outline-none`}
          data-testid="code-theme-select">
          {CODE_THEMES.map(t => <option key={t.key} value={t.key}>{t.label}</option>)}
        </select>
      </div>

      {/* Custom CSS */}
      <div>
        <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>Custom CSS</label>
        <textarea value={config.custom_css || ''}
          onChange={e => setConfig(c => ({ ...c, custom_css: e.target.value }))}
          placeholder="/* Add custom CSS overrides here */"
          rows={5}
          className={`w-full px-3 py-2.5 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-xs font-mono ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors resize-y leading-relaxed`}
          style={theme.inputBgStyle} data-testid="custom-css" />
      </div>

      <div className="flex justify-end pt-2">
        <button onClick={handleSave} disabled={saving || !isOwner}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-opacity"
          data-testid="save-design-settings">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saved ? 'Saved!' : 'Save Design'}
        </button>
      </div>
    </div>
  );
};

// ── Social Links Section ─────────────────────────────────
const PLATFORMS = [
  { key: 'twitter', label: 'Twitter / X', placeholder: 'https://x.com/yourhandle' },
  { key: 'linkedin', label: 'LinkedIn', placeholder: 'https://linkedin.com/company/yourcompany' },
  { key: 'discord', label: 'Discord', placeholder: 'https://discord.gg/invite-code' },
  { key: 'youtube', label: 'YouTube', placeholder: 'https://youtube.com/@yourchannel' },
  { key: 'reddit', label: 'Reddit', placeholder: 'https://reddit.com/r/yoursubreddit' },
];

const SocialSection = ({ theme, isDark }) => {
  const [links, setLinks] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/kb/social-links`)
      .then(r => r.json()).then(d => { setLinks(d.links || {}); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/kb/admin/social-links`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        credentials: 'include', body: JSON.stringify({ links }),
      });
      if (!res.ok) throw new Error('Save failed');
      setSaved(true); setTimeout(() => setSaved(false), 2000);
    } catch (e) { alert('Failed to save: ' + e.message); }
    finally { setSaving(false); }
  };

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="w-5 h-5 animate-spin text-[#00A1B2]" /></div>;

  return (
    <div className="space-y-5" data-testid="settings-social">
      <p className={`text-xs ${theme.textSecondary}`}>Configure social links displayed at the bottom of every docs page. Leave blank to hide.</p>
      {PLATFORMS.map(({ key, label, placeholder }) => (
        <div key={key}>
          <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>{label}</label>
          <div className="relative">
            <input value={links[key] || ''} onChange={e => setLinks(p => ({ ...p, [key]: e.target.value }))}
              placeholder={placeholder}
              className={`w-full px-3 py-2.5 pr-8 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors`}
              style={theme.inputBgStyle} data-testid={`social-input-${key}`} />
            {links[key] && (
              <a href={links[key]} target="_blank" rel="noopener noreferrer"
                className={`absolute right-2.5 top-1/2 -translate-y-1/2 ${theme.textSecondary} hover:text-[#00A1B2] transition-colors`}>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        </div>
      ))}
      <div className="flex justify-end pt-2">
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-opacity"
          data-testid="save-social-settings">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saved ? 'Saved!' : 'Save Links'}
        </button>
      </div>
    </div>
  );
};

// ── Main Settings Component ──────────────────────────────
export const UnifiedSettings = ({ navGroups, articles, onSaveNav, onClose, theme, isDark, isOwner, onRefresh }) => {
  const [activeTab, setActiveTab] = useState('global');

  const renderSection = () => {
    switch (activeTab) {
      case 'global': return <GlobalSection theme={theme} isDark={isDark} isOwner={isOwner} />;
      case 'navigation': return <NavigationSection navGroups={navGroups} articles={articles} onSaveNav={onSaveNav} theme={theme} isDark={isDark} isOwner={isOwner} />;
      case 'trash': return <TrashSection theme={theme} isOwner={isOwner} onRefresh={onRefresh} />;
      case 'design': return <DesignSection theme={theme} isDark={isDark} isOwner={isOwner} />;
      // Social links aren't owner-gated server side (open to any signed-in
      // user, like content edits) — no restriction here either.
      case 'social': return <SocialSection theme={theme} isDark={isDark} />;
      default: return null;
    }
  };

  const activeTabData = TABS.find(t => t.key === activeTab);

  return (
    <div className={`fixed inset-0 z-50 flex flex-col ${isDark ? 'bg-[#0a0a0a]' : 'bg-gray-50'}`} data-testid="unified-settings">
      {/* Header */}
      <header className={`h-12 flex items-center px-4 border-b flex-shrink-0 gap-3 ${isDark ? 'bg-[#111] border-slate-800/80' : 'bg-white border-gray-200'}`} data-testid="settings-header">
        <button onClick={onClose}
          className={`flex items-center gap-2 transition-colors ${isDark ? 'text-slate-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}
          data-testid="settings-back-btn">
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm font-medium">Back to Editor</span>
        </button>
        <div className={`w-px h-5 ${isDark ? 'bg-slate-700/40' : 'bg-gray-200'}`} />
        <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>Settings</span>
      </header>

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Settings Sidebar */}
        <nav className={`w-56 flex-shrink-0 border-r overflow-y-auto py-4 px-3 ${isDark ? 'bg-[#0c0c0c] border-slate-800/80' : 'bg-white border-gray-200'}`} data-testid="settings-sidebar">
          <div className="space-y-1">
            {TABS.map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.key;
              return (
                <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                    isActive
                      ? `${isDark ? 'bg-[#00A1B2]/10 text-[#00A1B2]' : 'bg-[#00A1B2]/8 text-[#00A1B2]'} font-medium`
                      : `${isDark ? 'text-slate-400 hover:text-white hover:bg-white/[0.04]' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'}`
                  }`}
                  data-testid={`settings-tab-${tab.key}`}>
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </nav>

        {/* Settings Content */}
        <div className="flex-1 overflow-y-auto" data-testid="settings-content">
          <div className="max-w-2xl mx-auto px-6 py-6">
            <h2 className={`text-lg font-semibold mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{activeTabData?.label}</h2>
            <p className={`text-xs mb-6 ${isDark ? 'text-slate-500' : 'text-gray-400'}`}>
              {activeTab === 'global' && 'Configure site-wide metadata for your documentation site.'}
              {activeTab === 'navigation' && 'Organize the sidebar navigation structure.'}
              {activeTab === 'trash' && 'Restore a deleted page or remove it permanently.'}
              {activeTab === 'design' && 'Customize the visual appearance of your docs.'}
              {activeTab === 'social' && 'Add social media links shown across your docs.'}
            </p>
            {renderSection()}
          </div>
        </div>
      </div>
    </div>
  );
};
