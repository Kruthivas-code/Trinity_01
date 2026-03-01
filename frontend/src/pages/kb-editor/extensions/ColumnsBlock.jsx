/**
 * ColumnsBlock — Custom TipTap node for column layouts (1, 2, or 3 cols)
 * with visual Card children that are editable inline.
 */
import { Node, mergeAttributes } from '@tiptap/react';
import { NodeViewWrapper, NodeViewContent, ReactNodeViewRenderer } from '@tiptap/react';
import { useState, useCallback } from 'react';
import { Columns, Trash2, GripVertical, MoreVertical, Settings2 } from 'lucide-react';
import { useEditorTheme } from '../EditorThemeContext';

// ============= Columns Block NodeView =============
const ColumnsBlockView = ({ node, updateAttributes, deleteNode, editor, getPos }) => {
  const [showSettings, setShowSettings] = useState(false);
  const themeId = useEditorTheme();
  const isLight = themeId === 'light';
  const cols = node.attrs.cols || 2;

  const setCols = useCallback((newCols) => {
    const currentChildren = node.content.content.length;
    updateAttributes({ cols: newCols });

    // Add cards if needed
    if (newCols > currentChildren) {
      const pos = getPos();
      const endPos = pos + node.nodeSize - 1;
      for (let i = currentChildren; i < newCols; i++) {
        editor.chain().insertContentAt(endPos, {
          type: 'columnCard',
          attrs: { title: `Card ${i + 1}`, description: 'Description', icon: 'zap' },
        }).run();
      }
    }
    setShowSettings(false);
  }, [node, updateAttributes, editor, getPos]);

  return (
    <NodeViewWrapper className="columns-block-wrapper my-6 relative group" data-testid="columns-block" data-cols={cols}>
      {/* Controls Bar */}
      <div className="columns-block-controls absolute -top-8 right-0 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        <div className="relative">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              isLight ? 'bg-white border-gray-200 text-gray-600 hover:text-gray-900 hover:bg-gray-50' : 'bg-slate-800 border-white/10 text-slate-300 hover:text-white hover:bg-slate-700'
            }`}
            data-testid="columns-settings-btn"
          >
            <Settings2 className="w-3.5 h-3.5" /> Edit Columns
          </button>
          {showSettings && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowSettings(false)} />
              <div className={`absolute z-50 top-full mt-1 right-0 border rounded-xl shadow-2xl p-4 w-56 ${isLight ? 'bg-white border-gray-200' : 'bg-[#1e1e1e] border-white/10'}`} data-testid="columns-settings-popup">
                <div className="flex items-center gap-2 mb-3">
                  <Columns className={`w-4 h-4 ${isLight ? 'text-gray-400' : 'text-slate-400'}`} />
                  <span className={`text-sm font-medium ${isLight ? 'text-gray-900' : 'text-white'}`}>Edit Columns Attributes</span>
                </div>
                <div className="mb-3">
                  <label className={`flex items-center gap-2 text-xs mb-1.5 ${isLight ? 'text-gray-500' : 'text-slate-400'}`}>
                    <Columns className="w-3.5 h-3.5" /> Cols
                  </label>
                  <select
                    value={cols}
                    onChange={(e) => setCols(parseInt(e.target.value))}
                    className={`w-full px-3 py-2 border rounded-lg text-sm focus:border-[#00A1B2] focus:outline-none ${isLight ? 'bg-gray-50 border-gray-200 text-gray-900' : 'bg-slate-800 border-slate-700 text-white'}`}
                    data-testid="columns-count-select"
                  >
                    <option value={1}>One</option>
                    <option value={2}>Two</option>
                    <option value={3}>Three</option>
                  </select>
                </div>
                <div className={`flex items-center justify-between pt-2 border-t ${isLight ? 'border-gray-200' : 'border-white/10'}`}>
                  <button
                    onClick={() => { setShowSettings(false); deleteNode(); }}
                    className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-400/10 rounded transition-colors"
                    data-testid="columns-delete-btn"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setShowSettings(false)}
                    className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${isLight ? 'bg-gray-100 hover:bg-gray-200 text-gray-900' : 'bg-slate-700 hover:bg-slate-600 text-white'}`}
                    data-testid="columns-save-btn"
                  >
                    Save Changes
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Columns Grid — use inline styles for reliable grid layout */}
      <NodeViewContent
        as="div"
        style={{
          display: 'grid',
          gap: '1rem',
          gridTemplateColumns: cols === 1 ? '1fr' : cols === 2 ? '1fr 1fr' : '1fr 1fr 1fr',
        }}
        data-testid="columns-grid"
      />
    </NodeViewWrapper>
  );
};

// ============= Column Card NodeView =============
const ColumnCardView = ({ node, updateAttributes, deleteNode }) => {
  const [showSettings, setShowSettings] = useState(false);
  const themeId = useEditorTheme();
  const isLight = themeId === 'light';
  const { title, description, icon, url, imagePath, cta, horizontal } = node.attrs;
  const [editForm, setEditForm] = useState({ title, description, icon, url, imagePath, cta, horizontal });

  const saveEdits = useCallback(() => {
    updateAttributes(editForm);
    setShowSettings(false);
  }, [editForm, updateAttributes]);

  const openSettings = useCallback(() => {
    setEditForm({ title: node.attrs.title, description: node.attrs.description, icon: node.attrs.icon, url: node.attrs.url, imagePath: node.attrs.imagePath, cta: node.attrs.cta, horizontal: node.attrs.horizontal });
    setShowSettings(true);
  }, [node.attrs]);

  // Get lucide icon component dynamically
  const IconComponent = getCardIcon(icon);

  return (
    <NodeViewWrapper className="column-card-wrapper" data-testid="column-card">
      <div className="relative group/card">
        {/* Card Visual */}
        <div
          className={`column-card-visual p-5 rounded-xl border border-white/10 bg-[#1a1a1a] hover:border-white/20 transition-all cursor-pointer ${
            horizontal ? 'flex items-start gap-4' : ''
          }`}
          onClick={openSettings}
          data-testid="card-visual"
        >
          {/* Three-dot menu */}
          <button
            className="absolute top-2 right-2 p-1 rounded text-slate-500 hover:text-white hover:bg-white/10 opacity-0 group-hover/card:opacity-100 transition-all z-10"
            onClick={(e) => { e.stopPropagation(); openSettings(); }}
            data-testid="card-menu-btn"
          >
            <MoreVertical className="w-4 h-4" />
          </button>

          {/* Icon */}
          {IconComponent && (
            <div className={`mb-3 ${horizontal ? 'mb-0 shrink-0' : ''}`}>
              <IconComponent className="w-6 h-6 text-[#00A1B2]" />
            </div>
          )}

          {/* Content */}
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-white mb-1 leading-tight">{title || 'Untitled'}</h4>
            <p className="text-xs text-slate-400 leading-relaxed">{description || 'Add a description...'}</p>
            {cta && (
              <span className="inline-block mt-2 text-xs text-[#00A1B2] font-medium">{cta}</span>
            )}
          </div>
        </div>

        {/* Edit Card Popup */}
        {showSettings && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setShowSettings(false)} />
            <div className="absolute z-50 top-0 right-0 translate-x-[calc(100%+8px)] bg-[#1e1e1e] border border-white/10 rounded-xl shadow-2xl p-4 w-64" data-testid="card-settings-popup">
              <div className="flex items-center gap-2 mb-4">
                <Settings2 className="w-4 h-4 text-slate-400" />
                <span className="text-sm font-medium text-white">Edit Card Attributes</span>
              </div>

              {/* Content Section */}
              <div className="mb-4">
                <h5 className="text-xs font-semibold text-slate-300 mb-2">Content</h5>

                <div className="space-y-2.5">
                  <div>
                    <label className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1">Title</label>
                    <input
                      value={editForm.title || ''}
                      onChange={(e) => setEditForm(f => ({ ...f, title: e.target.value }))}
                      className="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:border-[#00A1B2] focus:outline-none"
                      placeholder="Card title"
                      data-testid="card-edit-title"
                    />
                  </div>
                  <div>
                    <label className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1">Description</label>
                    <textarea
                      value={editForm.description || ''}
                      onChange={(e) => setEditForm(f => ({ ...f, description: e.target.value }))}
                      className="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:border-[#00A1B2] focus:outline-none resize-none"
                      rows={2}
                      placeholder="Card description"
                      data-testid="card-edit-description"
                    />
                  </div>
                  <div>
                    <label className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1">Icon</label>
                    <input
                      value={editForm.icon || ''}
                      onChange={(e) => setEditForm(f => ({ ...f, icon: e.target.value }))}
                      className="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:border-[#00A1B2] focus:outline-none"
                      placeholder="e.g. rocket, code, zap"
                      data-testid="card-edit-icon"
                    />
                  </div>
                  <div>
                    <label className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1">URL</label>
                    <input
                      value={editForm.url || ''}
                      onChange={(e) => setEditForm(f => ({ ...f, url: e.target.value }))}
                      className="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:border-[#00A1B2] focus:outline-none"
                      placeholder="/features/mcp"
                      data-testid="card-edit-url"
                    />
                  </div>
                  <div>
                    <label className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1">Image Path</label>
                    <input
                      value={editForm.imagePath || ''}
                      onChange={(e) => setEditForm(f => ({ ...f, imagePath: e.target.value }))}
                      className="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:border-[#00A1B2] focus:outline-none"
                      placeholder="Enter Image Path"
                      data-testid="card-edit-image"
                    />
                  </div>
                  <div>
                    <label className="flex items-center gap-1.5 text-[11px] text-slate-400 mb-1">Call To Action</label>
                    <input
                      value={editForm.cta || ''}
                      onChange={(e) => setEditForm(f => ({ ...f, cta: e.target.value }))}
                      className="w-full px-2.5 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:border-[#00A1B2] focus:outline-none"
                      placeholder="Enter Call To Action"
                      data-testid="card-edit-cta"
                    />
                  </div>
                </div>
              </div>

              {/* Appearance */}
              <div className="mb-4">
                <h5 className="text-xs font-semibold text-slate-300 mb-2">Appearance</h5>
                <label className="flex items-center gap-2 cursor-pointer">
                  <span className="text-xs text-slate-400">Horizontal</span>
                  <button
                    type="button"
                    onClick={() => setEditForm(f => ({ ...f, horizontal: !f.horizontal }))}
                    className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                      editForm.horizontal ? 'bg-[#00A1B2]' : 'bg-slate-700'
                    }`}
                    data-testid="card-edit-horizontal"
                  >
                    <span className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow transform transition ${editForm.horizontal ? 'translate-x-4' : 'translate-x-0'}`} />
                  </button>
                </label>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between pt-3 border-t border-white/10">
                <button
                  onClick={() => { setShowSettings(false); deleteNode(); }}
                  className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-400/10 rounded transition-colors"
                  data-testid="card-delete-btn"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
                <button
                  onClick={saveEdits}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs rounded-lg transition-colors"
                  data-testid="card-save-btn"
                >
                  Save Changes
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </NodeViewWrapper>
  );
};

// Simple icon mapper for card icons
function getCardIcon(iconName) {
  if (!iconName) return null;
  // Dynamic import is complex — use a simple map of common icons
  const icons = {
    zap: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>,
    code: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>,
    rocket: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"></path><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"></path><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"></path><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"></path></svg>,
    globe: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>,
    lightbulb: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"></path><path d="M9 18h6"></path><path d="M10 22h4"></path></svg>,
    puzzle: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19.439 7.85c-.049.322.059.648.289.878l1.568 1.568c.47.47.706 1.087.706 1.704s-.235 1.233-.706 1.704l-1.611 1.611a.98.98 0 0 1-.837.276c-.47-.07-.802-.48-.968-.925a2.501 2.501 0 1 0-3.214 3.214c.446.166.855.497.925.968a.979.979 0 0 1-.276.837l-1.61 1.61a2.404 2.404 0 0 1-1.705.707 2.402 2.402 0 0 1-1.704-.706l-1.568-1.568a1.026 1.026 0 0 0-.877-.29c-.493.074-.84.504-1.02.968a2.5 2.5 0 1 1-3.237-3.237c.464-.18.894-.527.967-1.02a1.026 1.026 0 0 0-.289-.877l-1.568-1.568A2.402 2.402 0 0 1 1.998 12c0-.617.236-1.234.706-1.704L4.23 8.77c.24-.24.581-.353.917-.303.515.077.877.528 1.073 1.01a2.5 2.5 0 1 0 3.259-3.259c-.482-.196-.933-.558-1.01-1.073-.05-.336.062-.676.303-.917l1.525-1.525A2.402 2.402 0 0 1 12 1.998c.617 0 1.234.236 1.704.706l1.568 1.568c.23.23.556.338.877.29.493-.074.84-.504 1.02-.968a2.5 2.5 0 1 1 3.237 3.237c-.464.18-.894.527-.967 1.02Z"></path></svg>,
    wrench: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>,
    users: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M22 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>,
    star: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>,
    shield: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>,
    database: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>,
    terminal: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>,
    'file-text': (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>,
    'book-open': (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path></svg>,
    layers: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>,
    'credit-card': (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>,
    sparkles: (props) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"></path><path d="M5 3v4"></path><path d="M19 17v4"></path><path d="M3 5h4"></path><path d="M17 19h4"></path></svg>,
  };
  return icons[iconName] || icons['file-text'];
}

// ============= TipTap Node: columnsBlock =============
export const ColumnsBlockNode = Node.create({
  name: 'columnsBlock',
  group: 'block',
  content: 'columnCard+',
  defining: true,
  isolating: true,

  addAttributes() {
    return {
      cols: { default: 2, parseHTML: el => parseInt(el.getAttribute('data-cols')) || 2 },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-type="columns-block"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 'data-type': 'columns-block', 'data-cols': HTMLAttributes.cols }), 0];
  },

  addNodeView() {
    return ReactNodeViewRenderer(ColumnsBlockView);
  },

  addStorage() {
    return { markdown: { serialize: columnsBlockSerializer } };
  },
});

function columnsBlockSerializer(state, node) {
  const cols = node.attrs.cols || 2;
  const cards = [];
  node.content.forEach(child => {
    if (child.type.name === 'columnCard') {
      const a = child.attrs;
      let cardAttrs = `title="${a.title || 'Card'}" icon="${a.icon || 'file-text'}"`;
      if (a.url) cardAttrs += ` url="${a.url}"`;
      if (a.imagePath) cardAttrs += ` imagePath="${a.imagePath}"`;
      if (a.cta) cardAttrs += ` cta="${a.cta}"`;
      if (a.horizontal) cardAttrs += ` horizontal="true"`;
      cards.push(`<Card ${cardAttrs}>\n${a.description || 'Description'}\n</Card>`);
    }
  });
  state.write(`<Columns cols={${cols}}>\n${cards.join('\n')}\n</Columns>\n\n`);
  state.closeBlock(node);
}

// ============= TipTap Node: columnCard =============
export const ColumnCardNode = Node.create({
  name: 'columnCard',
  group: 'block',
  content: '',
  atom: true,
  draggable: true,

  addAttributes() {
    return {
      title: {
        default: 'Card Title',
        parseHTML: el => el.getAttribute('data-title') || 'Card Title',
      },
      description: {
        default: 'Description',
        parseHTML: el => el.getAttribute('data-description') || 'Description',
      },
      icon: {
        default: 'file-text',
        parseHTML: el => el.getAttribute('data-icon') || 'file-text',
      },
      url: {
        default: '',
        parseHTML: el => el.getAttribute('data-url') || '',
      },
      imagePath: {
        default: '',
        parseHTML: el => el.getAttribute('data-image-path') || '',
      },
      cta: {
        default: '',
        parseHTML: el => el.getAttribute('data-cta') || '',
      },
      horizontal: {
        default: false,
        parseHTML: el => el.getAttribute('data-horizontal') === 'true',
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-type="column-card"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, {
      'data-type': 'column-card',
      'data-title': HTMLAttributes.title,
      'data-description': HTMLAttributes.description,
      'data-icon': HTMLAttributes.icon,
      'data-url': HTMLAttributes.url,
      'data-image-path': HTMLAttributes.imagePath,
      'data-cta': HTMLAttributes.cta,
      'data-horizontal': HTMLAttributes.horizontal,
    })];
  },

  addNodeView() {
    return ReactNodeViewRenderer(ColumnCardView);
  },

  addStorage() {
    return { markdown: { serialize() { /* handled by parent columnsBlock */ } } };
  },
});
