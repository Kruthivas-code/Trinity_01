/**
 * CategorySettingsSlider — Settings panel for categories and subcategories.
 * Slides out from behind the left sidebar (same pattern as PageSettingsSlider).
 * Fields: Title (rename), Public toggle, Delete with confirmation.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { X, Trash2, Type, ToggleLeft, FolderOpen, Layers } from 'lucide-react';

const DeleteConfirmation = ({ name, type, onConfirm, onCancel, isDark }) => (
  <div className="fixed inset-0 z-[60] flex items-center justify-center" data-testid="category-delete-confirmation">
    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onCancel} />
    <div className={`relative z-10 w-full max-w-sm mx-4 rounded-xl border p-6 shadow-2xl ${isDark ? 'bg-[#1a1a1a] border-slate-700' : 'bg-white border-gray-200'}`}>
      <h3 className={`text-base font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
        Delete {type}?
      </h3>
      <p className={`text-sm mb-5 ${isDark ? 'text-slate-400' : 'text-gray-500'}`}>
        Are you sure you want to delete <strong className={isDark ? 'text-white' : 'text-gray-900'}>"{name}"</strong>? Pages inside will become unassigned. This cannot be undone.
      </p>
      <div className="flex items-center gap-3 justify-end">
        <button onClick={onCancel}
          className={`px-4 py-2 text-sm rounded-lg transition-colors ${isDark ? 'text-slate-400 hover:text-white hover:bg-slate-800' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'}`}
          data-testid="category-delete-cancel-btn">
          Cancel
        </button>
        <button onClick={onConfirm}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
          data-testid="category-delete-confirm-btn">
          Delete
        </button>
      </div>
    </div>
  </div>
);

export const CategorySettingsSlider = ({ item, type, onSave, onDelete, onClose, isDark }) => {
  // item = { key, label, published?, ... } for either a group or section
  // type = 'category' | 'subcategory'
  const [label, setLabel] = useState(item.label || '');
  const [published, setPublished] = useState(item.published !== false); // default true
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [visible, setVisible] = useState(false);
  const sliderRef = useRef(null);

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true));
  }, []);

  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') handleClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleClose = useCallback(() => {
    // Auto-save on close
    onSave({ ...item, label: label.trim() || item.label, published });
    setVisible(false);
    setTimeout(onClose, 200);
  }, [onSave, onClose, item, label, published]);

  const handleDelete = () => {
    setShowDeleteConfirm(false);
    onDelete(item, type);
    onClose();
  };

  const isCategory = type === 'category';
  const Icon = isCategory ? Layers : FolderOpen;

  const inputClass = `w-full px-3 py-2.5 rounded-lg text-sm border transition-colors focus:outline-none ${
    isDark
      ? 'bg-slate-800/80 border-slate-700 text-white placeholder:text-slate-600 focus:border-[#00A1B2]'
      : 'bg-white border-gray-300 text-gray-900 placeholder:text-gray-400 focus:border-[#00A1B2]'
  }`;
  const labelClass = `flex items-center gap-2 text-xs font-medium mb-1.5 ${isDark ? 'text-slate-400' : 'text-gray-500'}`;

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed z-10 transition-opacity duration-200 ${visible ? 'opacity-100' : 'opacity-0'}`}
        style={{ top: '56px', left: '656px', right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.25)' }}
        onClick={handleClose}
        data-testid="category-settings-backdrop"
      />

      {/* Slider Panel */}
      <div
        ref={sliderRef}
        className={`fixed z-20 flex flex-col border-r shadow-xl transition-transform duration-200 ease-out ${
          isDark ? 'bg-[#111111] border-slate-800' : 'bg-white border-gray-200'
        } ${visible ? 'translate-x-0' : '-translate-x-full'}`}
        style={{ top: '56px', left: '256px', bottom: 0, minWidth: '400px', width: '400px', maxWidth: 'calc(100vw - 256px)' }}
        data-testid="category-settings-slider"
      >
        {/* Header */}
        <div className={`flex items-center justify-between px-5 py-4 border-b flex-shrink-0 ${isDark ? 'border-slate-800' : 'border-gray-200'}`}>
          <div className="flex items-center gap-2">
            <Icon className={`w-4 h-4 ${isDark ? 'text-[#00A1B2]/70' : 'text-[#00A1B2]'}`} />
            <h3 className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {isCategory ? 'Category' : 'Subcategory'} Settings
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className={`p-1.5 rounded-lg transition-colors ${isDark ? 'text-slate-500 hover:text-red-400 hover:bg-red-500/10' : 'text-gray-400 hover:text-red-500 hover:bg-red-50'}`}
              title={`Delete ${type}`}
              data-testid="category-delete-btn"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              onClick={handleClose}
              className={`p-1.5 rounded-lg transition-colors ${isDark ? 'text-slate-500 hover:text-white hover:bg-slate-800' : 'text-gray-400 hover:text-gray-900 hover:bg-gray-100'}`}
              data-testid="category-close-btn"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
          {/* Title */}
          <div>
            <label className={labelClass}>
              <Type className="w-3.5 h-3.5" /> Title
            </label>
            <input
              value={label}
              onChange={e => setLabel(e.target.value)}
              placeholder={`${isCategory ? 'Category' : 'Subcategory'} title`}
              className={inputClass}
              data-testid="category-title-input"
            />
            <p className={`text-xs mt-1.5 ${isDark ? 'text-slate-600' : 'text-gray-400'}`}>
              This name appears in the sidebar navigation.
            </p>
          </div>

          {/* Public Toggle */}
          <div className={`border-t pt-5 ${isDark ? 'border-slate-800' : 'border-gray-200'}`}>
            <label className={labelClass}>
              <ToggleLeft className="w-3.5 h-3.5" /> Visibility
            </label>
            <div className="flex items-center justify-between mt-1">
              <div>
                <p className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {published ? 'Public' : 'Hidden'}
                </p>
                <p className={`text-xs mt-0.5 ${isDark ? 'text-slate-500' : 'text-gray-400'}`}>
                  {published
                    ? `This ${type} and its pages are visible in the docs`
                    : `This ${type} is hidden from the public docs`}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setPublished(p => !p)}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  published ? 'bg-[#00A1B2]' : isDark ? 'bg-slate-700' : 'bg-gray-300'
                }`}
                role="switch"
                aria-checked={published}
                data-testid="category-publish-toggle"
              >
                <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${published ? 'translate-x-5' : 'translate-x-0'}`} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <DeleteConfirmation
          name={label || item.label}
          type={type}
          onConfirm={handleDelete}
          onCancel={() => setShowDeleteConfirm(false)}
          isDark={isDark}
        />
      )}
    </>
  );
};
