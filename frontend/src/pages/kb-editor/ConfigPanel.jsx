/**
 * ConfigPanel — Document settings sidebar (slug, nav group, section, icon, order, published)
 */
import { useState } from 'react';
import { X, ChevronDown, FileText } from 'lucide-react';
import { getIcon } from '../../components/docs/IconPicker';

const COMMON_ICONS = [
  'file-text', 'book-open', 'code', 'zap', 'rocket', 'wrench', 'globe', 'shield',
  'terminal', 'database', 'layers', 'git-branch', 'package', 'cloud', 'server', 'cpu',
  'smartphone', 'monitor', 'mail', 'message-square', 'users', 'key', 'lock', 'unlock',
  'credit-card', 'dollar-sign', 'bar-chart', 'pie-chart', 'activity', 'trending-up',
  'check-circle', 'alert-triangle', 'info', 'help-circle', 'star', 'heart', 'thumbs-up',
  'play', 'music', 'image', 'video', 'camera', 'mic', 'volume-2', 'headphones',
  'link', 'external-link', 'share-2', 'download', 'upload', 'folder', 'clipboard',
  'calendar', 'clock', 'map-pin', 'navigation', 'compass', 'sun', 'moon', 'settings',
];

const IconPicker = ({ value, onChange, theme }) => {
  const [open, setOpen] = useState(false);
  const CurrentIcon = value ? getIcon(value) : FileText;
  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className={`flex items-center gap-2 px-3 py-2 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} w-full hover:border-[#00A1B2]/50 transition-colors`} data-testid="icon-picker-btn">
        <CurrentIcon className="w-4 h-4 text-[#00A1B2]" />
        <span className="flex-1 text-left truncate">{value || 'No icon'}</span>
        <ChevronDown className={`w-3 h-3 ${theme.textSecondary}`} />
      </button>
      {open && (
        <div className={`absolute z-50 top-full mt-1 left-0 right-0 ${theme.dropdownBg} border ${theme.dropdownBorder} rounded-lg shadow-xl p-2 max-h-48 overflow-y-auto`} data-testid="icon-picker-grid">
          <button onClick={() => { onChange(''); setOpen(false); }} className={`w-full text-left px-2 py-1 text-xs ${theme.textSecondary} ${theme.hoverText} ${theme.hover} rounded mb-1`}>No icon</button>
          <div className="grid grid-cols-8 gap-1">
            {COMMON_ICONS.map(icon => {
              const Icon = getIcon(icon);
              return (
                <button key={icon} onClick={() => { onChange(icon); setOpen(false); }} title={icon}
                  className={`p-1.5 rounded transition-all ${value === icon ? 'bg-[#00A1B2] text-white' : `${theme.textMuted} ${theme.hoverText} ${theme.hover}`}`}>
                  <Icon className="w-4 h-4" />
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export const ConfigPanel = ({ form, setForm, navGroups, onClose, theme }) => (
  <div className={`w-72 border-l ${theme.border} ${theme.panelBg} flex flex-col h-full overflow-y-auto`} data-testid="config-panel">
    <div className={`flex items-center justify-between px-4 py-3 border-b ${theme.border}`}>
      <h3 className={`text-sm font-semibold ${theme.text}`}>Document Settings</h3>
      <button onClick={onClose} className={`${theme.textMuted} ${theme.hoverText} transition-colors`}><X className="w-4 h-4" /></button>
    </div>
    <div className="p-4 space-y-4">
      <div>
        <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>Slug</label>
        <input value={form.slug || ''} onChange={e => setForm(f => ({ ...f, slug: e.target.value }))}
          className={`w-full px-3 py-2 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} font-mono focus:border-[#00A1B2] focus:outline-none transition-colors`} data-testid="config-slug" />
      </div>
      <div>
        <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>Nav Group</label>
        <select value={form.nav_group_key || ''} onChange={e => {
          const g = navGroups.find(g => g.key === e.target.value);
          setForm(f => ({ ...f, nav_group_key: e.target.value, nav_group_label: g?.label || '', section_key: g?.sections?.[0]?.key || '', section_label: g?.sections?.[0]?.label || '' }));
        }} className={`w-full px-3 py-2 ${theme.selectBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} focus:border-[#00A1B2] focus:outline-none transition-colors`} data-testid="config-nav-group">
          {navGroups.map(g => <option key={g.key} value={g.key}>{g.label}</option>)}
        </select>
      </div>
      <div>
        <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>Section</label>
        <select value={form.section_key || ''} onChange={e => {
          const g = navGroups.find(g => g.key === form.nav_group_key);
          const s = g?.sections?.find(s => s.key === e.target.value);
          setForm(f => ({ ...f, section_key: e.target.value, section_label: s?.label || '' }));
        }} className={`w-full px-3 py-2 ${theme.selectBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} focus:border-[#00A1B2] focus:outline-none transition-colors`} data-testid="config-section">
          {(navGroups.find(g => g.key === form.nav_group_key)?.sections || []).map(s => <option key={s.key} value={s.key}>{s.label}</option>)}
        </select>
      </div>
      <div>
        <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>Icon</label>
        <IconPicker value={form.icon || ''} onChange={v => setForm(f => ({ ...f, icon: v }))} theme={theme} />
      </div>
      <div>
        <label className={`block text-xs font-medium ${theme.textMuted} mb-1.5`}>Order</label>
        <input type="number" value={form.order ?? 0} onChange={e => setForm(f => ({ ...f, order: parseInt(e.target.value) || 0 }))}
          className={`w-full px-3 py-2 ${theme.inputBg} border ${theme.inputBorder} rounded-lg text-sm ${theme.inputText} focus:border-[#00A1B2] focus:outline-none transition-colors`} data-testid="config-order" />
      </div>
      <div className="flex items-center gap-3 pt-2">
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={form.published !== false} onChange={e => setForm(f => ({ ...f, published: e.target.checked }))}
            className="rounded border-gray-400 text-[#00A1B2] focus:ring-[#00A1B2]" data-testid="config-published" />
          <span className={`text-sm ${theme.textMuted}`}>Published</span>
        </label>
      </div>
    </div>
  </div>
);
