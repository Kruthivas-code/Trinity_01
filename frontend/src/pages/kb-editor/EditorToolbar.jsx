/**
 * EditorToolbar — Markdown formatting toolbar with snippet insertion
 */
import { useState, useRef } from 'react';
import {
  Bold, Italic, Heading1, Heading2, Heading3,
  List, ListOrdered, Quote, Code, Link as LinkIcon, Image as ImageIcon,
  MoreHorizontal, Info, AlertTriangle, Lightbulb, CheckCircle,
  Columns, Youtube
} from 'lucide-react';

const ToolBtn = ({ onClick, active, disabled, children, title, theme }) => (
  <button onClick={onClick} disabled={disabled} title={title}
    className={`p-1.5 rounded-md transition-all ${active ? 'bg-[#00A1B2] text-white' : `${theme.textMuted} ${theme.hoverText} ${theme.hover}`} ${disabled ? 'opacity-30 cursor-not-allowed' : ''}`}>
    {children}
  </button>
);

const SNIPPET_MAP = {
  callout_note: '<Callout type="NOTE" title="Note">\nYour content here\n</Callout>',
  callout_tip: '<Callout type="TIP" title="Tip">\nYour content here\n</Callout>',
  callout_warning: '<Callout type="WARNING" title="Warning">\nYour content here\n</Callout>',
  steps: '<Steps>\n<Step title="Step 1">\nDescription\n</Step>\n<Step title="Step 2">\nDescription\n</Step>\n</Steps>',
  card_group: '<CardGroup>\n<Card title="Card 1" icon="rocket">\nDescription\n</Card>\n<Card title="Card 2" icon="code">\nDescription\n</Card>\n</CardGroup>',
  tabs: '<Tabs>\n<Tab label="Tab 1">\nContent\n</Tab>\n<Tab label="Tab 2">\nContent\n</Tab>\n</Tabs>',
  accordion: '<Accordion>\n<AccordionItem title="Item 1">\nContent\n</AccordionItem>\n</Accordion>',
  youtube: '<YouTube id="VIDEO_ID" title="Video Title" />',
  columns: '<Columns cols={2}>\n<Card title="Left" icon="zap">\nContent\n</Card>\n<Card title="Right" icon="code">\nContent\n</Card>\n</Columns>',
};

const INSERT_ITEMS = [
  { key: 'callout_note', label: 'Note Callout', icon: <Info className="w-4 h-4 text-blue-400" /> },
  { key: 'callout_tip', label: 'Tip Callout', icon: <Lightbulb className="w-4 h-4 text-amber-400" /> },
  { key: 'callout_warning', label: 'Warning Callout', icon: <AlertTriangle className="w-4 h-4 text-red-400" /> },
  { key: 'steps', label: 'Steps', icon: <CheckCircle className="w-4 h-4 text-emerald-400" /> },
  { key: 'card_group', label: 'Card Group', icon: <Columns className="w-4 h-4 text-purple-400" /> },
  { key: 'tabs', label: 'Tabs', icon: <Columns className="w-4 h-4 text-cyan-400" /> },
  { key: 'accordion', label: 'Accordion', icon: <MoreHorizontal className="w-4 h-4 text-slate-400" /> },
  { key: 'youtube', label: 'YouTube Video', icon: <Youtube className="w-4 h-4 text-red-400" /> },
  { key: 'columns', label: 'Columns', icon: <Columns className="w-4 h-4 text-teal-400" /> },
];

export const EditorToolbar = ({ textareaRef, content, setContent, onUploadImage, theme }) => {
  const [showInsert, setShowInsert] = useState(false);
  const fileInputRef = useRef(null);

  const wrap = (prefix, suffix = prefix) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const selected = content.substring(start, end);
    const before = content.substring(0, start);
    const after = content.substring(end);
    const newText = `${before}${prefix}${selected || 'text'}${suffix}${after}`;
    setContent(newText);
    setTimeout(() => { ta.focus(); ta.setSelectionRange(start + prefix.length, start + prefix.length + (selected || 'text').length); }, 0);
  };

  const insertLine = (prefix) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const pos = ta.selectionStart;
    const before = content.substring(0, pos);
    const after = content.substring(pos);
    const needsNewline = before.length > 0 && !before.endsWith('\n') ? '\n' : '';
    const text = `${before}${needsNewline}${prefix}`;
    setContent(text + after);
    setTimeout(() => { ta.focus(); ta.setSelectionRange(text.length, text.length); }, 0);
  };

  const insertSnippet = (key) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const pos = ta.selectionStart;
    const before = content.substring(0, pos);
    const after = content.substring(pos);
    const needsNewline = before.length > 0 && !before.endsWith('\n') ? '\n\n' : '';
    const text = `${before}${needsNewline}${SNIPPET_MAP[key]}\n`;
    setContent(text + after);
    setShowInsert(false);
    setTimeout(() => { ta.focus(); ta.setSelectionRange(text.length, text.length); }, 0);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) onUploadImage(file);
    e.target.value = '';
  };

  return (
    <div className={`flex items-center gap-0.5 px-4 py-2 border-b ${theme.border} ${theme.panelBg} flex-shrink-0 flex-wrap`} data-testid="editor-toolbar">
      <ToolBtn onClick={() => insertLine('# ')} title="Heading 1" theme={theme}><Heading1 className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => insertLine('## ')} title="Heading 2" theme={theme}><Heading2 className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => insertLine('### ')} title="Heading 3" theme={theme}><Heading3 className="w-4 h-4" /></ToolBtn>
      <div className={`w-px h-5 ${theme.divider} mx-1`} />
      <ToolBtn onClick={() => wrap('**')} title="Bold (Cmd+B)" theme={theme}><Bold className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => wrap('*')} title="Italic (Cmd+I)" theme={theme}><Italic className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => wrap('`')} title="Inline Code" theme={theme}><Code className="w-4 h-4" /></ToolBtn>
      <div className={`w-px h-5 ${theme.divider} mx-1`} />
      <ToolBtn onClick={() => insertLine('- ')} title="Bullet List" theme={theme}><List className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => insertLine('1. ')} title="Numbered List" theme={theme}><ListOrdered className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => insertLine('> ')} title="Blockquote" theme={theme}><Quote className="w-4 h-4" /></ToolBtn>
      <div className={`w-px h-5 ${theme.divider} mx-1`} />
      <ToolBtn onClick={() => wrap('[', '](url)')} title="Link" theme={theme}><LinkIcon className="w-4 h-4" /></ToolBtn>
      <ToolBtn onClick={() => fileInputRef.current?.click()} title="Upload Image" theme={theme}><ImageIcon className="w-4 h-4" /></ToolBtn>
      <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileSelect} className="hidden" />
      <div className={`w-px h-5 ${theme.divider} mx-1`} />
      <div className="relative">
        <ToolBtn onClick={() => setShowInsert(!showInsert)} active={showInsert} title="Insert component" theme={theme}>
          <MoreHorizontal className="w-4 h-4" />
        </ToolBtn>
        {showInsert && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setShowInsert(false)} />
            <div className={`absolute z-50 top-full mt-1 left-0 ${theme.dropdownBg} border ${theme.dropdownBorder} rounded-xl shadow-2xl py-1.5 w-52`} data-testid="insert-menu">
              {INSERT_ITEMS.map(item => (
                <button key={item.key} onClick={() => insertSnippet(item.key)}
                  className={`w-full flex items-center gap-3 px-3 py-2 text-sm ${theme.textMuted} ${theme.hover} ${theme.hoverText} transition-colors`}
                  data-testid={`insert-${item.key}`}>
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
