/**
 * SlashCommand — TipTap extension for "/" command menu
 * Shows a floating dropdown with headings, paragraphs, and insert items
 */
import { Extension } from '@tiptap/react';
import Suggestion from '@tiptap/suggestion';
import { createRoot } from 'react-dom/client';
import { useState, useEffect, useCallback, useRef, forwardRef, useImperativeHandle } from 'react';
import tippy from 'tippy.js';
import {
  Type, Heading1, Heading2, Heading3,
  List, ListOrdered, Quote, Code, Minus,
  Info, Lightbulb, AlertTriangle, CheckCircle, AlertCircle,
  Columns, Youtube, MoreHorizontal, LayoutGrid, TableIcon
} from 'lucide-react';

import { useEditorTheme } from '../EditorThemeContext';

const SLASH_ITEMS = [
  { key: 'paragraph', label: 'Paragraph', description: 'Plain text', icon: Type, group: 'Basic' },
  { key: 'heading1', label: 'Heading 1', description: 'Large heading', icon: Heading1, group: 'Basic' },
  { key: 'heading2', label: 'Heading 2', description: 'Medium heading', icon: Heading2, group: 'Basic' },
  { key: 'heading3', label: 'Heading 3', description: 'Small heading', icon: Heading3, group: 'Basic' },
  { key: 'bullet_list', label: 'Bullet List', description: 'Unordered list', icon: List, group: 'Basic' },
  { key: 'ordered_list', label: 'Ordered List', description: 'Numbered list', icon: ListOrdered, group: 'Basic' },
  { key: 'blockquote', label: 'Blockquote', description: 'Quote block', icon: Quote, group: 'Basic' },
  { key: 'code_block', label: 'Code Block', description: 'Code snippet', icon: Code, group: 'Basic' },
  { key: 'horizontal_rule', label: 'Divider', description: 'Horizontal line', icon: Minus, group: 'Basic' },
  { key: 'columns_1', label: '1 Column', description: 'Single column block', icon: Columns, group: 'Layout' },
  { key: 'columns_2', label: '2 Columns', description: 'Two column layout', icon: Columns, group: 'Layout' },
  { key: 'columns_3', label: '3 Columns', description: 'Three column layout', icon: LayoutGrid, group: 'Layout' },
  { key: 'card_group', label: 'Card Group', description: 'Group of cards', icon: LayoutGrid, group: 'Components' },
  { key: 'callout_info', label: 'Info Callout', description: 'Make writing stand out', icon: Info, group: 'Callouts' },
  { key: 'callout_check', label: 'Check Callout', description: 'Content with a checkmark', icon: CheckCircle, group: 'Callouts' },
  { key: 'callout_note', label: 'Note Callout', description: 'Add a note', icon: Info, group: 'Callouts' },
  { key: 'callout_tip', label: 'Tip Callout', description: 'Suggest a helpful tip', icon: Lightbulb, group: 'Callouts' },
  { key: 'callout_warning', label: 'Warning Callout', description: 'Raise a warning', icon: AlertTriangle, group: 'Callouts' },
  { key: 'callout_danger', label: 'Danger Callout', description: 'Highlight a danger', icon: AlertCircle, group: 'Callouts' },
  { key: 'table', label: 'Table', description: 'Insert a table', icon: TableIcon, group: 'Components' },
  { key: 'steps', label: 'Steps', description: 'Step-by-step guide', icon: CheckCircle, group: 'Components' },
  { key: 'tabs', label: 'Tabs', description: 'Tabbed content', icon: Columns, group: 'Components' },
  { key: 'accordion', label: 'Accordion', description: 'Collapsible section', icon: MoreHorizontal, group: 'Components' },
  { key: 'youtube', label: 'YouTube', description: 'Embed video', icon: Youtube, group: 'Components' },
];

