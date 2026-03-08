import React, { useRef, useEffect, useCallback } from 'react';
import { 
  Bold, Italic, Underline, List, ListOrdered, 
  Link2, Quote, Code, Minus
} from 'lucide-react';

// Toolbar button component - defined outside to prevent re-creation
const ToolbarButton = ({ onClick, children, title, disabled }) => (
  <button
    type="button"
    onMouseDown={(e) => {
      e.preventDefault(); // Prevent focus loss
      if (!disabled) onClick();
    }}
    className="h-7 w-7 flex items-center justify-center rounded transition-colors text-foreground/60 hover:text-foreground hover:bg-foreground/10 disabled:opacity-50 disabled:cursor-not-allowed"
    title={title}
    disabled={disabled}
  >
    {children}
  </button>
);

const RichTextEditor = ({ 
  value, 
  onChange, 
  placeholder = 'Type here...', 
  mode = 'note',
  onSubmit,
  disabled = false 
}) => {
  const editorRef = useRef(null);
  const isInitialMount = useRef(true);

  // Initialize editor content
  useEffect(() => {
    if (editorRef.current && isInitialMount.current) {
      editorRef.current.innerHTML = value || '';
      isInitialMount.current = false;
    }
  }, [value]);

  // Sync external value changes (e.g., clearing after submit or inserting canned responses)
  useEffect(() => {
    if (editorRef.current && !isInitialMount.current) {
      // Only update if the value is different (to avoid cursor jumping)
      const currentContent = editorRef.current.innerHTML;
      const currentClean = currentContent === '<br>' ? '' : currentContent;
      if (value !== currentClean) {
        editorRef.current.innerHTML = value || '';
      }
    }
  }, [value]);

  const handleInput = useCallback(() => {
    if (editorRef.current) {
      const html = editorRef.current.innerHTML;
      const cleanHtml = html === '<br>' ? '' : html;
      onChange(cleanHtml);
    }
  }, [onChange]);

  const execCommand = useCallback((command, cmdValue = null) => {
    document.execCommand(command, false, cmdValue);
    editorRef.current?.focus();
    handleInput();
  }, [handleInput]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      onSubmit?.();
    }
  }, [onSubmit]);

  const insertLink = useCallback(() => {
    const url = window.prompt('Enter URL:');
    if (url) {
      execCommand('createLink', url);
    }
  }, [execCommand]);

  return (
    <div className={`rounded-lg border transition-all ${
      disabled ? 'opacity-50' : ''
    } ${
      mode === 'note' 
        ? 'border-amber-400/30 focus-within:border-amber-400/50 focus-within:ring-1 focus-within:ring-amber-400/30' 
        : 'border-border/40 focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/30'
    }`}>
      {/* Toolbar */}
      <div className="flex items-center gap-0.5 px-2 py-1.5 border-b border-border/30 bg-secondary/20 rounded-t-lg">
        <ToolbarButton onClick={() => execCommand('bold')} title="Bold (⌘B)" disabled={disabled}>
          <Bold size={14} />
        </ToolbarButton>
        <ToolbarButton onClick={() => execCommand('italic')} title="Italic (⌘I)" disabled={disabled}>
          <Italic size={14} />
        </ToolbarButton>
        <ToolbarButton onClick={() => execCommand('underline')} title="Underline (⌘U)" disabled={disabled}>
          <Underline size={14} />
        </ToolbarButton>
        
        <div className="w-px h-4 bg-border/40 mx-1" />
        
        <ToolbarButton onClick={() => execCommand('insertUnorderedList')} title="Bullet list" disabled={disabled}>
          <List size={14} />
        </ToolbarButton>
        <ToolbarButton onClick={() => execCommand('insertOrderedList')} title="Numbered list" disabled={disabled}>
          <ListOrdered size={14} />
        </ToolbarButton>
        
        <div className="w-px h-4 bg-border/40 mx-1" />
        
        <ToolbarButton onClick={() => execCommand('formatBlock', 'blockquote')} title="Quote" disabled={disabled}>
          <Quote size={14} />
        </ToolbarButton>
        <ToolbarButton onClick={() => execCommand('formatBlock', 'pre')} title="Code block" disabled={disabled}>
          <Code size={14} />
        </ToolbarButton>
        <ToolbarButton onClick={insertLink} title="Insert link" disabled={disabled}>
          <Link2 size={14} />
        </ToolbarButton>
        <ToolbarButton onClick={() => execCommand('insertHorizontalRule')} title="Divider" disabled={disabled}>
          <Minus size={14} />
        </ToolbarButton>
      </div>

      {/* Editor Area */}
      <div
        ref={editorRef}
        contentEditable={!disabled}
        onInput={handleInput}
        onKeyDown={handleKeyDown}
        className="min-h-[80px] max-h-[200px] overflow-y-auto px-3 py-2.5 text-sm text-foreground outline-none bg-secondary/10 rounded-b-lg prose prose-sm dark:prose-invert max-w-none
          [&_blockquote]:border-l-2 [&_blockquote]:border-primary/50 [&_blockquote]:pl-3 [&_blockquote]:italic [&_blockquote]:text-muted-foreground
          [&_pre]:bg-foreground/10 [&_pre]:rounded [&_pre]:p-2 [&_pre]:text-xs [&_pre]:font-mono
          [&_a]:text-primary [&_a]:underline
          [&_ul]:list-disc [&_ul]:pl-4
          [&_ol]:list-decimal [&_ol]:pl-4
          [&_hr]:border-border/40 [&_hr]:my-2"
        data-placeholder={placeholder}
        style={{ minHeight: '80px' }}
        data-testid="rich-text-editor"
        suppressContentEditableWarning
      />

      {/* Empty state placeholder */}
      <style>{`
        [data-testid="rich-text-editor"]:empty:before {
          content: attr(data-placeholder);
          color: hsl(var(--muted-foreground) / 0.7);
          pointer-events: none;
        }
      `}</style>
    </div>
  );
};

export default RichTextEditor;
