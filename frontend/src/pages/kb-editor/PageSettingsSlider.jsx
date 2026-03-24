/**
 * PageSettingsSlider — Right slide-in panel for page-level settings
 * Fields: meta title, slug, meta description, sidebar title, keywords, tags, publishing status
 * Includes delete with confirmation overlay
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { X, Trash2, Plus, Globe, Tag, Search, FileText, AlignLeft, Type, ToggleLeft } from 'lucide-react';

const DeleteConfirmation = ({ articleTitle, onConfirm, onCancel, isDark }) => (
  <div className="fixed inset-0 z-[60] flex items-center justify-center" data-testid="delete-confirmation-overlay">
    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onCancel} />
    <div className={`relative z-10 w-full max-w-sm mx-4 rounded-xl border p-6 shadow-2xl ${isDark ? 'bg-[#1a1a1a] border-slate-700' : 'bg-white border-gray-200'}`}>
      <h3 className={`text-base font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
        Delete page?
      </h3>
      <p className={`text-sm mb-5 ${isDark ? 'text-slate-400' : 'text-gray-500'}`}>
        Are you sure you want to delete <strong className={isDark ? 'text-white' : 'text-gray-900'}>"{articleTitle}"</strong>? This action cannot be undone.
      </p>
      <div className="flex items-center gap-3 justify-end">
        <button onClick={onCancel}
          className={`px-4 py-2 text-sm rounded-lg transition-colors ${isDark ? 'text-slate-400 hover:text-white hover:bg-slate-800' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'}`}
          data-testid="delete-cancel-btn">
          Cancel
        </button>
        <button onClick={onConfirm}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
          data-testid="delete-confirm-btn">
          Delete
        </button>
      </div>
    </div>
  </div>
);

export const PageSettingsSlider = ({ form, setForm, onSave, onDelete, onClose, isDark }) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [newKeyword, setNewKeyword] = useState('');
  const [newTag, setNewTag] = useState('');
  const sliderRef = useRef(null);

  // Close on Escape
  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const addKeyword = useCallback(() => {
    const kw = newKeyword.trim();
    if (!kw) return;
    const current = form.keywords || [];
    if (!current.includes(kw)) {
      setForm(f => ({ ...f, keywords: [...(f.keywords || []), kw] }));
    }
    setNewKeyword('');
  }, [newKeyword, form.keywords, setForm]);

  const removeKeyword = (idx) => {
    setForm(f => ({ ...f, keywords: (f.keywords || []).filter((_, i) => i !== idx) }));
  };

  const addTag = useCallback(() => {
    const t = newTag.trim();
    if (!t) return;
    const current = form.tags || [];
    if (!current.includes(t)) {
      setForm(f => ({ ...f, tags: [...(f.tags || []), t] }));
    }
    setNewTag('');
  }, [newTag, form.tags, setForm]);

  const removeTag = (idx) => {
    setForm(f => ({ ...f, tags: (f.tags || []).filter((_, i) => i !== idx) }));
  };

  const handleDelete = () => {
    setShowDeleteConfirm(false);
    onDelete(form.slug);
    onClose();
  };

  const inputClass = `w-full px-3 py-2.5 rounded-lg text-sm border transition-colors focus:outline-none ${
    isDark
      ? 'bg-slate-800/80 border-slate-700 text-white placeholder:text-slate-600 focus:border-[#00A1B2]'
      : 'bg-white border-gray-300 text-gray-900 placeholder:text-gray-400 focus:border-[#00A1B2]'
  }`;

  const labelClass = `flex items-center gap-2 text-xs font-medium mb-1.5 ${isDark ? 'text-slate-400' : 'text-gray-500'}`;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} data-testid="settings-slider-backdrop" />

      {/* Slider Panel */}
      <div
        ref={sliderRef}
        className={`fixed top-0 right-0 z-50 h-full w-[380px] max-w-[90vw] flex flex-col border-l shadow-2xl transition-transform duration-200 ease-out ${
          isDark ? 'bg-[#111111] border-slate-800' : 'bg-white border-gray-200'
        }`}
        style={{ animation: 'slideInRight 0.2s ease-out' }}
        data-testid="page-settings-slider"
      >
        {/* Header */}
        <div className={`flex items-center justify-between px-5 py-4 border-b flex-shrink-0 ${isDark ? 'border-slate-800' : 'border-gray-200'}`}>
          <h3 className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Page Settings
          </h3>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className={`p-1.5 rounded-lg transition-colors ${isDark ? 'text-slate-500 hover:text-red-400 hover:bg-red-500/10' : 'text-gray-400 hover:text-red-500 hover:bg-red-50'}`}
              title="Delete page"
              data-testid="slider-delete-btn"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className={`p-1.5 rounded-lg transition-colors ${isDark ? 'text-slate-500 hover:text-white hover:bg-slate-800' : 'text-gray-400 hover:text-gray-900 hover:bg-gray-100'}`}
              data-testid="slider-close-btn"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Body — scrollable */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
          {/* Meta Title */}
          <div>
            <label className={labelClass}>
              <Type className="w-3.5 h-3.5" /> Title
            </label>
            <input
              value={form.title || ''}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              placeholder="Page title"
              className={inputClass}
              data-testid="slider-title-input"
            />
          </div>

          {/* Slug */}
          <div>
            <label className={labelClass}>
              <Globe className="w-3.5 h-3.5" /> Slug
            </label>
            <input
              value={form.slug || ''}
              onChange={e => setForm(f => ({ ...f, slug: e.target.value }))}
              placeholder="page-slug"
              className={`${inputClass} font-mono`}
              data-testid="slider-slug-input"
            />
          </div>

          {/* Meta Description */}
          <div>
            <label className={labelClass}>
              <AlignLeft className="w-3.5 h-3.5" /> Description
            </label>
            <textarea
              value={form.description || ''}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="Brief meta description"
              rows={3}
              className={`${inputClass} resize-none`}
              data-testid="slider-description-input"
            />
          </div>

          {/* Sidebar Title */}
          <div>
            <label className={labelClass}>
              <FileText className="w-3.5 h-3.5" /> Sidebar title
            </label>
            <input
              value={form.sidebar_title || ''}
              onChange={e => setForm(f => ({ ...f, sidebar_title: e.target.value }))}
              placeholder="Title shown in sidebar"
              className={inputClass}
              data-testid="slider-sidebar-title-input"
            />
          </div>

          {/* Keywords */}
          <div>
            <label className={labelClass}>
              <Search className="w-3.5 h-3.5" /> Keywords
            </label>
            <div className="space-y-2">
              {(form.keywords || []).map((kw, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <span className={`flex-1 px-3 py-2 rounded-lg text-sm ${isDark ? 'bg-slate-800/80 text-white' : 'bg-gray-50 text-gray-900'}`}>
                    {kw}
                  </span>
                  <button onClick={() => removeKeyword(idx)}
                    className={`p-1.5 rounded-lg transition-colors ${isDark ? 'text-slate-500 hover:text-red-400' : 'text-gray-400 hover:text-red-500'}`}
                    data-testid={`remove-keyword-${idx}`}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              <div className="flex items-center gap-2">
                <input
                  value={newKeyword}
                  onChange={e => setNewKeyword(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addKeyword(); } }}
                  placeholder="Enter keyword"
                  className={inputClass}
                  data-testid="slider-keyword-input"
                />
              </div>
              <button onClick={addKeyword}
                className={`flex items-center gap-1.5 text-xs font-medium transition-colors ${isDark ? 'text-[#00A1B2] hover:text-[#00b8cc]' : 'text-[#00A1B2] hover:text-[#008a99]'}`}
                data-testid="add-keyword-btn">
                <Plus className="w-3 h-3" /> Add keyword
              </button>
            </div>
          </div>

          {/* Tags */}
          <div>
            <label className={labelClass}>
              <Tag className="w-3.5 h-3.5" /> Tags
            </label>
            <div className="space-y-2">
              <div className="flex flex-wrap gap-1.5">
                {(form.tags || []).map((tag, idx) => (
                  <span key={idx} className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs ${isDark ? 'bg-slate-800 text-slate-300' : 'bg-gray-100 text-gray-700'}`}>
                    {tag}
                    <button onClick={() => removeTag(idx)} className="hover:text-red-400 transition-colors" data-testid={`remove-tag-${idx}`}>
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <input
                  value={newTag}
                  onChange={e => setNewTag(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag(); } }}
                  placeholder="Enter tag name"
                  className={inputClass}
                  data-testid="slider-tag-input"
                />
              </div>
              <button onClick={addTag}
                className={`flex items-center gap-1.5 text-xs font-medium transition-colors ${isDark ? 'text-[#00A1B2] hover:text-[#00b8cc]' : 'text-[#00A1B2] hover:text-[#008a99]'}`}
                data-testid="add-tag-btn">
                <Plus className="w-3 h-3" /> Add tag
              </button>
            </div>
          </div>

          {/* Publishing Status */}
          <div className={`border-t pt-5 ${isDark ? 'border-slate-800' : 'border-gray-200'}`}>
            <label className={labelClass}>
              <ToggleLeft className="w-3.5 h-3.5" /> Publishing
            </label>
            <div className="flex items-center justify-between mt-1">
              <div>
                <p className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {form.published ? 'Published' : 'Draft'}
                </p>
                <p className={`text-xs mt-0.5 ${isDark ? 'text-slate-500' : 'text-gray-400'}`}>
                  {form.published ? 'Visible to the public' : 'Not visible to the public'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setForm(f => ({ ...f, published: !f.published }))}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  form.published ? 'bg-[#00A1B2]' : isDark ? 'bg-slate-700' : 'bg-gray-300'
                }`}
                role="switch"
                aria-checked={form.published}
                data-testid="slider-publish-toggle"
              >
                <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${form.published ? 'translate-x-5' : 'translate-x-0'}`} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <DeleteConfirmation
          articleTitle={form.title || form.slug || 'this page'}
          onConfirm={handleDelete}
          onCancel={() => setShowDeleteConfirm(false)}
          isDark={isDark}
        />
      )}

      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
      `}</style>
    </>
  );
};
