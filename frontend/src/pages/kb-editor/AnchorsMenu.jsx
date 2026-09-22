/**
 * AnchorsMenu — Anchors Menu (Phase 4 of the help-doc-v3 port).
 * Dropdown listing every heading in the current article plus any inline
 * `<a id="...">` anchor markers, lets you copy a deep-link URL for any of
 * them, and insert a new `<a id="..."></a>` marker at the end of the
 * content.
 *
 * Ported from help-doc-v3's frontend/src/components/editor/AnchorsMenu.jsx,
 * restyled to Trinity's kb-editor `theme` prop convention. Heading
 * extraction reuses Trinity's OWN parser
 * (frontend/src/lib/mdx/parser.js's parseContent()) instead of
 * reimplementing heading regex + slugify — same `# heading` -> id scheme
 * DocContent.jsx's table-of-contents already uses on the public site, so a
 * copied anchor link is guaranteed to match what the public page actually
 * renders. Trinity's parser doesn't support (and this file doesn't invent)
 * help-doc-v3's `{#custom-id}` heading-id override syntax — Trinity's real
 * markdown vocabulary (routes/assistant.py's COMPONENT_GUIDE) has no such
 * escape hatch, so a heading's anchor is always its auto-generated slug.
 * Inline `<a id="...">`/`<a name="...">` markers ARE new parsing here
 * (parseContent() only extracts headings) since they're plain HTML, not a
 * component the MDX parser needs to recognize.
 *
 * Props:
 *   content         — current markdown content (string)
 *   onContentChange — (newContent) => void, used to insert a new anchor
 *   slug            — current article's slug (the /docs/{slug} path segment)
 *   theme           — kb-editor EDITOR_THEMES entry
 */
import { useState, useMemo, useRef, useEffect } from 'react';
import { Link2, Copy, Check, Plus, Hash, X } from 'lucide-react';
import { parseContent } from '../../lib/mdx/parser';

const slugify = (text) => String(text || '')
  .toLowerCase().trim()
  .replace(/[^\w\s-]/g, '')
  .replace(/\s+/g, '-')
  .replace(/-+/g, '-');

