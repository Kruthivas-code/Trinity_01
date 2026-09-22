/**
 * WritingAssistant — AI writing companion for the KB editor (Phase 3 of the
 * help-doc-v3 feature port).
 *
 * Ported UX from help-doc-v3/frontend/src/components/editor/WritingAssistant.jsx
 * (3 modes, diff-preview accept/discard/retry, 8 canned quick actions in
 * Tweak, a style picker in New Page), but:
 *   - adapted to Trinity's own fetch + isDark/local-classes conventions,
 *     the same way Phase 2's VersionHistoryPanel.jsx (a right-side
 *     slide-over opened from a header button, exactly this component's
 *     shape) established — plain `fetch(..., { credentials: 'include' })`,
 *     no axios, no sonner toasts;
 *   - the quick-action instructions teach Trinity's REAL markdown/component
 *     vocabulary (frontend/src/lib/mdx/parser.js is the ground truth for
 *     exact tag syntax), not help-doc-v3's Mintlify-flavored one — most
 *     importantly `<Tab label="...">` (not `title`) and a bare `<CardGroup>`
 *     with no `cols` attribute;
 *   - "New Page" mode never calls a creation endpoint itself. It hands the
 *     generated draft back to the caller via `onDraftNewPage`, which
 *     KBEditor.jsx wires up to do exactly what its own sidebar "+" already
 *     does: pre-fill the new-page form and route to
 *     /dashboard/kb-editor/new. The actual creation request from there is
 *     the SAME, unmodified, owner-gated POST /api/kb/admin/articles Phase 1
 *     already protects — a non-owner can draft with the assistant, but
 *     still can't create the page (same 403 as the manual "+" flow). See
 *     backend/routes/assistant.py's module docstring for the full
 *     reasoning.
 *
 * Backend endpoints used (backend/routes/assistant.py):
 *   POST /api/assistant/tweak     { instruction, markdown, selection? } -> { markdown, applied_to_selection }
 *   POST /api/assistant/generate  { raw_input, title?, style? }         -> { markdown, title }
 *   POST /api/assistant/chat      { message, markdown? }                -> { reply }
 */
