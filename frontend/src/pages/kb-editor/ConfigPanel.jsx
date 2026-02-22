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

const IconPicker = ({ value, onChange }) => {
  const [open, setOpen] = useState(false);
  const CurrentIcon = value ? getIcon(value) : FileText;
  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white w-full hover:border-slate-600 transition-colors" data-testid="icon-picker-btn">
        <CurrentIcon className="w-4 h-4 text-[#00A1B2]" />
        <span className="flex-1 text-left truncate">{value || 'No icon'}</span>
        <ChevronDown className="w-3 h-3 text-slate-500" />
      </button>
      {open && (
        <div className="absolute z-50 top-full mt-1 left-0 right-0 bg-slate-900 border border-slate-700 rounded-lg shadow-xl p-2 max-h-48 overflow-y-auto" data-testid="icon-picker-grid">
          <button onClick={() => { onChange(''); setOpen(false); }} className="w-full text-left px-2 py-1 text-xs text-slate-500 hover:text-white hover:bg-slate-800 rounded mb-1">No icon</button>
          <div className="grid grid-cols-8 gap-1">
            {COMMON_ICONS.map(icon => {
              const Icon = getIcon(icon);
              return (
                <button key={icon} onClick={() => { onChange(icon); setOpen(false); }} title={icon}
                  className={`p-1.5 rounded transition-all ${value === icon ? 'bg-[#00A1B2] text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}>
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

export const ConfigPanel = ({ form, setForm, navGroups, onClose }) => (
  <div className="w-72 border-l border-slate-800/80 bg-[#0c0c0c] flex flex-col h-full overflow-y-auto" data-testid="config-panel">
    <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/80">
      <h3 className="text-sm font-semibold text-white">Document Settings</h3>
      <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors"><X className="w-4 h-4" /></button>
    </div>
    <div className="p-4 space-y-4">
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1.5">Slug</label>
        <input value={form.slug || ''} onChange={e => setForm(f => ({ ...f, slug: e.target.value }))}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white font-mono focus:border-[#00A1B2] focus:outline-none transition-colors" data-testid="config-slug" />
      </div>
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1.5">Nav Group</label>
        <select value={form.nav_group_key || ''} onChange={e => {
          const g = navGroups.find(g => g.key === e.target.value);
          setForm(f => ({ ...f, nav_group_key: e.target.value, nav_group_label: g?.label || '', section_key: g?.sections?.[0]?.key || '', section_label: g?.sections?.[0]?.label || '' }));
        }} className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:border-[#00A1B2] focus:outline-none transition-colors" data-testid="config-nav-group">
          {navGroups.map(g => <option key={g.key} value={g.key}>{g.label}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1.5">Section</label>
        <select value={form.section_key || ''} onChange={e => {
          const g = navGroups.find(g => g.key === form.nav_group_key);
          const s = g?.sections?.find(s => s.key === e.target.value);
          setForm(f => ({ ...f, section_key: e.target.value, section_label: s?.label || '' }));
        }} className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:border-[#00A1B2] focus:outline-none transition-colors" data-testid="config-section">
          {(navGroups.find(g => g.key === form.nav_group_key)?.sections || []).map(s => <option key={s.key} value={s.key}>{s.label}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1.5">Icon</label>
        <IconPicker value={form.icon || ''} onChange={v => setForm(f => ({ ...f, icon: v }))} />
      </div>
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-1.5">Order</label>
        <input type="number" value={form.order ?? 0} onChange={e => setForm(f => ({ ...f, order: parseInt(e.target.value) || 0 }))}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:border-[#00A1B2] focus:outline-none transition-colors" data-testid="config-order" />
      </div>
      <div className="flex items-center gap-3 pt-2">
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={form.published !== false} onChange={e => setForm(f => ({ ...f, published: e.target.checked }))}
            className="rounded border-slate-600 bg-slate-800 text-[#00A1B2] focus:ring-[#00A1B2]" data-testid="config-published" />
          <span className="text-sm text-slate-300">Published</span>
        </label>
      </div>
    </div>
  </div>
);
