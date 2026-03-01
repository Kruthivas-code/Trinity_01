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
  Info, Lightbulb, AlertTriangle, CheckCircle,
  Columns, Youtube, MoreHorizontal, LayoutGrid
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
  { key: 'columns_2', label: '2 Columns', description: 'Two column layout', icon: Columns, group: 'Layout' },
  { key: 'columns_3', label: '3 Columns', description: 'Three column layout', icon: LayoutGrid, group: 'Layout' },
  { key: 'card_group', label: 'Card Group', description: 'Group of cards', icon: LayoutGrid, group: 'Components' },
  { key: 'callout_note', label: 'Note', description: 'Info callout', icon: Info, group: 'Components' },
  { key: 'callout_tip', label: 'Tip', description: 'Tip callout', icon: Lightbulb, group: 'Components' },
  { key: 'callout_warning', label: 'Warning', description: 'Warning callout', icon: AlertTriangle, group: 'Components' },
  { key: 'steps', label: 'Steps', description: 'Step-by-step guide', icon: CheckCircle, group: 'Components' },
  { key: 'tabs', label: 'Tabs', description: 'Tabbed content', icon: Columns, group: 'Components' },
  { key: 'accordion', label: 'Accordion', description: 'Collapsible section', icon: MoreHorizontal, group: 'Components' },
  { key: 'youtube', label: 'YouTube', description: 'Embed video', icon: Youtube, group: 'Components' },
];

const CommandList = forwardRef(({ items, command }, ref) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const listRef = useRef(null);

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
    <div ref={listRef} className="slash-command-menu bg-[#1a1a1a] border border-white/10 rounded-xl shadow-2xl py-1.5 w-56 max-h-[320px] overflow-y-auto" data-testid="slash-command-menu">
      {Object.entries(groups).map(([groupName, groupItems]) => (
        <div key={groupName}>
          <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
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
                  idx === selectedIndex ? 'bg-[#00A1B2]/20 text-white' : 'text-slate-300 hover:bg-white/5 hover:text-white'
                }`}
                data-testid={`slash-${item.key}`}
              >
                <Icon className="w-4 h-4 text-slate-400 shrink-0" />
                <div className="flex-1 text-left">
                  <div className="text-sm">{item.label}</div>
                  <div className="text-[10px] text-slate-500">{item.description}</div>
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
            case 'columns_2':
              editor.chain().focus().insertContent({
                type: 'columnsBlock',
                attrs: { cols: 2 },
                content: [
                  { type: 'columnCard', attrs: { title: 'Card 1', description: 'Description', icon: 'zap' } },
                  { type: 'columnCard', attrs: { title: 'Card 2', description: 'Description', icon: 'code' } },
                ],
              }).run();
              break;
            case 'columns_3':
              editor.chain().focus().insertContent({
                type: 'columnsBlock',
                attrs: { cols: 3 },
                content: [
                  { type: 'columnCard', attrs: { title: 'Card 1', description: 'Description', icon: 'zap' } },
                  { type: 'columnCard', attrs: { title: 'Card 2', description: 'Description', icon: 'code' } },
                  { type: 'columnCard', attrs: { title: 'Card 3', description: 'Description', icon: 'rocket' } },
                ],
              }).run();
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
              // Component snippets — insert as markdown text
              const snippets = {
                callout_note: '<Callout type="NOTE" title="Note">\nYour content here\n</Callout>',
                callout_tip: '<Callout type="TIP" title="Tip">\nYour content here\n</Callout>',
                callout_warning: '<Callout type="WARNING" title="Warning">\nYour content here\n</Callout>',
                steps: '<Steps>\n<Step title="Step 1">\nDescription\n</Step>\n<Step title="Step 2">\nDescription\n</Step>\n</Steps>',
                tabs: '<Tabs>\n<Tab label="Tab 1">\nContent\n</Tab>\n<Tab label="Tab 2">\nContent\n</Tab>\n</Tabs>',
                accordion: '<Accordion>\n<AccordionItem title="Item 1">\nContent\n</AccordionItem>\n</Accordion>',
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
