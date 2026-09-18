import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useTheme } from '@/contexts/ThemeContext';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Inbox, ClipboardList, BarChart3, CheckCircle2, RotateCcw, Trash2,
  ArrowLeft, Loader2, UserPlus, Sun, Moon, Users, History, Download, ExternalLink,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

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

const StatusPill = ({ s }) => {
  const map = {
    published: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400',
    unpublished: 'bg-muted text-muted-foreground',
    in_review: 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400',
    done: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400',
  };
  const label = { published: 'Published', unpublished: 'Unpublished', in_review: 'In review', done: 'Done' };
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${map[s] || 'bg-muted text-muted-foreground'}`}>{label[s] || s}</span>;
};

const ACTION_LABEL = {
  assigned: 'assigned', delegated: 'delegated', commented: 'commented on', replied: 'replied on',
  resolved: 'resolved a comment on', published: 'published', unpublished: 'unpublished', verdict: 'set a verdict on',
};

function csvDownload(filename, head, rows) {
  const csv = [head, ...rows].map((row) => row.map((c) => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url);
}

export default function ReviewConsole({ user }) {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';
  const isOwner = user?.role === 'admin';
  const myEmail = (user?.email || '').toLowerCase();

  const [tab, setTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [articles, setArticles] = useState([]);
  const [navGroups, setNavGroups] = useState([]);
  const [progress, setProgress] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [inbox, setInbox] = useState({ comments: [], unread: 0, open: 0, total: 0 });
  const [knownEmails, setKnownEmails] = useState([]);
  const [mis, setMis] = useState(null);
  const [misLoading, setMisLoading] = useState(false);
  const [activity, setActivity] = useState([]);
  const [activityPerson, setActivityPerson] = useState('');

  // assignment creation form
  const [scopeType, setScopeType] = useState('page');
  const [scopeId, setScopeId] = useState('');
  const [assigneeEmail, setAssigneeEmail] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [creating, setCreating] = useState(false);

  // delegate form (reviewer moving their own queue, or owner moving anyone's)
  const [delegateFrom, setDelegateFrom] = useState(isOwner ? '' : myEmail);
  const [delegateTo, setDelegateTo] = useState('');
  const [delegating, setDelegating] = useState(false);

  const loadCore = useCallback(async () => {
    setLoading(true);
    try {
      const [kb, asg] = await Promise.all([
        fetch(`${API}/api/kb/admin/articles`, { credentials: 'include' }).then((r) => r.json()),
        api('/assignments'),
      ]);
      setArticles(kb.articles || []);
      setNavGroups(kb.groups || []);
      setAssignments(asg.assignments || []);
      api('/known-emails').then((r) => setKnownEmails(r.emails || [])).catch(() => {});
      if (isOwner) {
        api('/progress').then(setProgress).catch(() => {});
        api('/inbox').then(setInbox).catch(() => {});
      }
    } catch (e) {
      toast.error('Failed to load review data');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOwner]);

  useEffect(() => { loadCore(); }, [loadCore]);

  const loadMis = useCallback(async () => {
    setMisLoading(true);
    try { setMis(await api('/mis')); }
    catch (e) { toast.error('Failed to load MIS'); }
    finally { setMisLoading(false); }
  }, []);
  useEffect(() => { if (tab === 'mis' && !mis) loadMis(); }, [tab, mis, loadMis]);

  const loadActivity = useCallback(async () => {
    try {
      const q = activityPerson ? `?person=${encodeURIComponent(activityPerson)}` : '';
      const r = await api(`/activity${q}`);
      setActivity(r.activity || []);
    } catch (e) { /* not owner */ }
  }, [activityPerson]);
  useEffect(() => { if (tab === 'activity' && isOwner) loadActivity(); }, [tab, isOwner, loadActivity]);

  const articleTitle = (slug) => articles.find((a) => a.slug === slug)?.title || slug;

  const createAssignment = async () => {
    if (!scopeId || !assigneeEmail.trim()) { toast.error('Pick a page/section and an assignee'); return; }
    setCreating(true);
    try {
      await api('/assignments', {
        method: 'POST',
        body: JSON.stringify({ scope_type: scopeType, scope_id: scopeId, scope_label: scopeType === 'page' ? articleTitle(scopeId) : scopeId, assignee_email: assigneeEmail.trim(), due_date: dueDate || null }),
      });
      toast.success('Assigned');
      setAssigneeEmail(''); setDueDate('');
      const asg = await api('/assignments');
      setAssignments(asg.assignments || []);
    } catch (e) { toast.error(e.message || 'Failed to assign'); }
    finally { setCreating(false); }
  };

  const updateStatus = async (a, status) => {
    try {
      await api(`/assignments/${a.id}`, { method: 'PUT', body: JSON.stringify({ status }) });
      setAssignments((prev) => prev.map((x) => (x.id === a.id ? { ...x, status } : x)));
    } catch (e) { toast.error(e.message || 'Failed to update'); }
  };

  const deleteAssignment = async (a) => {
    try {
      await api(`/assignments/${a.id}`, { method: 'DELETE' });
      setAssignments((prev) => prev.filter((x) => x.id !== a.id));
    } catch (e) { toast.error(e.message || 'Failed to delete'); }
  };

  const runDelegateBulk = async () => {
    if (!delegateFrom.trim() || !delegateTo.trim()) { toast.error('Both emails are required'); return; }
    setDelegating(true);
    try {
      const r = await api('/assignments/delegate-bulk', { method: 'POST', body: JSON.stringify({ from_email: delegateFrom.trim(), to_email: delegateTo.trim() }) });
      toast.success(`Reassigned ${r.reassigned} page(s) to ${r.to_email}`);
      setDelegateTo('');
      const asg = await api('/assignments');
      setAssignments(asg.assignments || []);
    } catch (e) { toast.error(e.message || 'Failed to delegate'); }
    finally { setDelegating(false); }
  };

  const publishToggle = async (slug, publish) => {
    try {
      await api(`/articles/${slug}/${publish ? 'publish' : 'unpublish'}`, { method: 'POST' });
      toast.success(publish ? 'Published' : 'Unpublished');
      loadCore();
    } catch (e) { toast.error(e.message || 'Action failed'); }
  };

  const markRead = async (c) => {
    try { await api(`/comments/${c.id}/read`, { method: 'POST' }); } catch (e) { /* noop */ }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-background text-muted-foreground">Loading review console…</div>;

  const myAssignments = assignments.filter((a) => (a.assignee_email || '').toLowerCase() === myEmail);
  // "group" scope assignment is tab::section (nav_group_key::section_key) —
  // matches review.py's flatten_scope_slugs, which reads those two flat
  // fields (immediate parent group) off kb_articles. The nav tree can nest
  // deeper than this now, but assigning review to an arbitrary middle-depth
  // subtree is Phase 1 work; this still covers every group exactly one level
  // under a top-level group, same as before the nav tree became recursive.
  const groupOptions = [];
  navGroups.forEach((g) => (g.children || [])
    .filter((c) => c.type === 'group')
    .forEach((s) => groupOptions.push({ value: `${g.key}::${s.key}`, label: `${g.label} / ${s.label}` })));

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 h-14 px-6 flex items-center justify-between border-b border-border bg-background/90 backdrop-blur">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="p-1.5 hover:bg-muted rounded-md" data-testid="review-console-back"><ArrowLeft className="w-4 h-4" /></button>
          <span className="font-semibold">Content Review</span>
          {isOwner ? <Badge variant="secondary">Admin</Badge> : <Badge variant="outline">Reviewer</Badge>}
        </div>
        <button onClick={toggleTheme} className="p-1.5 rounded-md hover:bg-muted text-muted-foreground" aria-label="Toggle theme">
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="overview" data-testid="tab-overview"><BarChart3 className="w-3.5 h-3.5 mr-1.5" /> Overview</TabsTrigger>
            <TabsTrigger value="assignments" data-testid="tab-assignments"><ClipboardList className="w-3.5 h-3.5 mr-1.5" /> Assignments</TabsTrigger>
            {isOwner && <TabsTrigger value="inbox" data-testid="tab-inbox"><Inbox className="w-3.5 h-3.5 mr-1.5" /> Inbox {inbox.open > 0 && <Badge variant="destructive" className="ml-1.5">{inbox.open}</Badge>}</TabsTrigger>}
            <TabsTrigger value="mis" data-testid="tab-mis"><Users className="w-3.5 h-3.5 mr-1.5" /> MIS</TabsTrigger>
            {isOwner && <TabsTrigger value="activity" data-testid="tab-activity"><History className="w-3.5 h-3.5 mr-1.5" /> Activity</TabsTrigger>}
          </TabsList>

          {/* ---------------- Overview ---------------- */}
          <TabsContent value="overview" className="mt-6 space-y-6">
            {isOwner && progress && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="glass rounded-xl p-4 border border-border/60">
                  <div className="text-2xl font-bold">{progress.total_assignments}</div>
                  <div className="text-xs text-muted-foreground">Total assignments</div>
                </div>
                <div className="glass rounded-xl p-4 border border-border/60">
                  <div className="text-2xl font-bold">{progress.assignments_by_status?.done || 0}</div>
                  <div className="text-xs text-muted-foreground">Marked done</div>
                </div>
                <div className="glass rounded-xl p-4 border border-border/60">
                  <div className="text-2xl font-bold">{progress.docs_by_status?.published || 0}</div>
                  <div className="text-xs text-muted-foreground">Published pages</div>
                </div>
                <div className="glass rounded-xl p-4 border border-border/60">
                  <div className="text-2xl font-bold">{progress.docs_by_status?.unpublished || 0}</div>
                  <div className="text-xs text-muted-foreground">Unpublished pages</div>
                </div>
              </div>
            )}
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3">Your assigned pages ({myAssignments.reduce((n, a) => n + (a.slugs?.length || 0), 0)})</h3>
              {myAssignments.length === 0 ? (
                <p className="text-sm text-muted-foreground">No pages assigned to you yet.</p>
              ) : (
                <div className="space-y-2">
                  {myAssignments.flatMap((a) => a.slugs.map((s) => ({ ...a, slug: s }))).map((row) => (
                    <div key={row.id + row.slug} className="flex items-center justify-between rounded-lg border border-border p-3">
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{articleTitle(row.slug)}</div>
                        <div className="text-xs text-muted-foreground">{row.due_date ? `Due ${row.due_date}` : 'No due date'}</div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <StatusPill s={row.status} />
                        <Button size="sm" variant="outline" onClick={() => navigate(`/dashboard/review/${row.slug}`)} data-testid={`overview-review-${row.slug}`}>Review <ExternalLink className="w-3.5 h-3.5 ml-1.5" /></Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          {/* ---------------- Assignments ---------------- */}
          <TabsContent value="assignments" className="mt-6 space-y-8">
            {isOwner && (
              <div className="glass rounded-2xl p-6 border border-border/60">
                <h3 className="text-sm font-semibold mb-4 flex items-center gap-2"><UserPlus className="w-4 h-4" /> Assign a page for review</h3>
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Scope</label>
                    <select value={scopeType} onChange={(e) => { setScopeType(e.target.value); setScopeId(''); }} className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm">
                      <option value="page">Single page</option>
                      <option value="group">Section</option>
                      <option value="tab">Whole category</option>
                    </select>
                  </div>
                  <div className="sm:col-span-1">
                    <label className="text-xs text-muted-foreground block mb-1">{scopeType === 'page' ? 'Page' : scopeType === 'group' ? 'Section' : 'Category'}</label>
                    {scopeType === 'page' && (
                      <select value={scopeId} onChange={(e) => setScopeId(e.target.value)} className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm">
                        <option value="">Select a page…</option>
                        {articles.map((a) => <option key={a.slug} value={a.slug}>{a.title}</option>)}
                      </select>
                    )}
                    {scopeType === 'group' && (
                      <select value={scopeId} onChange={(e) => setScopeId(e.target.value)} className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm">
                        <option value="">Select a section…</option>
                        {groupOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </select>
                    )}
                    {scopeType === 'tab' && (
                      <select value={scopeId} onChange={(e) => setScopeId(e.target.value)} className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm">
                        <option value="">Select a category…</option>
                        {navGroups.map((g) => <option key={g.key} value={g.key}>{g.label}</option>)}
                      </select>
                    )}
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Assignee email</label>
                    <Input list="known-emails" value={assigneeEmail} onChange={(e) => setAssigneeEmail(e.target.value)} placeholder="reviewer@company.com" />
                    <datalist id="known-emails">{knownEmails.map((e) => <option key={e} value={e} />)}</datalist>
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Due date (optional)</label>
                    <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
                  </div>
                </div>
                <Button className="mt-4" onClick={createAssignment} disabled={creating} data-testid="create-assignment-btn">
                  {creating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <UserPlus className="w-4 h-4 mr-2" />} Assign
                </Button>
              </div>
            )}

            <div>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3">{isOwner ? 'All assignments' : 'Your assignments'}</h3>
              {assignments.length === 0 ? (
                <p className="text-sm text-muted-foreground">No assignments yet.</p>
              ) : (
                <div className="space-y-2">
                  {assignments.map((a) => (
                    <div key={a.id} className="flex items-center justify-between rounded-lg border border-border p-3 gap-3" data-testid={`assignment-row-${a.id}`}>
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{a.scope_label} <span className="text-muted-foreground font-normal">({a.slugs.length} page{a.slugs.length !== 1 ? 's' : ''})</span></div>
                        <div className="text-xs text-muted-foreground">→ {a.assignee_email}{a.delegated_from ? ` (delegated from ${a.delegated_from})` : ''}{a.due_date ? ` · due ${a.due_date}` : ''}</div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <StatusPill s={a.status} />
                        {(isOwner || a.assignee_email === myEmail) && a.status !== 'done' && (
                          <Button size="sm" variant="outline" onClick={() => updateStatus(a, 'done')} data-testid={`assignment-done-btn-${a.id}`}>Mark done</Button>
                        )}
                        {isOwner && (
                          <button data-testid={`assignment-delete-btn-${a.id}`} onClick={() => deleteAssignment(a)} className="p-1.5 text-rose-500 hover:bg-rose-500/10 rounded"><Trash2 className="w-4 h-4" /></button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {isOwner && (
              <div>
                <h3 className="text-sm font-semibold text-muted-foreground mb-3">Pages</h3>
                <div className="space-y-2">
                  {articles.map((a) => (
                    <div key={a.slug} className="flex items-center justify-between rounded-lg border border-border p-3 gap-3" data-testid={`page-row-${a.slug}`}>
                      <div className="min-w-0 text-sm font-medium truncate">{a.title}</div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <StatusPill s={a.published ? 'published' : 'unpublished'} />
                        <Button size="sm" variant="outline" onClick={() => navigate(`/dashboard/review/${a.slug}`)}>Review</Button>
                        <Button size="sm" variant={a.published ? 'outline' : 'default'} onClick={() => publishToggle(a.slug, !a.published)} data-testid={`publish-toggle-${a.slug}`}>
                          {a.published ? 'Unpublish' : 'Publish'}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="glass rounded-2xl p-6 border border-border/60">
              <h3 className="text-sm font-semibold mb-4">Delegate a queue</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">From</label>
                  <Input value={delegateFrom} onChange={(e) => setDelegateFrom(e.target.value)} placeholder="current-reviewer@company.com" disabled={!isOwner} />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">To</label>
                  <Input list="known-emails" value={delegateTo} onChange={(e) => setDelegateTo(e.target.value)} placeholder="new-reviewer@company.com" />
                </div>
                <Button onClick={runDelegateBulk} disabled={delegating} variant="outline">{delegating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null} Delegate all</Button>
              </div>
            </div>
          </TabsContent>

          {/* ---------------- Inbox ---------------- */}
          {isOwner && (
            <TabsContent value="inbox" className="mt-6">
              <div className="flex items-center gap-4 mb-4 text-sm text-muted-foreground">
                <span>{inbox.total} total</span><span>·</span><span>{inbox.open} open</span><span>·</span><span>{inbox.unread} unread</span>
              </div>
              <div className="space-y-2">
                {inbox.comments.length === 0 && <p className="text-sm text-muted-foreground">No comments yet.</p>}
                {inbox.comments.map((c) => (
                  <div key={c.id} className={`rounded-lg border p-3 text-sm cursor-pointer ${c.resolved ? 'border-emerald-300/50 bg-emerald-50/40 dark:border-emerald-500/30 dark:bg-emerald-500/10' : 'border-border'}`} onClick={() => { markRead(c); navigate(`/dashboard/review/${c.doc_slug}${c.anchor_text ? `?focus=${encodeURIComponent(c.anchor_text.slice(0, 40))}` : ''}`); }}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium">{articleTitle(c.doc_slug)}</span>
                      {c.resolved ? <span className="text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> Resolved</span> : <span className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1"><RotateCcw className="w-3.5 h-3.5" /> Open</span>}
                    </div>
                    <div className="text-xs text-muted-foreground mb-1">{c.author_name || c.author_email}</div>
                    <p className="text-foreground/90 line-clamp-2">{c.body}</p>
                  </div>
                ))}
              </div>
            </TabsContent>
          )}

          {/* ---------------- MIS ---------------- */}
          <TabsContent value="mis" className="mt-6 space-y-6">
            {misLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
            {mis && (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="glass rounded-xl p-4 border border-border/60"><div className="text-2xl font-bold">{mis.funnel.total_pages}</div><div className="text-xs text-muted-foreground">Total pages</div></div>
                  <div className="glass rounded-xl p-4 border border-border/60"><div className="text-2xl font-bold">{mis.funnel.unassigned}</div><div className="text-xs text-muted-foreground">Unassigned</div></div>
                  <div className="glass rounded-xl p-4 border border-border/60"><div className="text-2xl font-bold">{mis.funnel.done}</div><div className="text-xs text-muted-foreground">Reviewed & correct</div></div>
                  <div className="glass rounded-xl p-4 border border-border/60"><div className="text-2xl font-bold">{mis.funnel.published}</div><div className="text-xs text-muted-foreground">Published</div></div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-muted-foreground">Reviewers</h3>
                    <Button size="sm" variant="outline" onClick={() => csvDownload('mis-reviewers.csv', ['Reviewer', 'Assigned', 'Done', '% done', 'Comments raised', 'Comments resolved', 'Overdue'], mis.reviewers.map((r) => [r.email, r.assigned, r.done, r.pct_done, r.comments_made, r.comments_resolved, r.overdue]))}><Download className="w-3.5 h-3.5 mr-1.5" /> Export CSV</Button>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead><tr className="text-left text-xs text-muted-foreground border-b border-border">
                        <th className="py-2 pr-4">Reviewer</th><th className="py-2 pr-4">Assigned</th><th className="py-2 pr-4">Done</th><th className="py-2 pr-4">% done</th><th className="py-2 pr-4">Comments</th><th className="py-2 pr-4">Overdue</th>
                      </tr></thead>
                      <tbody>
                        {mis.reviewers.map((r) => (
                          <tr key={r.email} className="border-b border-border/60">
                            <td className="py-2 pr-4">{r.email}</td><td className="py-2 pr-4">{r.assigned}</td><td className="py-2 pr-4">{r.done}</td>
                            <td className="py-2 pr-4">{r.pct_done}%</td><td className="py-2 pr-4">{r.comments_made} made / {r.comments_resolved} resolved</td>
                            <td className="py-2 pr-4">{r.overdue > 0 ? <span className="text-rose-500 font-medium">{r.overdue}</span> : '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-muted-foreground">Images missing alt text ({mis.images_missing_alt.length})</h3>
                    {mis.images_missing_alt.length > 0 && <Button size="sm" variant="outline" onClick={() => csvDownload('mis-images-missing-alt.csv', ['Page', 'Slug', 'Published', 'Missing count'], mis.images_missing_alt.map((p) => [p.title, p.slug, p.published, p.count]))}><Download className="w-3.5 h-3.5 mr-1.5" /> Export CSV</Button>}
                  </div>
                  {mis.images_missing_alt.length === 0 ? <p className="text-sm text-muted-foreground">None — nice.</p> : (
                    <div className="space-y-1.5">
                      {mis.images_missing_alt.map((p) => (
                        <div key={p.slug} className="flex items-center justify-between rounded-lg border border-border p-2.5 text-sm">
                          <span className="truncate">{p.title}</span>
                          <Badge variant="destructive">{p.count} missing</Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-muted-foreground mb-3">Comment health (pages with activity)</h3>
                  {mis.comments_health.length === 0 ? <p className="text-sm text-muted-foreground">No comment activity yet.</p> : (
                    <div className="space-y-1.5">
                      {mis.comments_health.map((p) => (
                        <div key={p.slug} className="flex items-center justify-between rounded-lg border border-border p-2.5 text-sm">
                          <span className="truncate">{p.title}{p.hot && <Badge variant="destructive" className="ml-2">Hot</Badge>}</span>
                          <span className="text-muted-foreground">{p.open} open / {p.resolved} resolved</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </TabsContent>

          {/* ---------------- Activity ---------------- */}
          {isOwner && (
            <TabsContent value="activity" className="mt-6">
              <div className="flex items-center gap-2 mb-4">
                <Input value={activityPerson} onChange={(e) => setActivityPerson(e.target.value)} placeholder="Filter by person's email…" className="max-w-xs" />
                <Button size="sm" variant="outline" onClick={loadActivity}>Filter</Button>
              </div>
              <div className="relative pl-4 border-l border-border space-y-4">
                {activity.length === 0 && <p className="text-sm text-muted-foreground">No activity yet.</p>}
                {activity.map((ev) => (
                  <div key={ev.id} className="relative">
                    <span className="absolute -left-[21px] top-1.5 w-2 h-2 rounded-full bg-primary" />
                    <div className="text-sm text-foreground/90">
                      <span className="font-medium">{ev.actor_name || ev.actor_email}</span> {ACTION_LABEL[ev.action] || ev.action}
                      {ev.doc_title ? <span className="text-muted-foreground"> "{ev.doc_title}"</span> : null}
                      {ev.meta?.verdict ? <span className="text-muted-foreground"> — "{ev.meta.verdict}"</span> : null}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">{new Date(ev.created_at).toLocaleString()}</div>
                  </div>
                ))}
              </div>
            </TabsContent>
          )}
        </Tabs>
      </div>
    </div>
  );
}
