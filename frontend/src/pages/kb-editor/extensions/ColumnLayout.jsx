/**
 * ColumnLayout — Editable column grid for the KB Editor.
 * Creates empty column containers where users can add any content
 * using "/" commands and the content toolbar.
 */
import { Node, mergeAttributes } from '@tiptap/core';
import { NodeViewWrapper, NodeViewContent, ReactNodeViewRenderer } from '@tiptap/react';
import { useCallback } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { useEditorTheme } from '../EditorThemeContext';

// ============= Column Layout View =============
const ColumnLayoutView = ({ node, editor, getPos, deleteNode, updateAttributes }) => {
  const themeId = useEditorTheme();
  const isLight = themeId === 'light';
  const cols = node.attrs.cols || 2;

  const addColumn = useCallback(() => {
    const pos = getPos();
    if (typeof pos !== 'number') return;
    const endPos = pos + node.nodeSize - 1;
    editor.chain().insertContentAt(endPos, {
      type: 'columnPane',
      content: [{ type: 'paragraph' }],
    }).run();
    updateAttributes({ cols: node.content.childCount + 1 });
  }, [editor, getPos, node, updateAttributes]);

  return (
    <NodeViewWrapper className="column-layout-wrapper my-6 relative group/cols" data-testid="column-layout" data-cols={cols}>
      <button
        onClick={() => deleteNode()}
        className={`absolute -top-3 right-0 p-1.5 rounded-lg opacity-0 group-hover/cols:opacity-100 transition-all z-10 ${
          isLight ? 'text-gray-400 hover:text-red-500 hover:bg-red-50' : 'text-slate-500 hover:text-red-400 hover:bg-red-400/10'
        }`}
        title="Delete column layout"
        data-testid="column-layout-delete-btn"
      >
        <Trash2 className="w-4 h-4" />
      </button>

      <NodeViewContent
        className={`column-layout-grid cols-${cols}`}
      />

      <button
        onClick={addColumn}
        className={`flex items-center gap-2 mt-2 transition-all opacity-0 group-hover/cols:opacity-100 ${
          isLight ? 'text-gray-400 hover:text-gray-600' : 'text-slate-500 hover:text-slate-300'
        }`}
        data-testid="add-column-btn"
      >
        <div className={`w-6 h-6 rounded-full flex items-center justify-center transition-colors ${
          isLight ? 'bg-gray-100 hover:bg-gray-200' : 'bg-white/10 hover:bg-white/15'
        }`}>
          <Plus className="w-3 h-3" />
        </div>
        <span className="text-[10px] font-mono">add column</span>
      </button>
    </NodeViewWrapper>
  );
};

// ============= Column Pane View =============
const ColumnPaneView = ({ deleteNode }) => {
  const themeId = useEditorTheme();
  const isLight = themeId === 'light';

  return (
    <NodeViewWrapper className="column-pane-wrapper relative group/pane" data-testid="column-pane">
      <button
        onClick={() => deleteNode()}
        className={`absolute -top-2 -right-2 p-1 rounded-full opacity-0 group-hover/pane:opacity-100 transition-all z-10 ${
          isLight
            ? 'bg-white text-gray-400 hover:text-red-500 shadow-sm border border-gray-200'
            : 'bg-[#1a1a1a] text-slate-500 hover:text-red-400 shadow-sm border border-white/10'
        }`}
        title="Delete column"
        data-testid="column-pane-delete-btn"
      >
        <Trash2 className="w-3 h-3" />
      </button>

      <div className={`rounded-lg border p-4 min-h-[80px] transition-colors ${
        isLight
          ? 'border-gray-200 bg-gray-50/50 hover:border-gray-300'
          : 'border-white/10 bg-white/[0.02] hover:border-white/20'
      }`}>
        <NodeViewContent className="column-pane-content" />
      </div>
    </NodeViewWrapper>
  );
};

// ============= Column Layout Extension =============
export const ColumnLayoutNode = Node.create({
  name: 'columnLayout',
  group: 'block',
  content: 'columnPane+',
  defining: true,

  addAttributes() {
    return {
      cols: {
        default: 2,
        parseHTML: (el) => parseInt(el.getAttribute('data-cols')) || 2,
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-type="column-layout"]' }];
  },

  renderHTML({ node, HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, {
      'data-type': 'column-layout',
      'data-cols': node.attrs.cols,
    }), 0];
  },

  addNodeView() {
    return ReactNodeViewRenderer(ColumnLayoutView);
  },

  addStorage() {
    return {
      markdown: {
        serialize(state, node) {
          const savedDelim = state.delim;
          state.delim = '';
          state.write(`<ColumnLayout cols={${node.attrs.cols || 2}}>\n`);
          state.renderContent(node);
          state.write('</ColumnLayout>\n\n');
          state.delim = savedDelim;
        },
      },
    };
  },
});

// ============= Column Pane Extension =============
export const ColumnPaneNode = Node.create({
  name: 'columnPane',
  content: 'block+',
  defining: true,

  parseHTML() {
    return [{ tag: 'div[data-type="column-pane"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 'data-type': 'column-pane' }), 0];
  },

  addNodeView() {
    return ReactNodeViewRenderer(ColumnPaneView);
  },

  addStorage() {
    return {
      markdown: {
        serialize(state, node) {
          const savedDelim = state.delim;
          state.delim = '';
          state.write('<Col>\n');
          state.renderContent(node);
          state.write('</Col>\n');
          state.delim = savedDelim;
        },
      },
    };
  },
});
