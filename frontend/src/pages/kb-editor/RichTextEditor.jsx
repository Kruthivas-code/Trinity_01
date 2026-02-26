/**
 * RichTextEditor — TipTap-based WYSIWYG editor for KB articles
 * Stores content as markdown, provides visual editing experience.
 * Supports slash commands, visual columns/cards, and standard formatting.
 */
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Image from '@tiptap/extension-image';
import Placeholder from '@tiptap/extension-placeholder';
import Underline from '@tiptap/extension-underline';
import { Markdown } from 'tiptap-markdown';
import { marked } from 'marked';
import { useState, useRef, useCallback, useEffect } from 'react';
import {
  Bold, Italic,
  List, ListOrdered, Quote, Code, Link as LinkIcon, Image as ImageIcon,
  Undo2, Redo2, ChevronDown, Plus,
  Info, Lightbulb, AlertTriangle, CheckCircle, MoreHorizontal,
  Columns, Youtube, Minus
} from 'lucide-react';
import { SlashCommand } from './extensions/SlashCommand';
import { ColumnsBlockNode, ColumnCardNode } from './extensions/ColumnsBlock';

// ============= Markdown <-> HTML Conversion Pipeline =============

// Tags that wrap children
const WRAPPER_TAGS = ['Columns', 'Callout', 'Steps', 'CardGroup', 'Tabs', 'Accordion', 'AccordionGroup'];
const STANDALONE_TAGS = ['YouTube', 'Loom', 'Figure', 'Video', 'Info', 'Note', 'Tip', 'Warning', 'Caution', 'Error', 'Danger', 'Success'];
const INNER_TAGS = ['Card', 'Step', 'Tab', 'AccordionItem'];

const preprocessMd = (md) => {
  if (!md) return { processed: '', placeholders: [], columnsBlocks: [] };
  const placeholders = [];
  const columnsBlocks = [];
  let processed = md;

  // 1. Extract <Columns> blocks with <Card> children → convert to visual nodes
  const columnsRegex = /<Columns(?:\s[\s\S]*?)?>([\s\S]*?)<\/Columns>/gi;
  processed = processed.replace(columnsRegex, (match) => {
    const colsMatch = match.match(/cols=\{?(\d+)\}?/i);
    const cols = colsMatch ? parseInt(colsMatch[1]) : 2;

    // Extract cards from within columns
    const cards = [];
    const cardRegex = /<Card(?:\s[\s\S]*?)?>([\s\S]*?)<\/Card>/gi;
    let cardMatch;
    while ((cardMatch = cardRegex.exec(match)) !== null) {
      const cardTag = cardMatch[0];
      const attrs = {};
      const attrRegex = /(\w+)=["'{]([^"'}]*)["'}]/g;
      let a;
      while ((a = attrRegex.exec(cardTag)) !== null) {
        attrs[a[1]] = a[2];
      }
      // Get inner content as description if not in attrs
      const innerContent = cardMatch[1]?.trim();
      cards.push({
        title: attrs.title || 'Card',
        description: attrs.description || innerContent || 'Description',
        icon: attrs.icon || 'file-text',
        url: attrs.url || attrs.href || '',
        imagePath: attrs.imagePath || attrs.image || '',
        cta: attrs.cta || '',
        horizontal: attrs.horizontal === 'true',
      });
    }

    const idx = columnsBlocks.length;
    columnsBlocks.push({ cols, cards });
    return `\n\nCOLUMNS_VISUAL_${idx}\n\n`;
  });

  // 2. Extract <CardGroup> similarly
  const cardGroupRegex = /<CardGroup(?:\s[\s\S]*?)?>([\s\S]*?)<\/CardGroup>/gi;
  processed = processed.replace(cardGroupRegex, (match) => {
    const colsMatch = match.match(/cols=\{?(\d+)\}?/i);
    const cols = colsMatch ? parseInt(colsMatch[1]) : 2;
    const cards = [];
    const cardRegex = /<Card(?:\s[\s\S]*?)?>([\s\S]*?)<\/Card>/gi;
    let cardMatch;
    while ((cardMatch = cardRegex.exec(match)) !== null) {
      const cardTag = cardMatch[0];
      const attrs = {};
      const attrRegex = /(\w+)=["'{]([^"'}]*)["'}]/g;
      let a;
      while ((a = attrRegex.exec(cardTag)) !== null) {
        attrs[a[1]] = a[2];
      }
      const innerContent = cardMatch[1]?.trim();
      cards.push({
        title: attrs.title || 'Card',
        description: attrs.description || innerContent || 'Description',
        icon: attrs.icon || 'file-text',
        url: attrs.url || attrs.href || '',
        imagePath: attrs.imagePath || attrs.image || '',
        cta: attrs.cta || '',
        horizontal: attrs.horizontal === 'true',
      });
    }
    const idx = columnsBlocks.length;
    columnsBlocks.push({ cols: cols || cards.length || 2, cards });
    return `\n\nCOLUMNS_VISUAL_${idx}\n\n`;
  });

  // 3. Remaining wrapper components → code blocks
  WRAPPER_TAGS.forEach(tag => {
    if (tag === 'Columns' || tag === 'CardGroup') return; // Already handled
    const regex = new RegExp(`<${tag}(?:\\s[\\s\\S]*?)?>[\\s\\S]*?<\\/${tag}>`, 'gi');
    processed = processed.replace(regex, (match) => {
      const idx = placeholders.length;
      placeholders.push(match);
      return `\n\nCOMPONENT_BLOCK_${idx}\n\n`;
    });
  });

  // 4. Standalone self-closing tags
  STANDALONE_TAGS.forEach(tag => {
    const regex = new RegExp(`<${tag}[^>]*\\/?>`, 'gi');
    processed = processed.replace(regex, (match) => {
      const idx = placeholders.length;
      placeholders.push(match);
      return `\n\nCOMPONENT_BLOCK_${idx}\n\n`;
    });
  });

  // 5. Iframes
  processed = processed.replace(/<iframe[\s\S]*?(?:\/>|<\/iframe>)/gi, (match) => {
    const idx = placeholders.length;
    placeholders.push(match);
    return `\n\nCOMPONENT_BLOCK_${idx}\n\n`;
  });

  // 6. Orphan inner components
  INNER_TAGS.forEach(tag => {
    const regex = new RegExp(`<${tag}(?:\\s[\\s\\S]*?)?>[\\s\\S]*?<\\/${tag}>`, 'gi');
    processed = processed.replace(regex, (match) => {
      const idx = placeholders.length;
      placeholders.push(match);
      return `\n\nCOMPONENT_BLOCK_${idx}\n\n`;
    });
  });

  // 7. Standalone div blocks
  processed = processed.replace(/<div[\s\S]*?<\/div>/gi, (match) => {
    const idx = placeholders.length;
    placeholders.push(match);
    return `\n\nCOMPONENT_BLOCK_${idx}\n\n`;
  });

  return { processed, placeholders, columnsBlocks };
};

