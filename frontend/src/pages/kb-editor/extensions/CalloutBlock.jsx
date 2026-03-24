/**
 * CalloutBlock — Custom TipTap extension for styled callout blocks.
 * Design matches the docs page Callout component in DocContent.jsx.
 * Supports types: info, check, note, tip, warning, danger
 */
import { Node, mergeAttributes } from '@tiptap/core';
import { NodeViewWrapper, NodeViewContent, ReactNodeViewRenderer } from '@tiptap/react';
import { Trash2, Info, CheckCircle, Lightbulb, AlertTriangle, AlertCircle } from 'lucide-react';

const CALLOUT_STYLES = {
  info: {
    bg: 'bg-blue-500/10', border: 'border-blue-500/30', iconColor: 'text-blue-400',
    Icon: Info, label: 'Info',
  },
  check: {
    bg: 'bg-[#00A1B2]/10', border: 'border-[#00A1B2]/30', iconColor: 'text-[#00A1B2]',
    Icon: CheckCircle, label: 'Check',
  },
  note: {
    bg: 'bg-blue-500/10', border: 'border-blue-500/30', iconColor: 'text-blue-400',
    Icon: Info, label: 'Note',
  },
  tip: {
    bg: 'bg-[#00A1B2]/10', border: 'border-[#00A1B2]/30', iconColor: 'text-[#00A1B2]',
    Icon: Lightbulb, label: 'Tip',
  },
  warning: {
    bg: 'bg-amber-500/10', border: 'border-amber-500/30', iconColor: 'text-amber-400',
    Icon: AlertTriangle, label: 'Warning',
  },
  danger: {
    bg: 'bg-red-500/10', border: 'border-red-500/30', iconColor: 'text-red-400',
    Icon: AlertCircle, label: 'Danger',
  },
};

const CalloutBlockView = ({ node, deleteNode }) => {
  const calloutType = (node.attrs.calloutType || 'info').toLowerCase();
  const style = CALLOUT_STYLES[calloutType] || CALLOUT_STYLES.info;
  const IconComp = style.Icon;
  const displayTitle = node.attrs.title || style.label;

  return (
    <NodeViewWrapper className="callout-block-wrapper relative group/callout" data-testid={`callout-block-${calloutType}`}>
      <div className={`p-4 rounded-lg border ${style.bg} ${style.border} callout-container`}>
        <div className="flex gap-3">
          <div className={`flex-shrink-0 ${style.iconColor}`}>
            <IconComp className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className={`font-semibold ${style.iconColor} mb-1 leading-5`}>{displayTitle}</p>
            <NodeViewContent className="callout-content text-[15px] leading-relaxed" />
          </div>
          <button
            onClick={() => deleteNode()}
            className="flex-shrink-0 p-1 rounded opacity-0 group-hover/callout:opacity-100 transition-all text-gray-400 hover:text-red-400"
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
