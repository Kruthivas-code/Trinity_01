import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { DocContent } from '@/components/docs/DocContent';
import { useTheme } from '@/contexts/ThemeContext';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft, MessageSquarePlus, CheckCircle2, RotateCcw, X, Sun, Moon,
  ChevronLeft, ChevronRight, ListChecks, Circle, Pencil, History,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const VERDICTS = ['Looks correct', 'Needs small edits', 'Wrong info', 'More info needed', 'Outdated', 'Tone / clarity', 'Other'];
const ACTION_LABEL = {
  assigned: 'assigned', delegated: 'delegated', commented: 'commented on',
  replied: 'replied on', resolved: 'resolved a comment', published: 'published',
  unpublished: 'unpublished', verdict: 'set a verdict',
};

async function api(path, opts = {}) {
  const res = await fetch(`${API}/api/review${path}`, {
    credentials: 'include',
    headers: opts.body ? { 'Content-Type': 'application/json' } : undefined,
    ...opts,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

// Lightweight @mention textarea: type "@" then filter people the app knows.
function MentionInput({ value, onChange, options, placeholder, rows = 3, testid, autoFocus }) {
  const ref = useRef(null);
  const [menu, setMenu] = useState(null);
  const handle = (e) => {
    onChange(e.target.value);
    const upto = e.target.value.slice(0, e.target.selectionStart);
    const m = upto.match(/@([\w.\-+@]*)$/);
    setMenu(m ? { q: m[1].toLowerCase() } : null);
  };
  const pick = (email) => {
    const pos = ref.current.selectionStart;
    const before = value.slice(0, pos).replace(/@([\w.\-+@]*)$/, '@' + email + ' ');
    onChange(before + value.slice(pos));
    setMenu(null); setTimeout(() => ref.current && ref.current.focus(), 0);
  };
  const matches = menu ? options.filter((o) => o.includes(menu.q)).slice(0, 6) : [];
  return (
    <div className="relative">
      <textarea ref={ref} value={value} onChange={handle} placeholder={placeholder} rows={rows} autoFocus={autoFocus} data-testid={testid} className="w-full border border-border bg-background rounded-md p-2 text-sm" />
      {menu && matches.length > 0 && (
        <div className="absolute z-50 left-2 bottom-full mb-1 bg-popover border border-border rounded-md shadow-lg max-h-40 overflow-y-auto" data-testid="mention-menu">
          {matches.map((m) => (
            <button key={m} type="button" onMouseDown={(e) => { e.preventDefault(); pick(m); }} className="block w-full text-left px-3 py-1.5 text-xs hover:bg-muted whitespace-nowrap" data-testid={`mention-opt-${m}`}>{m}</button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ReviewPage({ user }) {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';
  const [doc, setDoc] = useState(null);
  const [comments, setComments] = useState([]);
  const [reviewOn, setReviewOn] = useState(true);
  const [sel, setSel] = useState(null);
  const [composer, setComposer] = useState(null);
  const [body, setBody] = useState('');
  const [loading, setLoading] = useState(true);
  const [verdict, setVerdict] = useState('');
  const [queue, setQueue] = useState([]);
  const [reviewedSet, setReviewedSet] = useState(new Set());
  const [verdictBy, setVerdictBy] = useState(null);
  const [verdictHistory, setVerdictHistory] = useState(null);
  const [pendingNav, setPendingNav] = useState(null);
  const [allPages, setAllPages] = useState([]);
  const [onlyAssigned, setOnlyAssigned] = useState(true);
  const [knownEmails, setKnownEmails] = useState([]);
  const [replyTo, setReplyTo] = useState(null);
  const [replyBody, setReplyBody] = useState('');
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState([]);

  const isOwner = user?.role === 'admin';
  const myEmail = (user?.email || '').toLowerCase();

  const loadComments = useCallback(async () => {
    const cm = await api(`/comments?doc_slug=${encodeURIComponent(slug)}`);
    setComments(cm.comments);
  }, [slug]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [listing, article] = await Promise.all([
          fetch(`${API}/api/kb/admin/articles`, { credentials: 'include' }).then((r) => r.json()),
          fetch(`${API}/api/kb/admin/articles/${slug}`, { credentials: 'include' }).then((r) => (r.ok ? r.json() : null)),
        ]);
        setDoc(article);

        const pages = (listing.articles || [])
          .slice()
          .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
          .map((a) => ({ slug: a.slug, title: a.title, tab: a.nav_group_key, section: a.section_key }));
        setAllPages(pages);

        api('/known-emails').then((r) => setKnownEmails(r.emails || [])).catch(() => {});
        await loadComments();

        try {
          const asg = await api('/assignments');
          const mine = (asg.assignments || []).filter((a) => (a.assignee_email || '').toLowerCase() === myEmail);
          const seen = new Set(); const q = [];
          mine.forEach((a) => (a.slugs || []).forEach((s) => { if (!seen.has(s)) { seen.add(s); q.push(s); } }));
          setQueue(q);
        } catch (e) { /* no queue */ }

        try {
          const vd = await api('/verdicts');
          const reviewed = new Set((vd.verdicts || []).filter((v) => v.verdict === 'Looks correct').map((v) => v.doc_slug));
          setReviewedSet(reviewed);
          const pageV = (vd.verdicts || []).find((v) => v.doc_slug === slug);
          setVerdict(pageV?.verdict || '');
          setVerdictBy(pageV ? { name: pageV.reviewer_name || pageV.reviewer_email, at: pageV.updated_at } : null);
        } catch (e) { /* no verdict yet */ }
      } catch (e) {
        toast.error('Failed to load page');
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  const assignedSet = useMemo(() => new Set(queue), [queue]);
  const hasAssignments = assignedSet.size > 0;
  const showOnlyAssigned = hasAssignments && onlyAssigned;
  const visiblePages = useMemo(
    () => (showOnlyAssigned ? allPages.filter((p) => assignedSet.has(p.slug)) : allPages),
    [allPages, assignedSet, showOnlyAssigned]
  );
  const idx = visiblePages.findIndex((p) => p.slug === slug);
  const prevSlug = idx > 0 ? visiblePages[idx - 1].slug : null;
  const nextSlug = idx >= 0 && idx < visiblePages.length - 1 ? visiblePages[idx + 1].slug : null;
  const reviewedCount = useMemo(() => queue.filter((s) => reviewedSet.has(s)).length, [queue, reviewedSet]);
  const showNav = allPages.length > 0;
  const reviewerEmail = (searchParams.get('reviewer') || myEmail || '');

  const buildUrl = (targetSlug) => `/dashboard/review/${targetSlug}${reviewerEmail ? `?reviewer=${encodeURIComponent(reviewerEmail)}` : ''}`;
  const guardedNavigate = (url) => { if (verdict) { navigate(url); return; } setPendingNav({ url }); };
  const goToSlug = (targetSlug) => { if (targetSlug) guardedNavigate(buildUrl(targetSlug)); };

  const onMouseUp = () => {
    if (!reviewOn) return;
    const s = window.getSelection();
    const text = s?.toString().trim();
    if (!text || text.length < 2) { setSel(null); return; }
    const rect = s.getRangeAt(0).getBoundingClientRect();
    setSel({ text, x: rect.left + rect.width / 2, y: rect.top + window.scrollY - 6 });
  };

  const startComment = () => { setComposer({ anchor_text: sel.text }); setSel(null); setBody(''); };

  const scrollToAnchor = (text) => {
    if (!text) return;
    const root = document.querySelector('[data-testid="review-content"]');
    if (!root) return;
    const needle = text.trim().slice(0, 60);
    const probe = needle.slice(0, 30);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      const at = node.nodeValue.indexOf(probe);
      if (at !== -1) {
        try {
          const range = document.createRange();
          range.setStart(node, at);
          range.setEnd(node, Math.min(node.nodeValue.length, at + needle.length));
          const s = window.getSelection(); s.removeAllRanges(); s.addRange(range);
        } catch (e) { /* ignore */ }
        node.parentElement?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
    }
    root.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  useEffect(() => {
    const f = searchParams.get('focus');
    if (f && doc && !loading) {
      const t = setTimeout(() => scrollToAnchor(f), 700);
      return () => clearTimeout(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc, loading]);

  const mentionsIn = (text) => knownEmails.filter((e) => new RegExp('@' + e.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?!\\w)', 'i').test(text));
  const renderBody = (text) => (text || '').split(/(@[\w.\-+@]+)/g).map((part, i) => (part.startsWith('@') && knownEmails.includes(part.slice(1).toLowerCase())
    ? <span key={i} className="text-primary font-medium">{part}</span> : part));

  const submitComment = async () => {
    if (!body.trim()) return;
    try {
      const data = await api('/comments', { method: 'POST', body: JSON.stringify({ doc_slug: slug, body: body.trim(), anchor_text: composer?.anchor_text || null, mentions: mentionsIn(body) }) });
      setComments((prev) => [...prev, data]);
      setComposer(null); setBody('');
      toast.success('Comment added');
    } catch (e) { toast.error(e.message || 'Failed to add comment'); }
  };

  const submitTopLevel = async () => {
    const b = replyBody.trim();
    if (!b || replyTo !== '__new__') return;
    try {
      const data = await api('/comments', { method: 'POST', body: JSON.stringify({ doc_slug: slug, body: b, mentions: mentionsIn(b) }) });
      setComments((p) => [...p, data]);
      setReplyTo(null); setReplyBody('');
      toast.success('Comment added');
    } catch (e) { toast.error(e.message || 'Failed to add comment'); }
  };

  const submitReply = async (parentId) => {
    const b = replyBody.trim();
    if (!b) return;
    try {
      const data = await api('/comments', { method: 'POST', body: JSON.stringify({ doc_slug: slug, body: b, parent_id: parentId, mentions: mentionsIn(b) }) });
      setComments((prev) => [...prev, data]);
      setReplyTo(null); setReplyBody('');
      toast.success('Reply added');
    } catch (e) { toast.error(e.message || 'Failed to reply'); }
  };

  const resolve = async (c, r) => {
    try {
      await api(`/comments/${c.id}/${r ? 'resolve' : 'reopen'}`, { method: 'POST' });
      setComments((prev) => prev.map((x) => (x.id === c.id ? { ...x, resolved: r } : x)));
    } catch (e) { toast.error('Action failed'); }
  };

  const saveVerdict = async (v) => {
    setVerdict(v);
    setReviewedSet((prev) => { const n = new Set(prev); if (v === 'Looks correct') n.add(slug); else n.delete(slug); return n; });
    setVerdictBy({ name: user?.name || user?.email || 'You', at: new Date().toISOString() });
    try {
      await api('/verdicts', { method: 'POST', body: JSON.stringify({ doc_slug: slug, verdict: v }) });
      toast.success('Verdict saved');
      if (verdictHistory !== null) loadHistory();
    } catch (e) { toast.error(e.message || 'Failed to save verdict'); }
  };

  const loadHistory = async () => {
    try {
      const r = await api(`/verdict-history?doc_slug=${encodeURIComponent(slug)}`);
      setVerdictHistory(r.history || []);
    } catch (e) { setVerdictHistory([]); }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-background text-muted-foreground">Loading…</div>;
  if (!doc) return <div className="min-h-screen flex items-center justify-center bg-background text-muted-foreground">Page not found.</div>;

  return (
    <div className="min-h-screen bg-background text-foreground" data-testid="review-page">
      <header className="sticky top-0 z-40 h-14 px-6 flex items-center justify-between border-b border-border bg-background/90 backdrop-blur">
        <div className="flex items-center gap-3 min-w-0">
          <button onClick={() => guardedNavigate('/dashboard/review')} className="p-1.5 hover:bg-muted rounded-md" data-testid="reviewpage-back"><ArrowLeft className="w-4 h-4" /></button>
          <span className="font-semibold truncate">{doc.title}</span>
          <Badge variant="outline" className="whitespace-nowrap text-amber-700 dark:text-amber-400 border-amber-300 dark:border-amber-500/40">Review mode</Badge>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          {showNav && (
            <div className="hidden sm:flex items-center gap-1">
              <button onClick={() => goToSlug(prevSlug)} disabled={!prevSlug} className="p-1.5 rounded-md hover:bg-muted disabled:opacity-30 disabled:hover:bg-transparent" data-testid="prev-page-btn" aria-label="Previous assigned page"><ChevronLeft className="w-4 h-4" /></button>
              <span className="text-xs text-muted-foreground tabular-nums">{idx >= 0 ? idx + 1 : '–'} / {visiblePages.length}</span>
              <button onClick={() => goToSlug(nextSlug)} disabled={!nextSlug} className="p-1.5 rounded-md hover:bg-muted disabled:opacity-30 disabled:hover:bg-transparent" data-testid="next-page-btn" aria-label="Next assigned page"><ChevronRight className="w-4 h-4" /></button>
            </div>
          )}
          <button onClick={toggleTheme} className="p-1.5 rounded-md hover:bg-muted text-muted-foreground" data-testid="theme-toggle" aria-label="Toggle theme">
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <Button size="sm" variant="outline" className="hidden sm:flex gap-1.5" onClick={() => navigate(`/dashboard/kb-editor/${slug}`)} data-testid="reviewpage-open-editor">
            <Pencil className="w-3.5 h-3.5" /> Edit in KB editor
          </Button>
          <Button size="sm" variant="outline" className="hidden sm:flex gap-1.5" onClick={() => { setShowHistory(true); api(`/activity/page/${slug}`).then((r) => setHistory(r.activity || [])).catch(() => {}); }} data-testid="reviewpage-history-btn">
            <History className="w-3.5 h-3.5" /> History
          </Button>
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none" data-testid="review-toggle">
            <span className="text-muted-foreground hidden sm:inline">Review</span>
            <button onClick={() => setReviewOn((v) => !v)} aria-pressed={reviewOn} className={`relative w-10 h-5 rounded-full transition-colors ${reviewOn ? 'bg-primary' : 'bg-muted'}`} data-testid="review-toggle-btn">
              <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${reviewOn ? 'translate-x-5' : ''}`} />
            </button>
          </label>
        </div>
      </header>

      <div className={`max-w-6xl mx-auto grid grid-cols-1 gap-8 px-6 py-8 ${showNav ? 'lg:grid-cols-[240px_1fr_300px]' : 'lg:grid-cols-[1fr_320px]'}`}>
        {showNav && (
          <nav className="lg:sticky lg:top-20 h-fit order-first" data-testid="review-sidenav">
            {hasAssignments && (
              <div className="mb-3" data-testid="review-progress">
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="flex items-center gap-1.5 font-semibold text-muted-foreground"><ListChecks className="w-3.5 h-3.5" /> Your reviews</span>
                  <span className="text-muted-foreground tabular-nums" data-testid="review-progress-count">{reviewedCount} of {queue.length} reviewed</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                  <div className="h-full bg-primary transition-all" style={{ width: `${queue.length ? (reviewedCount / queue.length) * 100 : 0}%` }} data-testid="review-progress-bar" />
                </div>
              </div>
            )}
            {hasAssignments && (
              <label className="flex items-center justify-between gap-2 text-xs mb-2 px-1 cursor-pointer select-none" data-testid="only-assigned-toggle">
                <span className="text-muted-foreground">Only my assigned pages</span>
                <button onClick={() => setOnlyAssigned((v) => !v)} aria-pressed={onlyAssigned} className={`relative w-9 h-5 rounded-full transition-colors flex-shrink-0 ${onlyAssigned ? 'bg-primary' : 'bg-muted'}`} data-testid="only-assigned-toggle-btn">
                  <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${onlyAssigned ? 'translate-x-4' : ''}`} />
                </button>
              </label>
            )}
            <div className="space-y-0.5 max-h-[70vh] overflow-y-auto pr-1">
              {visiblePages.map((p, i) => {
                const s = p.slug;
                const done = reviewedSet.has(s);
                const active = s === slug;
                const isAssigned = assignedSet.has(s);
                const showTab = i === 0 || visiblePages[i - 1].tab !== p.tab;
                return (
                  <div key={s}>
                    {showTab && <div className="px-2 pt-3 pb-1 text-[10px] uppercase tracking-wide text-muted-foreground/70">{p.tab}</div>}
                    <button
                      onClick={() => goToSlug(s)}
                      data-testid={`sidenav-item-${s}`}
                      className={`w-full text-left flex items-start gap-2 px-2.5 py-1.5 rounded-md text-sm transition-colors ${active ? 'bg-primary/10 text-primary font-medium' : 'text-muted-foreground hover:bg-muted'}`}
                    >
                      {done
                        ? <CheckCircle2 className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-emerald-500" />
                        : <Circle className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${isAssigned ? 'text-muted-foreground' : 'text-muted-foreground/40'}`} />}
                      <span className="line-clamp-2">{p.title}</span>
                    </button>
                  </div>
                );
              })}
            </div>
          </nav>
        )}

        <article onMouseUp={onMouseUp} className={`min-w-0 ${reviewOn ? 'cursor-text' : ''}`} data-testid="review-content">
          <h1 className="text-3xl font-bold mb-4">{doc.title}</h1>
          <div className="doc-content">
            <DocContent content={doc.content_markdown?.replace(new RegExp(`^#\\s*${(doc.title || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\n+`, 'i'), '') || doc.content_markdown} />
          </div>
          {showNav && (
            <div className="mt-10 pt-6 border-t border-border flex items-center justify-between">
              <button onClick={() => goToSlug(prevSlug)} disabled={!prevSlug} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground disabled:opacity-30" data-testid="prev-page-footer"><ChevronLeft className="w-4 h-4" /> Previous</button>
              <button onClick={() => goToSlug(nextSlug)} disabled={!nextSlug} className="flex items-center gap-1.5 text-sm font-medium text-primary hover:opacity-80 disabled:opacity-30" data-testid="next-page-footer">Next page <ChevronRight className="w-4 h-4" /></button>
            </div>
          )}
        </article>

        <aside className="lg:sticky lg:top-20 h-fit">
          <div className="mb-5">
            <h3 className="text-sm font-semibold text-muted-foreground mb-2">Verdict{!verdict && <span className="ml-1 text-amber-600 dark:text-amber-400">· not set</span>}</h3>
            <div className="flex flex-wrap gap-1.5">
              {VERDICTS.map((v) => (
                <button key={v} onClick={() => saveVerdict(v)} className={`text-xs px-2 py-1 rounded-full border transition-colors ${verdict === v ? 'bg-primary text-primary-foreground border-primary' : 'border-border text-muted-foreground hover:bg-muted'}`} data-testid={`reviewpage-verdict-${v.replace(/\W+/g, '-')}`}>{v}</button>
              ))}
            </div>
            {verdict && verdictBy && (
              <p className="mt-2 text-xs text-muted-foreground" data-testid="verdict-set-by">
                Set by <span className="text-foreground font-medium">{verdictBy.name}</span>{verdictBy.at ? ` · ${new Date(verdictBy.at).toLocaleString()}` : ''}
              </p>
            )}
            <button onClick={() => (verdictHistory === null ? loadHistory() : setVerdictHistory(null))} className="mt-2 text-xs text-primary hover:underline" data-testid="verdict-history-toggle">
              {verdictHistory === null ? 'View verdict history' : 'Hide history'}
            </button>
            {verdictHistory !== null && (
              <div className="mt-2 rounded-md border border-border divide-y divide-border max-h-48 overflow-y-auto" data-testid="verdict-history">
                {verdictHistory.length === 0 ? (
                  <p className="text-xs text-muted-foreground px-2.5 py-2">No verdict changes recorded.</p>
                ) : verdictHistory.map((h, i) => (
                  <div key={i} className="px-2.5 py-1.5 text-xs">
                    <Badge variant="secondary" className="font-medium">{h.meta?.verdict || '—'}</Badge>
                    <span className="text-muted-foreground"> — {h.actor_name || h.actor_email}</span>
                    {h.created_at && <span className="text-muted-foreground"> · {new Date(h.created_at).toLocaleString()}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
          <h3 className="text-sm font-semibold text-muted-foreground mb-3">Comments ({comments.length})</h3>
          {reviewOn && <p className="text-xs text-muted-foreground mb-3">Select any text in the page to pin a comment to it.</p>}
          <div className="space-y-2 max-h-[calc(100vh-16rem)] overflow-y-auto pr-1" data-testid="review-comments-rail">
            {comments.filter((c) => !c.parent_id).length === 0 && <p className="text-xs text-muted-foreground">No comments yet.</p>}
            {comments.filter((c) => !c.parent_id).map((c) => {
              const replies = comments.filter((r) => r.parent_id === c.id);
              return (
                <div key={c.id} onClick={() => c.anchor_text && scrollToAnchor(c.anchor_text)} className={`rounded-lg border p-3 text-sm ${c.anchor_text ? 'cursor-pointer hover:border-primary/50' : ''} ${c.resolved ? 'border-emerald-300/50 bg-emerald-50/40 dark:border-emerald-500/30 dark:bg-emerald-500/10' : 'border-border'}`} data-testid={`review-comment-${c.id}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-muted-foreground">{c.author_name || c.author_email}</span>
                    {c.resolved
                      ? <button onClick={(e) => { e.stopPropagation(); resolve(c, false); }} className="text-[11px] flex items-center gap-1 text-muted-foreground" data-testid={`reviewpage-reopen-${c.id}`}><RotateCcw className="w-3 h-3" /> Reopen</button>
                      : <button onClick={(e) => { e.stopPropagation(); resolve(c, true); }} className="text-[11px] flex items-center gap-1 text-emerald-600 dark:text-emerald-400" data-testid={`reviewpage-resolve-${c.id}`}><CheckCircle2 className="w-3 h-3" /> Resolve</button>}
                  </div>
                  {c.anchor_text && <div className="text-xs italic text-muted-foreground border-l-2 border-primary/50 pl-2 mb-1">"{c.anchor_text}"</div>}
                  <p className="text-foreground/90 whitespace-pre-wrap">{renderBody(c.body)}</p>

                  {replies.length > 0 && (
                    <div className="mt-2 pl-3 border-l-2 border-border space-y-2">
                      {replies.map((r) => (
                        <div key={r.id} data-testid={`review-reply-${r.id}`}>
                          <span className="text-xs font-medium text-muted-foreground">{r.author_name || r.author_email}</span>
                          <p className="text-foreground/90 whitespace-pre-wrap">{renderBody(r.body)}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {replyTo === c.id ? (
                    <div className="mt-2" onClick={(e) => e.stopPropagation()}>
                      <MentionInput value={replyBody} onChange={setReplyBody} options={knownEmails} rows={2} autoFocus placeholder="Reply…  use @ to mention" testid={`reply-input-${c.id}`} />
                      <div className="flex justify-end gap-2 mt-1">
                        <button onClick={() => { setReplyTo(null); setReplyBody(''); }} className="text-[11px] px-2 py-1 text-muted-foreground hover:bg-muted rounded">Cancel</button>
                        <button onClick={() => submitReply(c.id)} disabled={!replyBody.trim()} className="text-[11px] px-2.5 py-1 bg-primary text-primary-foreground rounded disabled:opacity-50" data-testid={`reply-submit-${c.id}`}>Reply</button>
                      </div>
                    </div>
                  ) : (
                    <button onClick={(e) => { e.stopPropagation(); setReplyTo(c.id); setReplyBody(''); }} className="mt-1.5 text-[11px] text-muted-foreground hover:text-primary" data-testid={`reply-btn-${c.id}`}>Reply</button>
                  )}
                </div>
              );
            })}
          </div>
          <div className="mt-3" data-testid="new-comment-box">
            <MentionInput value={replyTo === '__new__' ? replyBody : ''} onChange={(v) => { setReplyTo('__new__'); setReplyBody(v); }} options={knownEmails} rows={2} placeholder="Add a comment…  use @ to mention" testid="new-comment-input" />
            <div className="flex justify-end mt-1">
              <button onClick={submitTopLevel} disabled={replyTo !== '__new__' || !replyBody.trim()} className="text-xs px-3 py-1.5 bg-primary text-primary-foreground rounded-md disabled:opacity-50" data-testid="new-comment-submit">Comment</button>
            </div>
          </div>
        </aside>
      </div>

      {sel && reviewOn && (
        <button onClick={startComment} style={{ position: 'absolute', left: sel.x, top: sel.y, transform: 'translate(-50%,-100%)' }} className="z-50 flex items-center gap-1.5 px-3 py-1.5 bg-primary hover:opacity-90 text-primary-foreground text-xs font-medium rounded-full shadow-lg" data-testid="selection-comment-btn">
          <MessageSquarePlus className="w-3.5 h-3.5" /> Comment
        </button>
      )}

      {composer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setComposer(null)}>
          <div className="w-full max-w-md bg-card rounded-xl shadow-xl p-5 border border-border" onClick={(e) => e.stopPropagation()} data-testid="review-composer">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold">Pin a comment</h3>
              <button onClick={() => setComposer(null)} className="p-1 hover:bg-muted rounded"><X className="w-4 h-4" /></button>
            </div>
            {composer.anchor_text && <div className="text-xs italic text-muted-foreground border-l-2 border-primary/50 pl-2 mb-3 line-clamp-3">"{composer.anchor_text}"</div>}
            <MentionInput value={body} onChange={setBody} options={knownEmails} rows={4} autoFocus placeholder="Your comment…  use @ to mention" testid="composer-input" />
            <div className="flex justify-end gap-2 mt-3">
              <Button variant="ghost" size="sm" onClick={() => setComposer(null)}>Cancel</Button>
              <Button size="sm" onClick={submitComment} disabled={!body.trim()} data-testid="composer-submit">Add comment</Button>
            </div>
          </div>
        </div>
      )}

      {pendingNav && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4" onClick={() => setPendingNav(null)}>
          <div className="w-full max-w-sm bg-card rounded-xl shadow-xl p-5 border border-border" onClick={(e) => e.stopPropagation()} data-testid="verdict-nudge">
            <h3 className="font-semibold mb-1">No verdict yet</h3>
            <p className="text-sm text-muted-foreground mb-4">You haven't left a verdict for <span className="font-medium text-foreground">{doc.title}</span>. Leave one now, or come back to it later?</p>
            <div className="flex flex-col gap-2">
              <Button className="w-full" onClick={() => { setPendingNav(null); window.scrollTo({ top: 0, behavior: 'smooth' }); }} data-testid="nudge-stay">Stay and leave a verdict</Button>
              <Button variant="outline" className="w-full" onClick={() => { const url = pendingNav.url; setPendingNav(null); navigate(url); }} data-testid="nudge-review-later">Review later, continue</Button>
            </div>
          </div>
        </div>
      )}
      {showHistory && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onClick={() => setShowHistory(false)} data-testid="page-history-overlay">
          <div className="w-[380px] h-full bg-card border-l border-border shadow-xl p-5 overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="page-history-panel">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold flex items-center gap-2"><History className="w-4 h-4" /> Page history</h3>
              <button onClick={() => setShowHistory(false)} className="p-1 hover:bg-muted rounded" data-testid="page-history-close"><X className="w-4 h-4" /></button>
            </div>
            {history.length === 0 ? (
              <p className="text-sm text-muted-foreground" data-testid="page-history-empty">No history for this page yet.</p>
            ) : (
              <div className="relative pl-4 border-l border-border space-y-4">
                {history.map((ev) => (
                  <div key={ev.id} className="relative" data-testid={`page-history-${ev.id}`}>
                    <span className="absolute -left-[21px] top-1.5 w-2 h-2 rounded-full bg-primary" />
                    <div className="text-sm text-foreground/90">
                      <span className="font-medium">{ev.actor_name || ev.actor_email}</span> {ACTION_LABEL[ev.action] || ev.action}
                      {ev.meta?.verdict ? <span className="text-muted-foreground"> — "{ev.meta.verdict}"</span> : null}
                      {ev.meta?.to ? <span className="text-muted-foreground"> ({ev.meta.from} → {ev.meta.to})</span> : null}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">{new Date(ev.created_at).toLocaleString()}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
