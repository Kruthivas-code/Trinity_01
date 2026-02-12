import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import {
  BookOpen, Search, X, ExternalLink, FileText, Link2,
  ArrowUp, ArrowDown, CornerDownLeft, Plus, Tag
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * KnowledgeBasePicker - Modal for searching & inserting KB articles/links into replies
 */
const KnowledgeBasePicker = ({ isOpen, onClose, onInsertLink, onInsertContent }) => {
  const [snippets, setSnippets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [selectedSnippet, setSelectedSnippet] = useState(null);
  const searchInputRef = useRef(null);
  const listRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      fetchSnippets('');
      setSelectedSnippet(null);
      setActiveIndex(0);
      setTimeout(() => searchInputRef.current?.focus(), 50);
    } else {
      setSearch('');
      setSelectedSnippet(null);
    }
  }, [isOpen]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (isOpen) fetchSnippets(search);
    }, 200);
    return () => clearTimeout(timer);
  }, [search, isOpen]);

  const fetchSnippets = async (q) => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (q) params.append('q', q);
      const res = await fetch(`${BACKEND_URL}/api/knowledge-base-search?${params}`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setSnippets(data.items || []);
        setActiveIndex(0);
      }
    } catch (err) {
      console.error('Failed to search KB:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (selectedSnippet) {
      if (e.key === 'Escape') {
        e.preventDefault();
        setSelectedSnippet(null);
      }
      return;
    }
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveIndex(prev => Math.min(prev + 1, snippets.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setActiveIndex(prev => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (snippets[activeIndex]) setSelectedSnippet(snippets[activeIndex]);
        break;
      case 'Escape':
        e.preventDefault();
        onClose();
        break;
      default:
        break;
    }
  };

  useEffect(() => {
    if (listRef.current && snippets.length > 0) {
      const el = listRef.current.querySelector(`[data-index="${activeIndex}"]`);
      if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [activeIndex, snippets.length]);

  const handleInsertAsLink = (snippet) => {
    if (snippet.external_url) {
      onInsertLink(snippet.external_url, snippet.title);
    } else {
      onInsertLink(`[KB: ${snippet.title}]`, snippet.title);
    }
    onClose();
  };

  const handleInsertContent = (snippet) => {
    onInsertContent(snippet.content);
    onClose();
  };

  if (!isOpen) return null;

  const modalContent = (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center" onKeyDown={handleKeyDown} data-testid="kb-picker-modal">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-xl mx-4 glass rounded-xl border border-border/60 shadow-2xl overflow-hidden max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-border/60 bg-secondary/20">
          <div className="flex items-center gap-2">
            <BookOpen size={18} className="text-primary" />
            <h3 className="font-medium text-sm">
              {selectedSnippet ? 'Insert KB Article' : 'Knowledge Base'}
            </h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-secondary transition-colors" data-testid="kb-picker-close">
            <X size={16} />
          </button>
        </div>

        {selectedSnippet ? (
          /* Preview & Insert */
          <div className="flex flex-col">
            <div className="p-4 flex-1 max-h-[50vh] overflow-y-auto">
              <div className="flex items-center gap-2 mb-2">
                {selectedSnippet.snippet_type === 'external' ? (
                  <ExternalLink size={14} className="text-blue-500" />
                ) : (
                  <FileText size={14} className="text-muted-foreground" />
                )}
                <span className="font-medium text-sm">{selectedSnippet.title}</span>
              </div>
              {selectedSnippet.external_url && (
                <a href={selectedSnippet.external_url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-500 hover:underline flex items-center gap-1 mb-2">
                  <Link2 size={10} />{selectedSnippet.external_url}
                </a>
              )}
              <div className="p-3 bg-secondary/50 rounded-lg text-sm whitespace-pre-wrap max-h-48 overflow-y-auto border border-border/30" data-testid="kb-preview-content">
                {selectedSnippet.content}
              </div>
            </div>
            <div className="flex items-center justify-between p-3 border-t border-border/60 bg-secondary/10">
              <button
                onClick={() => setSelectedSnippet(null)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg hover:bg-secondary transition-colors"
                data-testid="kb-picker-back"
              >
                Back
              </button>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleInsertAsLink(selectedSnippet)}
                  className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-border hover:bg-secondary transition-colors"
                  data-testid="kb-insert-link"
                >
                  <Link2 size={13} />
                  Insert as Link
                </button>
                {selectedSnippet.snippet_type !== 'external' && (
                  <button
                    onClick={() => handleInsertContent(selectedSnippet)}
                    className="flex items-center gap-1.5 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
                    data-testid="kb-insert-content"
                  >
                    Insert Content
                    <CornerDownLeft size={13} />
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : (
          /* Search & List */
          <>
            <div className="p-3 border-b border-border/60">
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  ref={searchInputRef}
                  type="text"
                  placeholder="Search knowledge base articles..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full h-9 pl-9 pr-3 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground/60"
                  data-testid="kb-picker-search"
                />
              </div>
            </div>

            <div ref={listRef} className="max-h-80 overflow-y-auto">
              {loading ? (
                <div className="p-6 text-center text-sm text-muted-foreground">Loading...</div>
              ) : snippets.length === 0 ? (
                <div className="p-8 text-center">
                  <BookOpen size={28} className="mx-auto text-muted-foreground/30 mb-2" />
                  <p className="text-sm text-muted-foreground">
                    {search ? 'No articles match your search' : 'No published articles yet'}
                  </p>
                </div>
              ) : (
                <div className="p-2 space-y-0.5">
                  {snippets.map((snippet, idx) => (
                    <button
                      key={snippet.snippet_id}
                      data-index={idx}
                      onClick={() => setSelectedSnippet(snippet)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors group ${
                        activeIndex === idx ? 'bg-primary/15 ring-1 ring-primary/30' : 'hover:bg-secondary/70'
                      }`}
                      data-testid={`kb-picker-item-${snippet.snippet_id}`}
                    >
                      <div className="flex items-center gap-2">
                        {snippet.snippet_type === 'external' ? (
                          <ExternalLink size={12} className="text-blue-500 shrink-0" />
                        ) : (
                          <FileText size={12} className="text-muted-foreground shrink-0" />
                        )}
                        <span className="font-medium text-sm truncate">{snippet.title}</span>
                      </div>
                      <p className="text-xs text-muted-foreground truncate mt-1 pl-5">
                        {snippet.content?.substring(0, 80)}...
                      </p>
                      {(snippet.tags || []).length > 0 && (
                        <div className="flex gap-1 mt-1 pl-5">
                          {snippet.tags.slice(0, 3).map(t => (
                            <span key={t} className="text-[9px] px-1 py-0.5 bg-secondary rounded text-muted-foreground">{t}</span>
                          ))}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="p-2 border-t border-border/60 bg-secondary/10 shrink-0">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-muted-foreground">Published & refined articles</span>
                <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <kbd className="px-1 py-0.5 bg-secondary rounded text-[9px]"><ArrowUp size={9} /></kbd>
                    <kbd className="px-1 py-0.5 bg-secondary rounded text-[9px]"><ArrowDown size={9} /></kbd>
                    Navigate
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 bg-secondary rounded text-[9px]">Enter</kbd> Select
                  </span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
};

export default KnowledgeBasePicker;
