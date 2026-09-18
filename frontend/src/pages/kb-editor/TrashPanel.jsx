/**
 * TrashPanel — soft-deleted KB pages (Phase 2 of the help-doc-v3 port).
 * Lives inside UnifiedSettings as its own tab, next to Navigation (trash and
 * nav are closely related — a restored page reappears in the nav tree).
 * Owner-only, matching the backend's GET/POST/DELETE /api/kb/admin/trash...
 * gating — UnifiedSettings only renders this tab's content for an owner.
 */
import { useState, useEffect, useCallback } from 'react';
import { Trash2, RotateCcw, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export const TrashPanel = ({ theme, onRestored }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/kb/admin/trash`, { credentials: 'include' });
      const data = await res.json();
      setItems(data.trash || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const restore = async (it) => {
    setBusy(it.slug);
    try {
      const res = await fetch(`${API}/api/kb/admin/trash/${it.slug}/restore`, { method: 'POST', credentials: 'include' });
      if (!res.ok) throw new Error('Restore failed');
      const data = await res.json();
      setItems((prev) => prev.filter((x) => x.slug !== it.slug));
      if (data.fell_back_to_top_level) {
        alert(`"${it.title || it.slug}" was restored, but its original section no longer exists — it was placed at the top level of the navigation tree. Move it into place from Navigation.`);
      }
      onRestored && onRestored();
    } catch (e) {
      alert('Failed to restore: ' + e.message);
    } finally {
      setBusy(null);
    }
  };

  const purge = async (it) => {
    if (!window.confirm(`Permanently delete "${it.title || it.slug}"? This cannot be undone.`)) return;
    setBusy(it.slug);
    try {
      const res = await fetch(`${API}/api/kb/admin/trash/${it.slug}`, { method: 'DELETE', credentials: 'include' });
      if (!res.ok) throw new Error('Delete failed');
      setItems((prev) => prev.filter((x) => x.slug !== it.slug));
    } catch (e) {
      alert('Failed to permanently delete: ' + e.message);
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="w-5 h-5 animate-spin text-[#00A1B2]" /></div>;

  return (
    <div className="space-y-3" data-testid="trash-panel">
      <p className={`text-xs ${theme.textSecondary}`}>Deleted pages are kept for 90 days, then removed automatically.</p>
      {items.length === 0 ? (
        <p className={`text-sm ${theme.textMuted}`} data-testid="trash-empty">Trash is empty.</p>
      ) : (
        <div className="space-y-2">
          {items.map((it) => (
            <div key={it.slug} className={`border ${theme.border} rounded-lg p-3`} data-testid={`trash-item-${it.slug}`}>
              <div className={`text-sm font-medium truncate ${theme.text}`}>{it.title || it.slug}</div>
              <div className={`text-xs mt-0.5 ${theme.textMuted}`}>
                Deleted by {it.deleted_by_name || it.deleted_by || 'someone'} · {it.days_left} day{it.days_left === 1 ? '' : 's'} until permanent deletion
              </div>
              <div className="flex gap-2 mt-2">
                <button
                  onClick={() => restore(it)}
                  disabled={busy === it.slug}
                  className="text-xs flex items-center gap-1 px-2 py-1 rounded-md border border-emerald-400/40 text-emerald-600 hover:bg-emerald-500/10 disabled:opacity-50 transition-colors"
                  data-testid={`trash-restore-${it.slug}`}
                >
                  {busy === it.slug ? <Loader2 className="w-3 h-3 animate-spin" /> : <RotateCcw className="w-3 h-3" />} Restore
                </button>
                <button
                  onClick={() => purge(it)}
                  disabled={busy === it.slug}
                  className="text-xs flex items-center gap-1 px-2 py-1 rounded-md border border-rose-400/40 text-rose-600 hover:bg-rose-500/10 disabled:opacity-50 transition-colors"
                  data-testid={`trash-purge-${it.slug}`}
                >
                  <Trash2 className="w-3 h-3" /> Delete forever
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TrashPanel;