const mdToHtml = (md) => {
  if (!md) return '';
  try {
    const { processed, placeholders, columnsBlocks } = preprocessMd(md);
    let html = marked.parse(processed, { breaks: false, gfm: true });

    // Restore visual columns blocks as TipTap-compatible HTML
    columnsBlocks.forEach((block, idx) => {
      const cardsHtml = block.cards.map(card =>
        `<div data-type="column-card" data-title="${(card.title || '').replace(/"/g, '&quot;')}" data-description="${(card.description || '').replace(/"/g, '&quot;')}" data-icon="${card.icon || 'file-text'}" data-url="${card.url || ''}" data-image-path="${card.imagePath || ''}" data-cta="${card.cta || ''}" data-horizontal="${card.horizontal || false}"></div>`
      ).join('');
      const columnsHtml = `<div data-type="columns-block" data-cols="${block.cols}">${cardsHtml}</div>`;
      html = html.replace(`<p>COLUMNS_VISUAL_${idx}</p>`, columnsHtml);
      html = html.replace(`COLUMNS_VISUAL_${idx}`, columnsHtml);
    });

    // Restore code-block components
    placeholders.forEach((component, idx) => {
      const escaped = component
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n\s*\n/g, '\n');
      const codeBlock = `<pre><code class="language-component">${escaped}</code></pre>`;
      html = html.replace(`<p>COMPONENT_BLOCK_${idx}</p>`, codeBlock);
      html = html.replace(`COMPONENT_BLOCK_${idx}`, codeBlock);
    });

    return html;
  } catch {
    return md;
  }
};

// Convert visual column/card nodes back to markdown
const columnsToMarkdown = (node) => {
  if (node.type.name === 'columnsBlock') {
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
    return `<Columns cols={${cols}}>\n${cards.join('\n')}\n</Columns>`;
  }
  return '';
};

