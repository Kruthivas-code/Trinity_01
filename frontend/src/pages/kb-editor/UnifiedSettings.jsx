/**
 * UnifiedSettings — Full-page settings panel with sidebar categories
 * Categories: Global, Navigation, Design Configuration, Social Links
 */
import { useState, useEffect, useCallback } from 'react';
import {
  ArrowLeft, Save, Loader2, Globe, Map, Palette, Share2,
  Plus, Trash2, FolderOpen, ArrowRight, FileText, Image as ImageIcon,
  ExternalLink
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const TABS = [
  { key: 'global', label: 'Global', icon: Globe },
  { key: 'navigation', label: 'Navigation', icon: Map },
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

const GlobalSection = ({ theme, isDark }) => {
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
      {GLOBAL_FIELDS.map(({ key, label, placeholder, type }) => (
        <div key={key}>
          <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>{label}</label>
          {type === 'textarea' ? (
            <textarea value={data[key] || ''} onChange={e => setData(p => ({ ...p, [key]: e.target.value }))}
              placeholder={placeholder} rows={3}
              className={`w-full px-3 py-2.5 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors resize-none`}
              style={theme.inputBgStyle} data-testid={`settings-${key}`} />
          ) : (
            <input value={data[key] || ''} onChange={e => setData(p => ({ ...p, [key]: e.target.value }))}
              placeholder={placeholder}
              className={`w-full px-3 py-2.5 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none transition-colors`}
              style={theme.inputBgStyle} data-testid={`settings-${key}`} />
          )}
        </div>
      ))}
      <div className="flex justify-end pt-2">
        <button onClick={handleSave} disabled={saving}
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
const NavigationSection = ({ navGroups, onSaveNav, onBulkMove, theme, isDark }) => {
  const [groups, setGroups] = useState(JSON.parse(JSON.stringify(navGroups)));
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [moveTarget, setMoveTarget] = useState(null);

  const addGroup = () => {
    setGroups([...groups, { key: `group-${Date.now()}`, label: 'New Group', icon: 'file-text', sections: [{ key: 'default', label: 'Default' }] }]);
  };
  const removeGroup = (idx) => { if (window.confirm('Delete this nav group?')) setGroups(groups.filter((_, i) => i !== idx)); };
  const updateGroup = (idx, field, val) => { const g = [...groups]; g[idx] = { ...g[idx], [field]: val }; setGroups(g); };
  const addSection = (gIdx) => { const g = [...groups]; g[gIdx].sections = [...(g[gIdx].sections || []), { key: `section-${Date.now()}`, label: 'New Section' }]; setGroups(g); };
  const removeSection = (gIdx, sIdx) => { const g = [...groups]; g[gIdx].sections = g[gIdx].sections.filter((_, i) => i !== sIdx); setGroups(g); };
  const updateSection = (gIdx, sIdx, field, val) => { const g = [...groups]; g[gIdx].sections[sIdx] = { ...g[gIdx].sections[sIdx], [field]: val }; setGroups(g); };
  const moveGroup = (idx, dir) => { const g = [...groups]; [g[idx], g[idx + dir]] = [g[idx + dir], g[idx]]; setGroups(g); };
  const moveSection = (gIdx, sIdx, dir) => { const g = [...groups]; const s = [...g[gIdx].sections]; [s[sIdx], s[sIdx + dir]] = [s[sIdx + dir], s[sIdx]]; g[gIdx].sections = s; setGroups(g); };

  const getMoveTargets = (gIdx, sIdx) => {
    const targets = [];
    groups.forEach((g, gi) => {
      (g.sections || []).forEach((s, si) => {
        if (gi !== gIdx || si !== sIdx) targets.push({ gIdx: gi, sIdx: si, groupKey: g.key, groupLabel: g.label, sectionKey: s.key, sectionLabel: s.label });
      });
    });
    return targets;
  };

  const handleBulkMove = async (sourceGIdx, sourceSIdx, target) => {
    const srcGroup = navGroups[sourceGIdx] || groups[sourceGIdx];
    const srcSection = (srcGroup?.sections || [])[sourceSIdx] || groups[sourceGIdx]?.sections?.[sourceSIdx];
    if (!srcGroup || !srcSection) return;
    const count = await onBulkMove(srcGroup.key, srcSection.key, target.groupKey, target.groupLabel, target.sectionKey, target.sectionLabel);
    setMoveTarget(null);
    if (count > 0) alert(`Moved ${count} article(s) successfully.`);
  };

  const handleSave = async () => {
    setSaving(true);
    await onSaveNav(groups);
    setSaving(false);
    setSaved(true); setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-4" data-testid="settings-navigation">
      <div className="flex items-center justify-between">
        <p className={`text-xs ${theme.textSecondary}`}>Manage navigation tabs and sections for your documentation site.</p>
        <button onClick={addGroup} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-[#00A1B2] hover:opacity-90 text-white rounded-lg transition-opacity" data-testid="add-group-btn">
          <Plus className="w-3 h-3" /> Add Tab
        </button>
      </div>

      <div className="space-y-3">
        {groups.map((group, gIdx) => (
          <div key={group.key} className={`border ${theme.border} rounded-xl overflow-hidden`} data-testid={`nav-group-${gIdx}`}>
            <div className={`flex items-center gap-2 p-3 ${isDark ? 'bg-white/[0.02]' : 'bg-gray-50/80'}`}>
              <div className="flex flex-col gap-0.5">
                <button disabled={gIdx === 0} onClick={() => moveGroup(gIdx, -1)} className={`${theme.textTertiary} ${theme.hoverText} disabled:opacity-20 text-[10px] leading-none`}>&#9650;</button>
                <button disabled={gIdx === groups.length - 1} onClick={() => moveGroup(gIdx, 1)} className={`${theme.textTertiary} ${theme.hoverText} disabled:opacity-20 text-[10px] leading-none`}>&#9660;</button>
              </div>
              <input value={group.label} onChange={e => updateGroup(gIdx, 'label', e.target.value)} placeholder="Tab name"
                className={`flex-1 bg-transparent text-sm font-medium ${theme.text} ${theme.placeholder} outline-none border-b border-transparent focus:border-[#00A1B2] px-1 py-0.5`} />
              <input value={group.key} onChange={e => updateGroup(gIdx, 'key', e.target.value)} placeholder="key"
                className={`w-36 ${theme.inputBg} text-xs font-mono ${theme.textMuted} rounded px-2 py-1 border ${theme.inputBorder}`} style={theme.inputBgStyle} />
              <button onClick={() => removeGroup(gIdx)} className={`p-1 ${theme.textTertiary} hover:text-red-400 rounded`}><Trash2 className="w-3.5 h-3.5" /></button>
            </div>
            <div className="p-3 space-y-2">
              {(group.sections || []).map((sec, sIdx) => (
                <div key={sec.key} data-testid={`nav-section-${gIdx}-${sIdx}`}>
                  <div className="flex items-center gap-2 pl-4">
                    <div className="flex flex-col gap-0.5">
                      <button disabled={sIdx === 0} onClick={() => moveSection(gIdx, sIdx, -1)} className={`${theme.textTertiary} ${theme.hoverText} disabled:opacity-20 text-[10px] leading-none`}>&#9650;</button>
                      <button disabled={sIdx === (group.sections || []).length - 1} onClick={() => moveSection(gIdx, sIdx, 1)} className={`${theme.textTertiary} ${theme.hoverText} disabled:opacity-20 text-[10px] leading-none`}>&#9660;</button>
                    </div>
                    <FolderOpen className={`w-3.5 h-3.5 ${theme.textTertiary} flex-shrink-0`} />
                    <input value={sec.label} onChange={e => updateSection(gIdx, sIdx, 'label', e.target.value)} placeholder="Section name"
                      className={`flex-1 bg-transparent text-sm ${theme.textMuted} ${theme.placeholder} outline-none border-b border-transparent focus:border-[#00A1B2] px-1 py-0.5`} />
                    <input value={sec.key} onChange={e => updateSection(gIdx, sIdx, 'key', e.target.value)} placeholder="key"
                      className={`w-28 ${theme.inputBg} text-xs font-mono ${theme.textMuted} rounded px-2 py-1 border ${theme.inputBorder}`} style={theme.inputBgStyle} />
                    <button onClick={() => setMoveTarget(moveTarget?.gIdx === gIdx && moveTarget?.sIdx === sIdx ? null : { gIdx, sIdx })}
                      className={`p-1 rounded transition-colors ${moveTarget?.gIdx === gIdx && moveTarget?.sIdx === sIdx ? 'text-[#00A1B2] bg-[#00A1B2]/10' : `${theme.textTertiary} hover:text-[#00A1B2]`}`}
                      title="Move articles to another section" data-testid={`move-section-${gIdx}-${sIdx}`}>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                    <button onClick={() => removeSection(gIdx, sIdx)} className={`p-1 ${theme.textTertiary} hover:text-red-400 rounded`}><Trash2 className="w-3 h-3" /></button>
                  </div>
                  {moveTarget?.gIdx === gIdx && moveTarget?.sIdx === sIdx && (
                    <div className={`ml-10 mt-2 p-2.5 border ${theme.border} rounded-lg ${isDark ? 'bg-white/[0.02]' : 'bg-gray-50'}`} data-testid="move-target-picker">
                      <p className={`text-xs ${theme.textMuted} mb-2`}>Move all articles in <strong className={theme.text}>{sec.label}</strong> to:</p>
                      <div className="space-y-1 max-h-32 overflow-y-auto">
                        {getMoveTargets(gIdx, sIdx).map((t, i) => (
                          <button key={i} onClick={() => handleBulkMove(gIdx, sIdx, t)}
                            className={`w-full text-left px-2.5 py-1.5 text-xs rounded ${theme.hover} ${theme.textMuted} ${theme.hoverText} transition-colors flex items-center gap-2`}
                            data-testid={`move-target-${i}`}>
                            <ArrowRight className="w-3 h-3 text-[#00A1B2]" />
                            <span className={theme.textSecondary}>{t.groupLabel}</span>
                            <span className={theme.textTertiary}>/</span>
                            <span>{t.sectionLabel}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
              <button onClick={() => addSection(gIdx)} className={`flex items-center gap-1.5 ml-4 px-2 py-1 text-xs ${theme.textSecondary} hover:text-[#00A1B2] rounded ${theme.hover} transition-colors`} data-testid={`add-section-${gIdx}`}>
                <Plus className="w-3 h-3" /> Add Section
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-end pt-2">
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-opacity"
          data-testid="save-nav-settings">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saved ? 'Saved!' : 'Save Navigation'}
        </button>
      </div>
    </div>
  );
};

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

const DesignSection = ({ theme, isDark }) => {
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
        <button onClick={handleSave} disabled={saving}
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
export const UnifiedSettings = ({ navGroups, onSaveNav, onBulkMove, onClose, theme, isDark }) => {
  const [activeTab, setActiveTab] = useState('global');

  const renderSection = () => {
    switch (activeTab) {
      case 'global': return <GlobalSection theme={theme} isDark={isDark} />;
      case 'navigation': return <NavigationSection navGroups={navGroups} onSaveNav={onSaveNav} onBulkMove={onBulkMove} theme={theme} isDark={isDark} />;
      case 'design': return <DesignSection theme={theme} isDark={isDark} />;
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
