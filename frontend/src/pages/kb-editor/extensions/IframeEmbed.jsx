/**
 * IframeEmbed — TipTap node extension for standalone iframe embeds
 * Renders actual iframe (YouTube, etc.) in the editor with hover edit controls
 */
import { useState, useCallback } from 'react';
import { Node, mergeAttributes } from '@tiptap/core';
import { NodeViewWrapper, ReactNodeViewRenderer } from '@tiptap/react';
import { Settings2, Trash2, ExternalLink } from 'lucide-react';
import { useEditorTheme } from '../EditorThemeContext';

const IframeEmbedView = ({ node, updateAttributes, deleteNode }) => {
  const [showEdit, setShowEdit] = useState(false);
  const themeId = useEditorTheme();
  const isLight = themeId === 'light';
  const { src, title } = node.attrs;
  const [editSrc, setEditSrc] = useState(src);
  const [editTitle, setEditTitle] = useState(title);

  const saveEdits = useCallback(() => {
    updateAttributes({ src: editSrc, title: editTitle });
    setShowEdit(false);
  }, [editSrc, editTitle, updateAttributes]);

  const openEdit = useCallback(() => {
    setEditSrc(node.attrs.src);
    setEditTitle(node.attrs.title);
    setShowEdit(true);
  }, [node.attrs]);

  return (
    <NodeViewWrapper className="iframe-embed-wrapper my-4" data-testid="iframe-embed">
      <div className="relative group/iframe">
        <div
          className={`rounded-xl border overflow-hidden transition-all ${
            isLight ? 'border-gray-200 bg-gray-50 hover:border-gray-300' : 'border-white/10 bg-[#1a1a1a] hover:border-white/20'
          }`}
        >
          {src ? (
            <iframe
              src={src}
              title={title || 'Embedded content'}
              className="w-full aspect-video"
              style={{ borderRadius: '12px' }}
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
              data-testid="iframe-embed-player"
            />
          ) : (
            <div className={`flex items-center justify-center aspect-video ${isLight ? 'text-gray-400' : 'text-slate-500'}`}>
              <span className="text-sm">No embed URL set</span>
            </div>
          )}
        </div>

        {/* Hover controls */}
        <div className={`absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover/iframe:opacity-100 transition-all z-10`}>
          {src && (
            <a href={src} target="_blank" rel="noopener noreferrer"
              className={`p-1.5 rounded-lg ${isLight ? 'text-gray-600 bg-white/90 hover:bg-white shadow-sm' : 'text-white bg-black/60 hover:bg-black/80'}`}
              title="Open in new tab" data-testid="iframe-open-link">
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
          <button
            className={`p-1.5 rounded-lg ${isLight ? 'text-gray-600 bg-white/90 hover:bg-white shadow-sm' : 'text-white bg-black/60 hover:bg-black/80'}`}
            onClick={(e) => { e.stopPropagation(); openEdit(); }}
            title="Edit embed"
            data-testid="iframe-embed-edit-btn"
          >
            <Settings2 className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Edit popup */}
        {showEdit && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setShowEdit(false)} />
            <div className={`absolute z-50 top-2 right-2 border rounded-xl shadow-2xl p-4 w-72 ${
              isLight ? 'bg-white border-gray-200' : 'bg-[#1e1e1e] border-white/10'
            }`} data-testid="iframe-embed-popup">
              <div className="flex items-center gap-2 mb-4">
                <Settings2 className={`w-4 h-4 ${isLight ? 'text-gray-400' : 'text-slate-400'}`} />
                <span className={`text-sm font-medium ${isLight ? 'text-gray-900' : 'text-white'}`}>Edit Embed</span>
              </div>
              <div className="space-y-3 mb-4">
                <div>
                  <label className={`block text-[11px] mb-1 ${isLight ? 'text-gray-500' : 'text-slate-400'}`}>Embed URL</label>
                  <input
                    value={editSrc}
                    onChange={(e) => setEditSrc(e.target.value)}
                    className={`w-full px-2.5 py-1.5 border rounded-lg text-xs focus:border-[#00A1B2] focus:outline-none ${
                      isLight ? 'bg-gray-50 border-gray-200 text-gray-900' : 'bg-slate-800 border-slate-700 text-white'
                    }`}
                    placeholder="https://www.youtube.com/embed/..."
                    data-testid="iframe-embed-src-input"
                  />
                </div>
                <div>
                  <label className={`block text-[11px] mb-1 ${isLight ? 'text-gray-500' : 'text-slate-400'}`}>Title</label>
                  <input
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className={`w-full px-2.5 py-1.5 border rounded-lg text-xs focus:border-[#00A1B2] focus:outline-none ${
                      isLight ? 'bg-gray-50 border-gray-200 text-gray-900' : 'bg-slate-800 border-slate-700 text-white'
                    }`}
                    placeholder="Video title"
                    data-testid="iframe-embed-title-input"
                  />
                </div>
              </div>
              <div className={`flex items-center justify-between pt-2 border-t ${isLight ? 'border-gray-200' : 'border-white/10'}`}>
                <button onClick={() => { setShowEdit(false); deleteNode(); }}
                  className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-400/10 rounded transition-colors"
                  data-testid="iframe-embed-delete">
                  <Trash2 className="w-4 h-4" />
                </button>
                <button onClick={saveEdits}
                  className="px-3 py-1.5 bg-[#00A1B2] text-white text-xs rounded-lg hover:opacity-90 transition-opacity"
                  data-testid="iframe-embed-save">
                  Save
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </NodeViewWrapper>
  );
};

export const IframeEmbed = Node.create({
  name: 'iframeEmbed',
  group: 'block',
  atom: true,

  addAttributes() {
    return {
      src: {
        default: '',
        parseHTML: el => el.getAttribute('data-src') || '',
      },
      title: {
        default: '',
        parseHTML: el => el.getAttribute('data-title') || '',
      },
      rawHtml: {
        default: '',
        parseHTML: el => el.getAttribute('data-raw-html') || '',
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-type="iframe-embed"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, {
      'data-type': 'iframe-embed',
      'data-src': HTMLAttributes.src,
      'data-title': HTMLAttributes.title,
      'data-raw-html': HTMLAttributes.rawHtml,
    })];
  },

  addNodeView() {
    return ReactNodeViewRenderer(IframeEmbedView, {
      stopEvent: ({ event }) => {
        // Prevent ProseMirror from handling mouse events on this atom node
        // to avoid "Selection passed to setSelection must point at the current document"
        if (event.type === 'mousedown' || event.type === 'mouseup' || event.type === 'click') {
          return true;
        }
        return false;
      },
    });
  },

  addStorage() {
    return {
      markdown: {
        serialize(state, node) {
          const { src, title, rawHtml } = node.attrs;
          if (rawHtml) {
            state.write(rawHtml + '\n\n');
          } else if (src) {
            state.write(`<iframe src="${src}" title="${title || 'Embedded content'}" frameborder="0" className="w-full aspect-video rounded-xl" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>\n\n`);
          }
          state.closeBlock(node);
        },
      },
    };
  },
});