const parseInlineAnchors = (content) => {
  if (!content) return [];
  const items = [];
  const lines = content.split('\n');
  let inCodeFence = false;
  lines.forEach((line) => {
    if (/^```/.test(line)) { inCodeFence = !inCodeFence; return; }
    if (inCodeFence) return;
    const anchorRegex = /<a\s+(?:id|name)=["']([^"']+)["'][^>]*>/g;
    let m;
    while ((m = anchorRegex.exec(line)) !== null) {
      items.push({ type: 'inline', level: 0, text: m[1], id: m[1], custom: true });
    }
  });
  return items;
};

const parseAnchors = (content) => {
  const headings = parseContent(content).headings.map((h) => ({
    type: 'heading', level: h.level, text: h.text, id: h.id, custom: false,
  }));
  return [...headings, ...parseInlineAnchors(content)];
};

export const AnchorsMenu = ({ content, onContentChange, slug, theme }) => {
  const [open, setOpen] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [newAnchorId, setNewAnchorId] = useState('');
  const dropdownRef = useRef(null);
  const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
  const docPath = slug ? `/docs/${slug}` : '/docs';

  const anchors = useMemo(() => parseAnchors(content), [content]);

  useEffect(() => {
    const onDown = (e) => {
      if (!open) return;
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  const handleCopy = async (anchorId) => {
    const url = `${baseUrl}${docPath}#${anchorId}`;
    try { await navigator.clipboard.writeText(url); } catch (e) { /* clipboard unavailable */ }
    setCopiedId(anchorId);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const handleInsertAnchor = () => {
    const id = slugify(newAnchorId);
    if (!id) return;
    onContentChange((content || '') + `\n\n<a id="${id}"></a>\n`);
    setNewAnchorId('');
  };

  const idTaken = anchors.some((a) => a.id === slugify(newAnchorId));
  const canInsert = newAnchorId.trim().length > 0 && !idTaken;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
          open ? 'bg-[#00A1B2] text-white' : `${theme.textMuted} ${theme.hoverText} ${theme.hover}`
        }`}
        title="Anchors & deep links"
        data-testid="anchors-toggle"
      >
        <Link2 className="w-4 h-4" />
        <span className="hidden sm:inline">Anchors</span>
        {anchors.length > 0 && (
          <span className={`ml-0.5 px-1.5 py-0.5 text-[10px] font-bold rounded-full ${open ? 'bg-white/20 text-white' : `${theme.inputBg} ${theme.textMuted}`}`}>
            {anchors.length}
          </span>
        )}
      </button>

      {open && (
        <div
          className={`absolute right-0 mt-2 w-[380px] max-h-[70vh] rounded-xl shadow-2xl overflow-hidden z-50 flex flex-col border ${theme.dropdownBorder} ${theme.dropdownBg}`}
          style={theme.dropdownBgStyle}
          data-testid="anchors-dropdown"
        >
          <div className={`px-4 py-3 border-b ${theme.border} flex items-center justify-between`}>
            <div>
              <p className={`text-[10px] uppercase tracking-wide font-semibold ${theme.textSecondary}`}>Document anchors</p>
              <p className={`text-sm font-semibold mt-0.5 ${theme.text}`}>Deep-link to any heading</p>
            </div>
            <button type="button" onClick={() => setOpen(false)} className={`p-1 rounded ${theme.textMuted} ${theme.hoverText}`} aria-label="Close">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className={`px-4 py-3 border-b ${theme.border}`}>
            <p className={`text-[10px] uppercase tracking-wide font-semibold mb-2 ${theme.textSecondary}`}>Insert anchor marker</p>
            <div className="flex items-center gap-2">
              <div className={`flex-1 flex items-center rounded-md border ${theme.inputBorder} ${theme.inputBg}`} style={theme.inputBgStyle}>
                <span className="pl-2.5 pr-1 text-slate-400 font-mono text-sm">#</span>
                <input
                  value={newAnchorId}
                  onChange={(e) => setNewAnchorId(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && canInsert) handleInsertAnchor(); }}
                  placeholder="my-anchor"
                  className={`flex-1 py-1.5 pr-2 bg-transparent text-sm outline-none font-mono ${theme.inputText} ${theme.placeholder}`}
                  data-testid="anchor-input"
                />
              </div>
              <button
                type="button"
                onClick={handleInsertAnchor}
                disabled={!canInsert}
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-[#00A1B2] text-white text-sm font-medium rounded-md disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
                data-testid="anchor-insert"
              >
                <Plus className="w-3.5 h-3.5" /> Insert
              </button>
            </div>
            {idTaken && newAnchorId.trim() && (
              <p className="mt-1.5 text-xs text-rose-500">Anchor ID already exists in this document.</p>
            )}
            <p className={`mt-1.5 text-[11px] ${theme.textSecondary}`}>
              Inserts <code className={`font-mono px-1 py-0.5 rounded ${theme.inputBg}`}>{'<a id="…"></a>'}</code> at end of content.
            </p>
          </div>

          <div className="flex-1 overflow-y-auto">
            <div className={`px-4 py-2 sticky top-0 border-b ${theme.border} ${theme.dropdownBg}`} style={theme.dropdownBgStyle}>
              <p className={`text-[10px] uppercase tracking-wide font-semibold ${theme.textSecondary}`}>Existing anchors · {anchors.length}</p>
            </div>
            {anchors.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <Hash className={`w-6 h-6 mx-auto mb-2 ${theme.textTertiary}`} />
                <p className={`text-sm ${theme.textMuted}`}>No headings or anchors yet.</p>
              </div>
            ) : (
              <ul className={`divide-y ${theme.id === 'dark' ? 'divide-slate-800' : 'divide-gray-100'}`}>
                {anchors.map((a, i) => {
                  const isHeading = a.type === 'heading';
                  const indent = isHeading ? Math.max(0, a.level - 1) * 12 : 0;
                  const isCopied = copiedId === a.id;
                  return (
                    <li key={`${a.id}-${i}`} className={`flex items-center gap-2 px-4 py-2 ${theme.hover} group`}>
                      <span className={`text-[10px] font-mono font-bold rounded px-1.5 py-0.5 flex-shrink-0 ${
                        isHeading ? 'bg-[#00A1B2]/10 text-[#00A1B2]' : 'bg-amber-500/10 text-amber-600 dark:text-amber-300'
                      }`}>
                        {isHeading ? `H${a.level}` : 'A'}
                      </span>
                      <div className="min-w-0 flex-1" style={{ paddingLeft: indent }}>
                        <p className={`text-sm font-medium truncate ${theme.text}`}>{a.text}</p>
                        <p className={`text-[11px] font-mono truncate ${theme.textSecondary}`}>#{a.id}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleCopy(a.id)}
                        className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded border opacity-0 group-hover:opacity-100 transition-all ${theme.inputBorder} ${theme.inputBg} ${theme.textMuted} hover:text-[#00A1B2] hover:border-[#00A1B2]`}
                        data-testid={`copy-anchor-${a.id}`}
                        title="Copy link"
                      >
                        {isCopied ? (<><Check className="w-3 h-3 text-[#00A1B2]" /><span className="text-[#00A1B2]">Copied</span></>) : (<><Copy className="w-3 h-3" /> Copy link</>)}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AnchorsMenu;