// ============= Editor UI Components =============

const API = process.env.REACT_APP_BACKEND_URL;

const HEADING_OPTIONS = [
  { level: 0, label: 'Paragraph' },
  { level: 1, label: 'Heading 1' },
  { level: 2, label: 'Heading 2' },
  { level: 3, label: 'Heading 3' },
  { level: 4, label: 'Heading 4' },
  { level: 5, label: 'Heading 5' },
  { level: 6, label: 'Heading 6' },
];

const INSERT_ITEMS = [
  { key: 'callout_note', label: 'Note Callout', icon: <Info className="w-4 h-4 text-blue-400" />, snippet: '<Callout type="NOTE" title="Note">\nYour content here\n</Callout>' },
  { key: 'callout_tip', label: 'Tip Callout', icon: <Lightbulb className="w-4 h-4 text-amber-400" />, snippet: '<Callout type="TIP" title="Tip">\nYour content here\n</Callout>' },
  { key: 'callout_warning', label: 'Warning Callout', icon: <AlertTriangle className="w-4 h-4 text-red-400" />, snippet: '<Callout type="WARNING" title="Warning">\nYour content here\n</Callout>' },
  { key: 'steps', label: 'Steps', icon: <CheckCircle className="w-4 h-4 text-emerald-400" />, snippet: '<Steps>\n<Step title="Step 1">\nDescription\n</Step>\n<Step title="Step 2">\nDescription\n</Step>\n</Steps>' },
  { key: 'tabs', label: 'Tabs', icon: <Columns className="w-4 h-4 text-cyan-400" />, snippet: '<Tabs>\n<Tab label="Tab 1">\nContent\n</Tab>\n<Tab label="Tab 2">\nContent\n</Tab>\n</Tabs>' },
  { key: 'accordion', label: 'Accordion', icon: <MoreHorizontal className="w-4 h-4 text-slate-400" />, snippet: '<Accordion>\n<AccordionItem title="Item 1">\nContent\n</AccordionItem>\n</Accordion>' },
  { key: 'youtube', label: 'YouTube Video', icon: <Youtube className="w-4 h-4 text-red-400" />, snippet: '<YouTube id="VIDEO_ID" title="Video Title" />' },
  { key: 'columns_2', label: '2 Columns', icon: <Columns className="w-4 h-4 text-teal-400" />, isVisual: true, cols: 2 },
  { key: 'columns_3', label: '3 Columns', icon: <Columns className="w-4 h-4 text-teal-400" />, isVisual: true, cols: 3 },
  { key: 'code_block', label: 'Code Block', icon: <Code className="w-4 h-4 text-green-400" />, snippet: '```javascript\n// Your code here\n```' },
  { key: 'horizontal_rule', label: 'Horizontal Rule', icon: <Minus className="w-4 h-4 text-gray-400" />, snippet: '---' },
];

const ToolBtn = ({ onClick, active, disabled, children, title, theme }) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    title={title}
    className={`p-1.5 rounded-md transition-all ${active ? 'bg-[#00A1B2] text-white' : `${theme.textMuted} ${theme.hoverText} ${theme.hover}`} ${disabled ? 'opacity-30 cursor-not-allowed' : ''}`}
    data-testid={`toolbar-${title?.toLowerCase().replace(/\s+/g, '-')}`}
  >
    {children}
  </button>
);

