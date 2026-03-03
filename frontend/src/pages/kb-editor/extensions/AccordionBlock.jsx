/**
 * AccordionBlock — Custom TipTap extension for collapsible accordion sections
 * Container node with expandable/collapsible items, each with a title and rich content area.
 */
import { Node, mergeAttributes } from '@tiptap/core';
import { NodeViewWrapper, NodeViewContent, ReactNodeViewRenderer } from '@tiptap/react';
import { useCallback, useState } from 'react';
import { Plus, Trash2, ChevronRight } from 'lucide-react';
import { useEditorTheme } from '../EditorThemeContext';

// ============= Accordion Block View =============
const AccordionBlockView = ({ node, editor, getPos, deleteNode }) => {
  const themeId = useEditorTheme();
  const isLight = themeId === 'light';

  const addItem = useCallback(() => {
    const pos = getPos();
    if (typeof pos !== 'number') return;
    const endPos = pos + node.nodeSize - 1;
    editor.chain().insertContentAt(endPos, {
      type: 'accordionItem',
      attrs: { title: 'New Section' },
      content: [{ type: 'paragraph' }],
    }).run();
  }, [editor, getPos, node]);

  return (
    <NodeViewWrapper className="accordion-block-wrapper my-6 relative group/accordion" data-testid="accordion-block">
      <button
        onClick={() => deleteNode()}
        className={`absolute -top-3 right-0 p-1.5 rounded-lg opacity-0 group-hover/accordion:opacity-100 transition-all z-10 ${
          isLight ? 'text-gray-400 hover:text-red-500 hover:bg-red-50' : 'text-slate-500 hover:text-red-400 hover:bg-red-400/10'
        }`}
        title="Delete accordion block"
        data-testid="accordion-delete-btn"
      >
        <Trash2 className="w-4 h-4" />
      </button>

      <NodeViewContent className="accordion-items" />

      <button
        onClick={addItem}
        className={`flex items-center gap-2 mt-2 text-sm transition-all ${
          isLight ? 'text-gray-400 hover:text-gray-600' : 'text-slate-500 hover:text-slate-300'
        }`}
        data-testid="add-accordion-item-btn"
      >
        <div className={`w-6 h-6 rounded-md flex items-center justify-center transition-colors ${
          isLight ? 'bg-gray-100 hover:bg-gray-200' : 'bg-white/10 hover:bg-white/15'
        }`}>
          <Plus className="w-3.5 h-3.5" />
        </div>
        <span>Add item</span>
      </button>
    </NodeViewWrapper>
  );
};

// ============= Accordion Item View =============
const AccordionItemView = ({ node, updateAttributes, deleteNode }) => {
  const themeId = useEditorTheme();
  const isLight = themeId === 'light';
  const [expanded, setExpanded] = useState(true);

  return (
    <NodeViewWrapper className="accordion-item-wrapper" data-testid="accordion-item">
      <div className={`rounded-lg border overflow-hidden mb-2 transition-colors ${
        isLight
          ? 'border-gray-200 bg-white'
          : 'border-white/10 bg-white/[0.02]'
      }`}>
        {/* Header */}
        <div
          className={`flex items-center gap-2 px-4 py-3 cursor-pointer select-none transition-colors ${
            isLight
              ? 'hover:bg-gray-50'
              : 'hover:bg-white/[0.04]'
          }`}
          onClick={() => setExpanded(!expanded)}
          data-testid="accordion-item-header"
        >
          <ChevronRight
            className={`w-4 h-4 flex-shrink-0 transition-transform duration-200 ${
              expanded ? 'rotate-90' : ''
            } ${isLight ? 'text-gray-400' : 'text-slate-500'}`}
          />
          <input
            type="text"
            value={node.attrs.title || ''}
            onChange={(e) => updateAttributes({ title: e.target.value })}
            onClick={(e) => e.stopPropagation()}
            className={`bg-transparent text-sm font-medium outline-none flex-1 ${
              isLight ? 'text-gray-800 placeholder:text-gray-300' : 'text-slate-200 placeholder:text-slate-600'
            }`}
            placeholder="Section title..."
            data-testid="accordion-item-title-input"
          />
          <button
            onClick={(e) => { e.stopPropagation(); deleteNode(); }}
            className={`p-1 rounded opacity-0 group-hover/accordion:opacity-100 transition-all flex-shrink-0 ${
              isLight ? 'text-gray-400 hover:text-red-500' : 'text-slate-500 hover:text-red-400'
            }`}
            title="Delete item"
            data-testid="accordion-item-delete-btn"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Content - collapsible */}
        <div
          className={`accordion-content-area transition-all duration-200 overflow-hidden ${
            expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
          }`}
        >
          <div className={`px-4 pb-4 pt-1 border-t ${
            isLight ? 'border-gray-100' : 'border-white/5'
          }`}>
            <NodeViewContent className="accordion-item-content min-h-[2em]" />
          </div>
        </div>
      </div>
    </NodeViewWrapper>
  );
};

// ============= Accordion Block Extension =============
export const AccordionBlockNode = Node.create({
  name: 'accordionBlock',
  group: 'block',
  content: 'accordionItem+',
  defining: true,

  parseHTML() {
    return [{ tag: 'div[data-type="accordion-block"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 'data-type': 'accordion-block' }), 0];
  },

  addNodeView() {
    return ReactNodeViewRenderer(AccordionBlockView);
  },

  addStorage() {
    return {
      markdown: {
        serialize(state, node) {
          const savedDelim = state.delim;
          state.delim = '';
          state.write('<Accordion>\n');
          state.renderContent(node);
          state.write('</Accordion>\n\n');
          state.delim = savedDelim;
        },
      },
    };
  },
});

// ============= Accordion Item Extension =============
export const AccordionItemNode = Node.create({
  name: 'accordionItem',
  content: 'block+',
  defining: true,

  addAttributes() {
    return {
      title: {
        default: 'Section',
        parseHTML: (el) => el.getAttribute('data-title') || 'Section',
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-type="accordion-item"]' }];
  },

  renderHTML({ node, HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, {
      'data-type': 'accordion-item',
      'data-title': node.attrs.title,
    }), 0];
  },

  addNodeView() {
    return ReactNodeViewRenderer(AccordionItemView);
  },

  addStorage() {
    return {
      markdown: {
        serialize(state, node) {
          const title = (node.attrs.title || '').replace(/"/g, '&quot;');
          const savedDelim = state.delim;
          state.delim = '';
          state.write(`<AccordionItem title="${title}">\n`);
          state.renderContent(node);
          state.write('</AccordionItem>\n');
          state.delim = savedDelim;
        },
      },
    };
  },
});