const CommandList = forwardRef(({ items, command }, ref) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const listRef = useRef(null);
  const themeId = useEditorTheme();
  const isLight = themeId === 'light';

  useEffect(() => setSelectedIndex(0), [items]);

  useImperativeHandle(ref, () => ({
    onKeyDown: ({ event }) => {
      if (event.key === 'ArrowUp') {
        setSelectedIndex(i => (i - 1 + items.length) % items.length);
        return true;
      }
      if (event.key === 'ArrowDown') {
        setSelectedIndex(i => (i + 1) % items.length);
        return true;
      }
      if (event.key === 'Enter') {
        if (items[selectedIndex]) command(items[selectedIndex]);
        return true;
      }
      return false;
    },
  }));

  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-index="${selectedIndex}"]`);
    if (el) el.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  if (!items.length) return null;

  // Group items
  const groups = {};
  items.forEach(item => {
    if (!groups[item.group]) groups[item.group] = [];
    groups[item.group].push(item);
  });

  let flatIndex = 0;

  return (
    <div ref={listRef} className={`slash-command-menu border rounded-xl shadow-2xl py-1.5 w-56 max-h-[320px] overflow-y-auto ${
      isLight ? 'bg-white border-gray-200' : 'bg-[#1a1a1a] border-white/10'
    }`} data-testid="slash-command-menu">
      {Object.entries(groups).map(([groupName, groupItems]) => (
        <div key={groupName}>
          <div className={`px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider ${isLight ? 'text-gray-400' : 'text-slate-500'}`}>
            {groupName}
          </div>
          {groupItems.map(item => {
            const idx = flatIndex++;
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                data-index={idx}
                onClick={() => command(item)}
                className={`w-full flex items-center gap-3 px-3 py-2 text-sm transition-colors ${
                  idx === selectedIndex
                    ? (isLight ? 'bg-[#00A1B2]/10 text-gray-900' : 'bg-[#00A1B2]/20 text-white')
                    : (isLight ? 'text-gray-600 hover:bg-gray-50 hover:text-gray-900' : 'text-slate-300 hover:bg-white/5 hover:text-white')
                }`}
                data-testid={`slash-${item.key}`}
              >
                <Icon className={`w-4 h-4 shrink-0 ${isLight ? 'text-gray-400' : 'text-slate-400'}`} />
                <div className="flex-1 text-left">
                  <div className="text-sm">{item.label}</div>
                  <div className={`text-[10px] ${isLight ? 'text-gray-400' : 'text-slate-500'}`}>{item.description}</div>
                </div>
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
});

CommandList.displayName = 'CommandList';

const renderSuggestion = () => {
  let component = null;
  let popup = null;
  let root = null;
  let commandListRef = { current: null };

  return {
    onStart: (props) => {
      const el = document.createElement('div');
      root = createRoot(el);
      
      const updateComponent = (updatedProps) => {
        root.render(
          <CommandList
            ref={commandListRef}
            items={updatedProps.items}
            command={updatedProps.command}
          />
        );
      };

      updateComponent(props);

      popup = tippy('body', {
        getReferenceClientRect: props.clientRect,
        appendTo: () => document.body,
        content: el,
        showOnCreate: true,
        interactive: true,
        trigger: 'manual',
        placement: 'bottom-start',
        maxWidth: 'none',
        theme: 'slash-command',
        popperOptions: {
          modifiers: [{ name: 'flip', options: { fallbackPlacements: ['top-start'] } }],
        },
      });

      component = { updateProps: updateComponent, el };
    },
    onUpdate: (props) => {
      if (component) {
        component.updateProps(props);
      }
      if (popup?.[0]) {
        popup[0].setProps({ getReferenceClientRect: props.clientRect });
      }
    },
    onKeyDown: (props) => {
      if (props.event.key === 'Escape') {
        popup?.[0]?.hide();
        return true;
      }
      return commandListRef.current?.onKeyDown(props) || false;
    },
    onExit: () => {
      popup?.[0]?.destroy();
      if (root) {
        setTimeout(() => root.unmount(), 0);
      }
      component = null;
    },
  };
};

export const SlashCommand = Extension.create({
  name: 'slashCommand',

  addOptions() {
    return {
      suggestion: {
        char: '/',
        command: ({ editor, range, props }) => {
          editor.chain().focus().deleteRange(range).run();
          
          const item = props;
          switch (item.key) {
            case 'paragraph':
              editor.chain().focus().setParagraph().run();
              break;
            case 'heading1':
              editor.chain().focus().toggleHeading({ level: 1 }).run();
              break;
            case 'heading2':
              editor.chain().focus().toggleHeading({ level: 2 }).run();
              break;
            case 'heading3':
              editor.chain().focus().toggleHeading({ level: 3 }).run();
              break;
            case 'bullet_list':
              editor.chain().focus().toggleBulletList().run();
              break;
            case 'ordered_list':
              editor.chain().focus().toggleOrderedList().run();
              break;
            case 'blockquote':
              editor.chain().focus().toggleBlockquote().run();
              break;
            case 'code_block':
              editor.chain().focus().toggleCodeBlock().run();
              break;
            case 'horizontal_rule':
              editor.chain().focus().setHorizontalRule().run();
              break;
            case 'columns_1':
              editor.chain().focus().insertContent({
                type: 'columnLayout',
                attrs: { cols: 1 },
                content: [
                  { type: 'columnPane', content: [{ type: 'paragraph' }] },
                ],
              }).run();
              break;
            case 'columns_2':
              editor.chain().focus().insertContent({
                type: 'columnLayout',
                attrs: { cols: 2 },
                content: [
                  { type: 'columnPane', content: [{ type: 'paragraph' }] },
                  { type: 'columnPane', content: [{ type: 'paragraph' }] },
                ],
              }).run();
              break;
            case 'columns_3':
              editor.chain().focus().insertContent({
                type: 'columnLayout',
                attrs: { cols: 3 },
                content: [
                  { type: 'columnPane', content: [{ type: 'paragraph' }] },
                  { type: 'columnPane', content: [{ type: 'paragraph' }] },
                  { type: 'columnPane', content: [{ type: 'paragraph' }] },
                ],
              }).run();
              break;
            case 'table':
              editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
              break;
            case 'card_group':
              editor.chain().focus().insertContent({
                type: 'columnsBlock',
                attrs: { cols: 3 },
                content: [
                  { type: 'columnCard', attrs: { title: 'Card 1', description: 'Description', icon: 'rocket' } },
                  { type: 'columnCard', attrs: { title: 'Card 2', description: 'Description', icon: 'code' } },
                  { type: 'columnCard', attrs: { title: 'Card 3', description: 'Description', icon: 'zap' } },
                ],
              }).run();
              break;
            default: {
              // Check for visual steps
              if (item.key === 'steps') {
                editor.chain().focus().insertContent({
                  type: 'stepsBlock',
                  content: [{
                    type: 'stepItem',
                    attrs: { title: 'Step 1' },
                    content: [{ type: 'paragraph' }],
                  }],
                }).run();
                break;
              }
              if (item.key === 'accordion') {
                editor.chain().focus().insertContent({
                  type: 'accordionBlock',
                  content: [{
                    type: 'accordionItem',
                    attrs: { title: 'Section 1' },
                    content: [{ type: 'paragraph' }],
                  }],
                }).run();
                break;
              }
              // Component snippets — insert as markdown text or visual nodes
              const calloutTypes = {
                callout_info: 'info', callout_check: 'check', callout_note: 'note',
                callout_tip: 'tip', callout_warning: 'warning', callout_danger: 'danger',
              };
              if (calloutTypes[item.key]) {
                const ct = calloutTypes[item.key];
                const labels = { info: 'Info', check: 'Check', note: 'Note', tip: 'Tip', warning: 'Warning', danger: 'Danger' };
                editor.chain().focus().insertContent({
                  type: 'calloutBlock',
                  attrs: { calloutType: ct, title: labels[ct] },
                  content: [{ type: 'paragraph' }],
                }).run();
                break;
              }
              const snippets = {
                tabs: '<Tabs>\n<Tab label="Tab 1">\nContent\n</Tab>\n<Tab label="Tab 2">\nContent\n</Tab>\n</Tabs>',
                youtube: '<YouTube id="VIDEO_ID" title="Video Title" />',
              };
              if (snippets[item.key]) {
                editor.chain().focus().insertContent('\n\n' + snippets[item.key] + '\n\n').run();
              }
            }
          }
        },
        items: ({ query }) => {
          return SLASH_ITEMS.filter(item =>
            item.label.toLowerCase().includes(query.toLowerCase()) ||
            item.description.toLowerCase().includes(query.toLowerCase())
          );
        },
        render: renderSuggestion,
      },
    };
  },

  addProseMirrorPlugins() {
    return [
      Suggestion({
        editor: this.editor,
        ...this.options.suggestion,
      }),
    ];
  },
});
