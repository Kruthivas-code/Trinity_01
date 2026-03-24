/**
 * CalloutBlock — Custom TipTap extension for styled callout blocks
 * Supports 6 types: info, check, note, tip, warning, danger
 * Each renders as a colored block with icon and editable content.
 */
import { Node, mergeAttributes } from '@tiptap/core';
import { NodeViewWrapper, NodeViewContent, ReactNodeViewRenderer } from '@tiptap/react';
import { Trash2, Info, CheckCircle, StickyNote, Lightbulb, AlertTriangle, ShieldAlert } from 'lucide-react';
import { useEditorTheme } from '../EditorThemeContext';

const CALLOUT_STYLES = {
  info: {
    dark: { bg: 'bg-[#1e1e2e]', border: 'border-[#4a4a5a]', iconColor: 'text-slate-300' },
    light: { bg: 'bg-[#f0f0f5]', border: 'border-[#c8c8d4]', iconColor: 'text-slate-500' },
    Icon: Info,
    label: 'Info',
  },
  check: {
    dark: { bg: 'bg-[#0f2918]', border: 'border-[#1a5c30]', iconColor: 'text-emerald-400' },
    light: { bg: 'bg-[#ecfdf5]', border: 'border-[#6ee7b7]', iconColor: 'text-emerald-600' },
    Icon: CheckCircle,
    label: 'Check',
  },
  note: {
    dark: { bg: 'bg-[#0f1a33]', border: 'border-[#1a3a6b]', iconColor: 'text-blue-400' },
    light: { bg: 'bg-[#eff6ff]', border: 'border-[#93c5fd]', iconColor: 'text-blue-600' },
    Icon: StickyNote,
    label: 'Note',
  },
  tip: {
    dark: { bg: 'bg-[#12261a]', border: 'border-[#22543d]', iconColor: 'text-teal-400' },
    light: { bg: 'bg-[#f0fdf4]', border: 'border-[#86efac]', iconColor: 'text-teal-600' },
    Icon: Lightbulb,
    label: 'Tip',
  },
  warning: {
    dark: { bg: 'bg-[#2a1f0a]', border: 'border-[#6b4f1a]', iconColor: 'text-amber-400' },
    light: { bg: 'bg-[#fffbeb]', border: 'border-[#fcd34d]', iconColor: 'text-amber-600' },
    Icon: AlertTriangle,
    label: 'Warning',
  },
  danger: {
    dark: { bg: 'bg-[#2a0f0f]', border: 'border-[#6b1a1a]', iconColor: 'text-red-400' },
    light: { bg: 'bg-[#fef2f2]', border: 'border-[#fca5a5]', iconColor: 'text-red-600' },
    Icon: ShieldAlert,
    label: 'Danger',
  },
};

const CalloutBlockView = ({ node, updateAttributes, deleteNode }) => {
  const themeId = useEditorTheme();
  const isLight = themeId === 'light';
  const calloutType = (node.attrs.calloutType || 'info').toLowerCase();
  const style = CALLOUT_STYLES[calloutType] || CALLOUT_STYLES.info;
  const colors = isLight ? style.light : style.dark;
  const IconComp = style.Icon;

  return (
    <NodeViewWrapper className="callout-block-wrapper my-4 relative group/callout" data-testid={`callout-block-${calloutType}`}>
      <div className={`rounded-lg border-l-4 ${colors.bg} ${colors.border} px-4 py-3`}>
        <div className="flex items-start gap-3">
          <div className={`flex-shrink-0 mt-0.5 ${colors.iconColor}`}>
            <IconComp className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <NodeViewContent className="callout-content min-h-[1.5em]" />
          </div>
          <button
            onClick={() => deleteNode()}
            className={`flex-shrink-0 p-1 rounded opacity-0 group-hover/callout:opacity-100 transition-all ${
              isLight ? 'text-gray-400 hover:text-red-500' : 'text-slate-500 hover:text-red-400'
            }`}
            title="Delete callout"
            data-testid="callout-delete-btn"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </NodeViewWrapper>
  );
};

export const CalloutBlockNode = Node.create({
  name: 'calloutBlock',
  group: 'block',
  content: 'block+',
  defining: true,

  addAttributes() {
    return {
      calloutType: {
        default: 'info',
        parseHTML: (el) => el.getAttribute('data-callout-type') || 'info',
      },
      title: {
        default: '',
        parseHTML: (el) => el.getAttribute('data-callout-title') || '',
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-type="callout-block"]' }];
  },

  renderHTML({ node, HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, {
      'data-type': 'callout-block',
      'data-callout-type': node.attrs.calloutType,
      'data-callout-title': node.attrs.title,
    }), 0];
  },

  addNodeView() {
    return ReactNodeViewRenderer(CalloutBlockView);
  },

  addStorage() {
    return {
      markdown: {
        serialize(state, node) {
          const type = (node.attrs.calloutType || 'info').toUpperCase();
          const title = node.attrs.title || CALLOUT_STYLES[(node.attrs.calloutType || 'info').toLowerCase()]?.label || 'Info';
          const savedDelim = state.delim;
          state.delim = '';
          state.write(`<Callout type="${type}" title="${title.replace(/"/g, '&quot;')}">\n`);
          state.renderContent(node);
          state.write('</Callout>\n\n');
          state.delim = savedDelim;
        },
      },
    };
  },
});

export { CALLOUT_STYLES };