import { useEffect, useMemo, useState, useCallback } from 'react';
import {
  Sparkles, X, Wand2, FilePlus2, MessageSquare, Loader2,
  Check, RotateCcw, ChevronRight, AlertCircle,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const QUICK_TWEAKS = [
  { id: 'improve', label: 'Improve writing', instruction: 'Polish the prose. Tighten sentences, remove fluff, fix grammar, and keep the same meaning.' },
  { id: 'expand', label: 'Expand', instruction: 'Add more depth, examples, and clarifying details where the content is thin. Stay faithful to the original facts.' },
  { id: 'shorten', label: 'Shorten', instruction: 'Make this more concise. Cut filler words and redundant phrasing while keeping every meaningful point.' },
  { id: 'simpler', label: 'Simpler language', instruction: 'Rewrite for a less technical audience. Replace jargon with plain language where appropriate.' },
  { id: 'examples', label: 'Add examples', instruction: 'Add concrete code examples or use cases where they would help the reader understand.' },
  { id: 'callouts', label: 'Add callouts', instruction: 'Insert <Callout type="note|tip|warning"> blocks at the spots where they would aid comprehension. Keep the rest of the structure exactly as-is.' },
  { id: 'to-steps', label: 'Convert to Steps', instruction: 'Identify sequential procedures in this content (numbered lists, "first/then/finally", install-then-configure-then-run patterns) and convert them into a <Steps><Step title="…">body</Step></Steps> block (the outer <Steps> tag takes no attributes). Leave non-sequential content untouched.' },
  { id: 'to-cards', label: 'Convert to CardGroup', instruction: 'Find sections that present parallel options or features (e.g. multiple frameworks, multiple platforms, related links) and convert them into a <CardGroup><Card title="…" icon="lucide-icon-name" href="…">short description</Card></CardGroup> (the outer <CardGroup> tag takes no attributes, and each Card\'s attributes must appear in the order title, icon, href). Use lucide icon names like rocket, book, code, settings, link, zap, terminal. Do not invent links — omit href if none is mentioned.' },
  { id: 'to-tabs', label: 'Add code Tabs', instruction: 'For any code example in this content, wrap or extend it in a <Tabs> component with at least two <Tab label="JavaScript"> / <Tab label="Python"> / <Tab label="cURL"> children (use `label`, not `title`), each containing the equivalent code block in its language. Preserve the surrounding prose. If a sample isn\'t portable to a language, mark it with a one-line comment explaining why instead of omitting the tab.' },
];

const STYLES = [
  { id: 'documentation', label: 'Documentation' },
  { id: 'tutorial', label: 'Tutorial' },
  { id: 'reference', label: 'Reference' },
  { id: 'blog', label: 'Blog post' },
];

const slugify = (s) =>
  (s || '').toLowerCase().trim().replace(/[^a-z0-9-_ ]/g, '').replace(/\s+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '') || `page-${Date.now()}`;

// Flatten the recursive kb_navigation tree into a pickable list of every
// group (any depth), each carrying its top-level ancestor's key/label —
// exactly the (nav_group_key, nav_group_label, section_key, section_label)
// shape create_article expects. A top-level group is a valid target in its
// own right (nav_group_key === section_key), same as picking it from the
// sidebar's "+" today.
function flattenGroupTargets(nodes, topKey, topLabel, depth, out) {
  for (const node of nodes || []) {
    if (node.type !== 'group') continue;
    const myTopKey = depth === 0 ? node.key : topKey;
    const myTopLabel = depth === 0 ? (node.label || node.key) : topLabel;
    out.push({
      key: node.key,
      label: `${'—'.repeat(depth)}${depth ? ' ' : ''}${node.label || node.key}`,
      topKey: myTopKey,
      topLabel: myTopLabel,
    });
    flattenGroupTargets(node.children || [], myTopKey, myTopLabel, depth + 1, out);
  }
  return out;
}

async function postJSON(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}

// ===================================================================
// Trigger button — sits in the editor header, next to Preview/History
// ===================================================================
export const WritingAssistantTrigger = ({ onOpen, isDark }) => (
  <button
    onClick={onOpen}
    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isDark ? 'bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700' : 'bg-gray-100 text-gray-600 hover:text-gray-900 hover:bg-gray-200'}`}
    title="Writing Assistant"
    data-testid="writing-assistant-trigger"
  >
    <Sparkles className="w-4 h-4" />
    <span className="hidden sm:inline">Assist</span>
  </button>
);

// ===================================================================
// Slide-over panel
// ===================================================================
export const WritingAssistant = ({
  open, onClose, isDark,
  content, selection, onApplyContent, onApplySelection,      // Tweak mode
  navGroups, articlesCount, onDraftNewPage,                  // New Page mode
}) => {
  const [mode, setMode] = useState('tweak'); // 'tweak' | 'new' | 'chat'
  const [visible, setVisible] = useState(false);

  useEffect(() => { if (open) requestAnimationFrame(() => setVisible(true)); }, [open]);

  const handleClose = useCallback(() => {
    setVisible(false);
    setTimeout(onClose, 200);
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e) => { if (e.key === 'Escape') handleClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, handleClose]);

  if (!open) return null;

  const panelBg = isDark ? 'bg-[#111111] border-slate-800' : 'bg-white border-gray-200';
  const text = isDark ? 'text-white' : 'text-gray-900';
  const textMuted = isDark ? 'text-slate-400' : 'text-gray-500';
  const border = isDark ? 'border-slate-800' : 'border-gray-200';

  return (
    <>
      <div
        className={`fixed z-40 transition-opacity duration-200 ${visible ? 'opacity-100' : 'opacity-0'}`}
        style={{ top: '56px', left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.25)' }}
        onClick={handleClose}
        data-testid="writing-assistant-backdrop"
      />
      <div
        className={`fixed z-50 flex flex-col border-l shadow-2xl transition-transform duration-200 ease-out ${panelBg} ${visible ? 'translate-x-0' : 'translate-x-full'}`}
        style={{ top: '56px', right: 0, bottom: 0, width: '440px', maxWidth: '100vw' }}
        data-testid="writing-assistant-panel"
      >
        {/* Header */}
        <div className={`flex items-center justify-between px-4 py-3 border-b flex-shrink-0 ${border}`}>
          <div className="flex items-center gap-2">
            <Sparkles className={`w-4 h-4 ${text}`} />
            <h2 className={`font-semibold text-sm ${text}`}>Writing Assistant</h2>
          </div>
          <button
            onClick={handleClose}
            className={`p-1.5 rounded-md transition-colors ${isDark ? 'text-slate-500 hover:text-white hover:bg-slate-800' : 'text-gray-400 hover:text-gray-900 hover:bg-gray-100'}`}
            data-testid="writing-assistant-close"
            aria-label="Close assistant"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Mode tabs */}
        <div className={`grid grid-cols-3 border-b flex-shrink-0 ${border}`}>
          {[
            { id: 'tweak', label: 'Tweak', icon: Wand2 },
            { id: 'new', label: 'New Page', icon: FilePlus2 },
            { id: 'chat', label: 'Chat', icon: MessageSquare },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              className={`flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors border-b-2 ${
                mode === id ? 'border-[#00A1B2] text-[#00A1B2]' : `border-transparent ${textMuted} hover:${text}`
              }`}
              data-testid={`assistant-mode-${id}`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {mode === 'tweak' && (
            <TweakMode
              content={content}
              selection={selection}
              onApplyContent={onApplyContent}
              onApplySelection={onApplySelection}
              isDark={isDark}
            />
          )}
          {mode === 'new' && (
            <NewPageMode
              navGroups={navGroups}
              articlesCount={articlesCount}
              onDraftNewPage={onDraftNewPage}
              onClose={handleClose}
              isDark={isDark}
            />
          )}
          {mode === 'chat' && <ChatMode content={content} isDark={isDark} />}
        </div>
      </div>
    </>
  );
};

// ===================================================================
// Tweak mode
// ===================================================================
const TweakMode = ({ content, selection, onApplyContent, onApplySelection, isDark }) => {
  const [instruction, setInstruction] = useState('');
  const [proposal, setProposal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const text = isDark ? 'text-white' : 'text-gray-900';
  const textMuted = isDark ? 'text-slate-400' : 'text-gray-500';
  const border = isDark ? 'border-slate-800' : 'border-gray-200';
  const chip = isDark ? 'bg-slate-800/80 text-slate-300' : 'bg-gray-100 text-gray-700';
  const inputClass = `w-full px-3 py-2 rounded-lg text-sm border transition-colors focus:outline-none resize-none ${
    isDark ? 'bg-slate-800/80 border-slate-700 text-white placeholder:text-slate-600 focus:border-[#00A1B2]' : 'bg-white border-gray-300 text-gray-900 placeholder:text-gray-400 focus:border-[#00A1B2]'
  }`;

  const targetLabel = selection?.text
    ? `Selected text (${selection.text.length} chars)`
    : 'Whole document';

  const run = useCallback(async (instr) => {
    const trimmed = (instr || '').trim();
    if (!trimmed) return;
    setLoading(true);
    setError('');
    setProposal(null);
    try {
      const data = await postJSON('/api/assistant/tweak', {
        instruction: trimmed,
        markdown: content || '',
        selection: selection?.text || null,
      });
      setProposal(data.markdown || '');
    } catch (e) {
      setError(
        e.status === 503 ? 'The AI assistant isn\'t configured on this server yet.'
          : e.status === 401 ? 'Your session expired — refresh the page and sign in again.'
          : e.message || 'Could not reach the assistant.'
      );
    } finally {
      setLoading(false);
    }
  }, [content, selection]);

  const accept = () => {
    if (proposal === null) return;
    if (selection?.text) {
      onApplySelection(proposal, selection.start, selection.end);
    } else {
      onApplyContent(proposal);
    }
    setProposal(null);
    setInstruction('');
  };

  return (
    <div className="p-4 space-y-4">
      <div>
        <div className={`text-xs uppercase tracking-wider font-semibold mb-1.5 ${textMuted}`}>Target</div>
        <div className={`px-3 py-2 rounded-md text-xs ${chip}`} data-testid="tweak-target">{targetLabel}</div>
      </div>

      <div>
        <div className={`text-xs uppercase tracking-wider font-semibold mb-1.5 ${textMuted}`}>Quick actions</div>
        <div className="grid grid-cols-2 gap-2">
          {QUICK_TWEAKS.map((q) => (
            <button
              key={q.id}
              onClick={() => run(q.instruction)}
              disabled={loading}
              className={`text-left px-3 py-2 text-xs rounded-md border transition-colors disabled:opacity-50 ${
                isDark ? 'bg-slate-800/60 border-slate-700 text-slate-300 hover:border-[#00A1B2] hover:text-white' : 'bg-white border-gray-200 text-gray-700 hover:border-[#00A1B2] hover:text-gray-900'
              }`}
              data-testid={`quick-tweak-${q.id}`}
            >
              {q.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className={`text-xs uppercase tracking-wider font-semibold mb-1.5 ${textMuted}`}>Custom instruction</div>
        <textarea
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          rows={3}
          placeholder="e.g. Rewrite this section in a friendlier tone and add a warning callout about rate limits."
          className={inputClass}
          data-testid="tweak-instruction"
        />
      </div>
      <button
        onClick={() => run(instruction)}
        disabled={loading || !instruction.trim()}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-opacity"
        data-testid="tweak-run"
      >
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
        Apply instruction
      </button>

      {error && (
        <div className="px-3 py-2 text-xs rounded-md flex items-start gap-2 bg-rose-500/10 text-rose-500" data-testid="tweak-error">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {proposal !== null && (
        <div className={`space-y-2 pt-3 border-t ${border}`}>
          <div className={`text-xs uppercase tracking-wider font-semibold ${textMuted}`}>Proposed result</div>
          <pre
            className={`px-3 py-2 max-h-64 overflow-auto text-[11px] font-mono rounded-md whitespace-pre-wrap border ${isDark ? 'bg-black/30 border-slate-800 text-slate-200' : 'bg-gray-50 border-gray-200 text-gray-800'}`}
            data-testid="tweak-proposal"
          >
            {proposal}
          </pre>
          <div className="flex items-center gap-2">
            <button onClick={accept} className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-md" data-testid="tweak-accept">
              <Check className="w-4 h-4" /> Apply
            </button>
            <button onClick={() => setProposal(null)} className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${textMuted} hover:${text}`} data-testid="tweak-discard">
              Discard
            </button>
            <button
              onClick={() => run(instruction || 'Try a different angle while still respecting the same intent.')}
              disabled={loading}
              className={`p-2 rounded-md disabled:opacity-50 transition-colors ${textMuted} hover:${text}`}
              title="Try again"
              data-testid="tweak-retry"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ===================================================================