export const RichTextEditor = ({ content, onChange, theme, onUploadImage }) => {
  const [showInsert, setShowInsert] = useState(false);
  const [showHeading, setShowHeading] = useState(false);
  const fileInputRef = useRef(null);
  const insertRef = useRef(null);
  const headingRef = useRef(null);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3, 4, 5, 6] },
      }),
      Link.configure({ openOnClick: false, HTMLAttributes: { class: 'text-[#00A1B2] underline' } }),
      Image.configure({ inline: false, allowBase64: true }),
      Underline,
      Placeholder.configure({ placeholder: 'Type "/" for commands, or start writing...' }),
      Markdown.configure({
        html: true,
        tightLists: true,
        bulletListMarker: '-',
        transformPastedText: true,
        transformCopiedText: true,
      }),
      SlashCommand,
      ColumnsBlockNode,
      ColumnCardNode,
    ],
    content: content ? mdToHtml(content) : '',
    editorProps: {
      attributes: {
        class: 'outline-none min-h-[400px] px-0 py-2',
      },
    },
    onUpdate: ({ editor }) => {
      // First get the standard markdown output
      let md = editor.storage.markdown.getMarkdown();
      
      // Restore component code blocks back to raw component syntax
      md = md.replace(/```component\n([\s\S]*?)\n```/g, (_, code) => {
        return code.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
      });

      // Serialize visual column/card nodes to markdown
      const { doc } = editor.state;
      const columnsMarkdown = [];
      doc.descendants((node) => {
        if (node.type.name === 'columnsBlock') {
          columnsMarkdown.push(columnsToMarkdown(node));
        }
      });

      // If we have visual columns that aren't in the markdown output, append them
      // The markdown serializer outputs empty strings for unknown node types
      if (columnsMarkdown.length > 0) {
        // Clean up any empty lines that represent the custom nodes
        // and inject the proper markdown
        let columnIdx = 0;
        md = md.replace(/\n{2,}/g, (match, offset) => {
          // Check if this gap corresponds to a column block position
          if (columnIdx < columnsMarkdown.length) {
            const before = md.substring(0, offset);
            const hasColumnHere = !before.includes('<Columns') || before.split('<Columns').length - 1 < columnIdx + 1;
            if (hasColumnHere && match.length >= 3) {
              return '\n\n' + columnsMarkdown[columnIdx++] + '\n\n';
            }
          }
          return match;
        });
        // If columns weren't placed inline, append them
        while (columnIdx < columnsMarkdown.length) {
          md += '\n\n' + columnsMarkdown[columnIdx++];
        }
      }

      onChange(md);
    },
  });

  // Update editor content when external content changes (switching articles)
  const lastExternalContent = useRef(content);
  useEffect(() => {
    if (!editor) return;
    if (content !== lastExternalContent.current) {
      lastExternalContent.current = content;
      editor.commands.setContent(mdToHtml(content || ''));
    }
  }, [content, editor]);

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e) => {
      if (insertRef.current && !insertRef.current.contains(e.target)) setShowInsert(false);
      if (headingRef.current && !headingRef.current.contains(e.target)) setShowHeading(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const insertSnippet = useCallback((snippet) => {
    if (!editor) return;
    editor.chain().focus().insertContent('\n\n' + snippet + '\n\n').run();
    setShowInsert(false);
  }, [editor]);

  const insertVisualColumns = useCallback((cols) => {
    if (!editor) return;
    const cards = Array.from({ length: cols }, (_, i) => ({
      type: 'columnCard',
      attrs: { title: `Card ${i + 1}`, description: 'Description', icon: ['rocket', 'code', 'zap'][i] || 'file-text' },
    }));
    editor.chain().focus().insertContent({
      type: 'columnsBlock',
      attrs: { cols },
      content: cards,
    }).run();
    setShowInsert(false);
  }, [editor]);

  const handleImageUpload = useCallback(async (file) => {
    if (!file || !file.type.startsWith('image/') || !onUploadImage) return;
    const url = await onUploadImage(file);
    if (url && editor) {
      editor.chain().focus().setImage({ src: url, alt: file.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ') }).run();
    }
  }, [editor, onUploadImage]);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) handleImageUpload(file);
    e.target.value = '';
  };

  const setLink = useCallback(() => {
    if (!editor) return;
    const prev = editor.getAttributes('link').href;
    const url = window.prompt('Enter URL', prev || 'https://');
    if (url === null) return;
    if (url === '') { editor.chain().focus().extendMarkRange('link').unsetLink().run(); return; }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
  }, [editor]);

  if (!editor) return null;

  const getCurrentHeading = () => {
    for (let i = 1; i <= 6; i++) {
      if (editor.isActive('heading', { level: i })) return `Heading ${i}`;
    }
    return 'Paragraph';
  };

  return (
    <div data-testid="rich-text-editor">
      {/* Toolbar */}
      <div className={`flex items-center gap-1 flex-wrap py-2 mb-3 border-b ${theme.border}`} data-testid="editor-toolbar">
        {/* Insert Button */}
        <div className="relative" ref={insertRef}>
          <button
            type="button"
            onClick={() => { setShowInsert(!showInsert); setShowHeading(false); }}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${showInsert ? 'bg-[#00A1B2] text-white' : `${theme.inputBg} border ${theme.inputBorder} ${theme.textMuted} ${theme.hoverText}`}`}
            data-testid="insert-btn"
          >
            <Plus className="w-3.5 h-3.5" /> Insert
          </button>
          {showInsert && (
            <div className={`absolute z-50 top-full mt-1 left-0 ${theme.id === 'dark' ? 'bg-[#1a1a1a] border-white/10' : 'bg-white border-gray-200'} border rounded-xl shadow-2xl py-1.5 w-52`} data-testid="insert-menu">
              {INSERT_ITEMS.map(item => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => item.isVisual ? insertVisualColumns(item.cols) : insertSnippet(item.snippet)}
                  className={`w-full flex items-center gap-3 px-3 py-2 text-sm ${theme.textMuted} ${theme.hover} ${theme.hoverText} transition-colors`}
                  data-testid={`insert-${item.key}`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Heading Dropdown */}
        <div className="relative" ref={headingRef}>
          <button
            type="button"
            onClick={() => { setShowHeading(!showHeading); setShowInsert(false); }}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all min-w-[110px] justify-between ${theme.inputBg} border ${theme.inputBorder} ${theme.textMuted} ${theme.hoverText}`}
            data-testid="heading-dropdown"
          >
            <span>{getCurrentHeading()}</span>
            <ChevronDown className="w-3 h-3" />
          </button>
          {showHeading && (
            <div className={`absolute z-50 top-full mt-1 left-0 ${theme.id === 'dark' ? 'bg-[#1a1a1a] border-white/10' : 'bg-white border-gray-200'} border rounded-xl shadow-2xl py-1 w-40`} data-testid="heading-menu">
              {HEADING_OPTIONS.map(opt => (
                <button
                  key={opt.level}
                  type="button"
                  onClick={() => {
                    if (opt.level === 0) editor.chain().focus().setParagraph().run();
                    else editor.chain().focus().toggleHeading({ level: opt.level }).run();
                    setShowHeading(false);
                  }}
                  className={`w-full text-left px-3 py-1.5 text-sm transition-colors ${
                    (opt.level === 0 && !editor.isActive('heading')) || editor.isActive('heading', { level: opt.level })
                      ? 'text-[#00A1B2] font-medium' : `${theme.textMuted} ${theme.hover} ${theme.hoverText}`
                  }`}
                  data-testid={`heading-${opt.level}`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className={`w-px h-5 ${theme.divider} mx-0.5`} />

        {/* Formatting */}
        <ToolBtn onClick={setLink} active={editor.isActive('link')} title="Link" theme={theme}><LinkIcon className="w-4 h-4" /></ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} title="Bold" theme={theme}><Bold className="w-4 h-4" /></ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} title="Italic" theme={theme}><Italic className="w-4 h-4" /></ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().toggleBlockquote().run()} active={editor.isActive('blockquote')} title="Blockquote" theme={theme}><Quote className="w-4 h-4" /></ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().toggleCode().run()} active={editor.isActive('code')} title="Inline Code" theme={theme}><Code className="w-4 h-4" /></ToolBtn>

        <div className={`w-px h-5 ${theme.divider} mx-0.5`} />

        <ToolBtn onClick={() => editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} title="Bullet List" theme={theme}><List className="w-4 h-4" /></ToolBtn>
        <ToolBtn onClick={() => editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} title="Ordered List" theme={theme}><ListOrdered className="w-4 h-4" /></ToolBtn>

        <div className={`w-px h-5 ${theme.divider} mx-0.5`} />

        <ToolBtn onClick={() => fileInputRef.current?.click()} title="Upload Image" theme={theme}><ImageIcon className="w-4 h-4" /></ToolBtn>
        <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileSelect} className="hidden" />

        <div className="ml-auto flex items-center gap-0.5">
          <ToolBtn onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} title="Undo" theme={theme}><Undo2 className="w-4 h-4" /></ToolBtn>
          <ToolBtn onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} title="Redo" theme={theme}><Redo2 className="w-4 h-4" /></ToolBtn>
        </div>
      </div>

      {/* Slash command hint */}
      <p className={`text-[11px] ${theme.textTertiary} mb-2`}>Type <kbd className="px-1 py-0.5 rounded text-[10px] bg-slate-800/50 border border-white/5">/</kbd> for commands</p>

      {/* Editor Content */}
      <EditorContent
        editor={editor}
        className={`tiptap-editor prose ${theme.proseClass} max-w-none ${theme.text} [&_.tiptap]:outline-none [&_.tiptap]:min-h-[400px]`}
        data-testid="editor-content-area"
      />
    </div>
  );
};
