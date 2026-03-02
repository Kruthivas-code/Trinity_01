/**
 * StepsBlock — Custom TipTap extension for step-by-step guides
 * Container node with editable step items, each with a title and rich content area.
 * Supports "/" commands and toolbar formatting within each step's content.
 */
import { Node, mergeAttributes } from '@tiptap/core';
import { NodeViewWrapper, NodeViewContent, ReactNodeViewRenderer } from '@tiptap/react';
import { useCallback } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { useEditorTheme } from '../EditorThemeContext';

// ============= Steps Block View =============
const StepsBlockView = ({ node, editor, getPos, deleteNode }) => {
  const themeId = useEditorTheme();
  const isLight = themeId === 'light';

  const addStep = useCallback(() => {
    const pos = getPos();
    if (typeof pos !== 'number') return;
    const endPos = pos + node.nodeSize - 1;
    editor.chain().insertContentAt(endPos, {
      type: 'stepItem',
      attrs: { title: `Step ${node.content.childCount + 1}` },
      content: [{ type: 'paragraph' }],
    }).run();
  }, [editor, getPos, node]);

  return (
    <NodeViewWrapper className="steps-block-wrapper my-6 relative group/steps" data-testid="steps-block">
      <button
        onClick={() => deleteNode()}
        className={`absolute -top-3 right-0 p-1.5 rounded-lg opacity-0 group-hover/steps:opacity-100 transition-all z-10 ${
          isLight ? 'text-gray-400 hover:text-red-500 hover:bg-red-50' : 'text-slate-500 hover:text-red-400 hover:bg-red-400/10'
        }`}
        title="Delete steps block"
        data-testid="steps-delete-btn"
      >
        <Trash2 className="w-4 h-4" />
      </button>

      <NodeViewContent className="steps-items" />

      <button
        onClick={addStep}
        className={`flex items-center gap-2 mt-1 transition-all ${
          isLight ? 'text-gray-400 hover:text-gray-600' : 'text-slate-500 hover:text-slate-300'
        }`}
        data-testid="add-step-btn"
      >
        <div className={`w-7 h-7 rounded-full flex items-center justify-center transition-colors ${
          isLight ? 'bg-gray-100 hover:bg-gray-200' : 'bg-white/10 hover:bg-white/15'
        }`}>
          <Plus className="w-3.5 h-3.5" />
        </div>
      </button>
    </NodeViewWrapper>
  );
};

// ============= Step Item View =============
const StepItemView = ({ node, updateAttributes, deleteNode, editor, getPos }) => {
  const themeId = useEditorTheme();
  const isLight = themeId === 'light';

  return (
    <NodeViewWrapper className="step-item-wrapper" data-testid="step-item">
      <div className="flex gap-3">
        {/* Left column: numbered circle + connecting line */}
        <div className="flex flex-col items-center flex-shrink-0">
          <div
            className={`step-number-circle w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0 ${
              isLight ? 'bg-gray-200 text-gray-600' : 'bg-white/15 text-slate-300'
            }`}
            data-testid="step-number"
          />
          <div className={`w-0.5 flex-1 mt-2 min-h-[20px] ${
            isLight ? 'bg-gray-200' : 'bg-white/10'
          }`} />
        </div>

        {/* Right column: title + editable content */}
        <div className="flex-1 min-w-0 pb-6">
          <div className="flex items-center gap-2 group/step-title">
            <input
              type="text"
              value={node.attrs.title || ''}
              onChange={(e) => updateAttributes({ title: e.target.value })}
              className={`bg-transparent text-base font-semibold outline-none w-full py-1 ${
                isLight ? 'text-gray-900 placeholder:text-gray-300' : 'text-white placeholder:text-slate-600'
              }`}
              placeholder="Step title..."
              data-testid="step-title-input"
            />
            <button
              onClick={() => deleteNode()}
              className={`p-1 rounded opacity-0 group-hover/step-title:opacity-100 transition-all flex-shrink-0 ${
                isLight ? 'text-gray-400 hover:text-red-500' : 'text-slate-500 hover:text-red-400'
              }`}
              title="Delete step"
              data-testid="step-delete-btn"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className={`mt-2 pl-1 border-l-2 ${
            isLight ? 'border-gray-200' : 'border-white/10'
          }`}>
            <NodeViewContent className="step-content min-h-[2em] py-1 px-3" />
          </div>
        </div>
      </div>
    </NodeViewWrapper>
  );
};

// ============= Steps Block Extension =============
export const StepsBlockNode = Node.create({
  name: 'stepsBlock',
  group: 'block',
  content: 'stepItem+',
  defining: true,

  parseHTML() {
    return [{ tag: 'div[data-type="steps-block"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 'data-type': 'steps-block' }), 0];
  },

  addNodeView() {
    return ReactNodeViewRenderer(StepsBlockView);
  },

  addStorage() {
    return {
      markdown: {
        serialize(state, node) {
          state.write('<Steps>\n');
          state.renderContent(node);
          state.write('</Steps>\n\n');
        },
      },
    };
  },
});

// ============= Step Item Extension =============
export const StepItemNode = Node.create({
  name: 'stepItem',
  content: 'block+',
  defining: true,

  addAttributes() {
    return {
      title: {
        default: 'Step 1',
        parseHTML: (el) => el.getAttribute('data-title') || 'Step',
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-type="step-item"]' }];
  },

  renderHTML({ node, HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, {
      'data-type': 'step-item',
      'data-title': node.attrs.title,
    }), 0];
  },

  addNodeView() {
    return ReactNodeViewRenderer(StepItemView);
  },

  addStorage() {
    return {
      markdown: {
        serialize(state, node) {
          const title = (node.attrs.title || '').replace(/"/g, '&quot;');
          state.write(`<Step title="${title}">\n`);
          state.renderContent(node);
          state.write('</Step>\n');
        },
      },
    };
  },
});