// New Page mode
// ===================================================================
const NewPageMode = ({ navGroups, articlesCount, onDraftNewPage, onClose, isDark }) => {
  const [title, setTitle] = useState('');
  const [raw, setRaw] = useState('');
  const [style, setStyle] = useState('documentation');
  const [groupKey, setGroupKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [draft, setDraft] = useState(null);

  const text = isDark ? 'text-white' : 'text-gray-900';
  const textMuted = isDark ? 'text-slate-400' : 'text-gray-500';
  const border = isDark ? 'border-slate-800' : 'border-gray-200';
  const inputClass = `w-full px-3 py-2 rounded-lg text-sm border transition-colors focus:outline-none resize-none ${
    isDark ? 'bg-slate-800/80 border-slate-700 text-white placeholder:text-slate-600 focus:border-[#00A1B2]' : 'bg-white border-gray-300 text-gray-900 placeholder:text-gray-400 focus:border-[#00A1B2]'
  }`;

  const groupOptions = useMemo(() => flattenGroupTargets(navGroups, null, null, 0, []), [navGroups]);

  useEffect(() => {
    if (groupOptions.length && !groupKey) setGroupKey(groupOptions[0].key);
  }, [groupOptions, groupKey]);

  const generate = async () => {
    setError('');
    setDraft(null);
    if (!title.trim() || !raw.trim()) {
      setError('Title and raw notes are required.');
      return;
    }
    setLoading(true);
    try {
      const data = await postJSON('/api/assistant/generate', { raw_input: raw, title, style });
      setDraft(data.markdown || '');
    } catch (e) {
      setError(
        e.status === 503 ? 'The AI assistant isn\'t configured on this server yet.' : e.message || 'Generation failed.'
      );
    } finally {
      setLoading(false);
    }
  };

  const useThisDraft = () => {
    const target = groupOptions.find((g) => g.key === groupKey);
    onDraftNewPage({
      title,
      slug: slugify(title),
      content_markdown: draft || '',
      nav_group_key: target?.topKey || groupKey,
      nav_group_label: target?.topLabel || target?.label || '',
      section_key: groupKey,
      section_label: target?.label?.replace(/^—+\s*/, '') || groupKey,
    });
    onClose();
  };

  if (!groupOptions.length) {
    return (
      <div className={`p-6 text-sm ${textMuted}`} data-testid="new-page-no-groups">
        Add a navigation group first (Settings → Navigation) before drafting new pages here.
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      <div>
        <label className={`text-xs uppercase tracking-wider font-semibold mb-1.5 block ${textMuted}`}>Page title</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Webhooks Configuration"
          className={inputClass}
          data-testid="new-page-title"
        />
      </div>

      <div>
        <label className={`text-xs uppercase tracking-wider font-semibold mb-1.5 block ${textMuted}`}>Style</label>
        <div className="grid grid-cols-2 gap-2">
          {STYLES.map((s) => (
            <button
              key={s.id}
              onClick={() => setStyle(s.id)}
              className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                style === s.id
                  ? 'bg-[#00A1B2] text-white border-[#00A1B2]'
                  : `${isDark ? 'bg-slate-800/60 border-slate-700 text-slate-300' : 'bg-white border-gray-200 text-gray-700'} hover:border-[#00A1B2]`
              }`}
              data-testid={`new-page-style-${s.id}`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className={`text-xs uppercase tracking-wider font-semibold mb-1.5 block ${textMuted}`}>Raw notes</label>
        <textarea
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          rows={8}
          placeholder="Paste rough notes, an outline, or bullet points. The assistant turns them into polished Markdown with headings, code blocks, and callouts."
          className={`${inputClass} font-mono`}
          data-testid="new-page-raw"
        />
      </div>

      <div>
        <label className={`text-xs uppercase tracking-wider font-semibold mb-1.5 block ${textMuted}`}>Add to group</label>
        <select
          value={groupKey}
          onChange={(e) => setGroupKey(e.target.value)}
          className={inputClass}
          data-testid="new-page-group"
        >
          {groupOptions.map((g) => (
            <option key={g.key} value={g.key}>{g.label}</option>
          ))}
        </select>
      </div>

      {!draft ? (
        <button
          onClick={generate}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-opacity"
          data-testid="new-page-generate"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          Generate Markdown
        </button>
      ) : (
        <>
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className={`text-xs uppercase tracking-wider font-semibold ${textMuted}`}>Draft (editable)</label>
              <button onClick={generate} disabled={loading} className={`text-[11px] flex items-center gap-1 ${textMuted} hover:${text}`} data-testid="new-page-regen">
                <RotateCcw className="w-3 h-3" /> Regenerate
              </button>
            </div>
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={10}
              className={`${inputClass} font-mono text-xs`}
              data-testid="new-page-draft"
            />
          </div>
          <button
            onClick={useThisDraft}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-md"
            data-testid="new-page-use-draft"
          >
            <ChevronRight className="w-4 h-4" /> Use this draft
          </button>
          <p className={`text-[11px] ${textMuted}`}>
            This opens the draft in a new, unsaved page. Nothing is created until you press Save there —
            same as adding a page from the sidebar.
          </p>
        </>
      )}

      {error && (
        <div className="px-3 py-2 text-xs rounded-md flex items-start gap-2 bg-rose-500/10 text-rose-500" data-testid="new-page-error">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};

// ===================================================================
// Chat mode — free-form Q&A about the current doc
// ===================================================================
const ChatMode = ({ content, isDark }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const text = isDark ? 'text-white' : 'text-gray-900';
  const textMuted = isDark ? 'text-slate-400' : 'text-gray-500';
  const border = isDark ? 'border-slate-800' : 'border-gray-200';
  const bubbleUser = isDark ? 'bg-slate-800 text-white' : 'bg-gray-100 text-gray-900';
  const bubbleAssistant = isDark ? 'bg-transparent border border-slate-800 text-slate-300' : 'bg-transparent border border-gray-200 text-gray-700';
  const inputClass = `flex-1 px-3 py-2 text-sm rounded-md border transition-colors focus:outline-none resize-none ${
    isDark ? 'bg-slate-800/80 border-slate-700 text-white placeholder:text-slate-600 focus:border-[#00A1B2]' : 'bg-white border-gray-300 text-gray-900 placeholder:text-gray-400 focus:border-[#00A1B2]'
  }`;

  const send = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    setMessages((m) => [...m, { role: 'user', text: trimmed }]);
    setInput('');
    setLoading(true);
    try {
      const data = await postJSON('/api/assistant/chat', { message: trimmed, markdown: content || '' });
      setMessages((m) => [...m, { role: 'assistant', text: data.reply || '(no response)' }]);
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', text: e.status === 503 ? 'The AI assistant isn\'t configured on this server yet.' : (e.message || 'Could not reach the assistant.') }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
        {messages.length === 0 && (
          <p className={`text-xs leading-relaxed ${textMuted}`}>
            Ask anything about this page — "Is the structure clear?", "Suggest a better intro paragraph",
            or "Turn this section into a casual tone".
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`rounded-md px-3 py-2 text-sm whitespace-pre-wrap ${m.role === 'user' ? `${bubbleUser} ml-6` : `${bubbleAssistant} mr-6`}`}
            data-testid={`chat-message-${m.role}-${i}`}
          >
            {m.text}
          </div>
        ))}
        {loading && (
          <div className={`text-xs flex items-center gap-2 ${textMuted}`}>
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Thinking…
          </div>
        )}
      </div>
      <div className={`p-3 border-t flex-shrink-0 ${border}`}>
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); send(); } }}
            rows={2}
            placeholder="Ask the assistant… (⌘/Ctrl+Enter to send)"
            className={inputClass}
            data-testid="chat-input"
          />
          <button
            onClick={send}
            disabled={!input.trim() || loading}
            className="px-3 py-2 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white rounded-md transition-opacity"
            data-testid="chat-send"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
};

export default WritingAssistant;
