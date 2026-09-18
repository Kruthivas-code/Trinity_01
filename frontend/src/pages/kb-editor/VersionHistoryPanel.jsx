/**
 * VersionHistoryPanel — save/restore named content snapshots for the
 * current article (Phase 2 of the help-doc-v3 port).
 *
 * Slides in from the right, over the editor's main content area, opened
 * from the header's "History" button (KBEditor.jsx) — the closest thing
 * this editor has to a toolbar action, since the standalone
 * EditorToolbar.jsx component isn't wired into the editor at all.
 *
 * Versions are explicit, user-named snapshots (matches help-doc-v3's own
 * VersionHistoryPanel.jsx / server.py exactly — a version is NOT created
 * automatically on every save). Restoring one auto-saves a backup snapshot
 * of the current content first, then overwrites the live article's content
 * fields only (title/description/body/icon/sidebar title/keywords/tags) —
 * slug, nav position and publish state are left untouched.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  History, Clock, RotateCcw, Trash2, Plus, X,
  Check, AlertCircle, Loader2, Eye, FileText,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export const VersionHistoryPanel = ({ slug, articleTitle, onClose, onRestore, isDark }) => {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newLabel, setNewLabel] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [previewContent, setPreviewContent] = useState(null);
  const [message, setMessage] = useState(null);
  const [restoringId, setRestoringId] = useState(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => { requestAnimationFrame(() => setVisible(true)); }, []);

  const handleClose = useCallback(() => {
    setVisible(false);
    setTimeout(onClose, 200);
  }, [onClose]);

  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') handleClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [handleClose]);

  const loadVersions = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/kb/admin/articles/${slug}/versions`, { credentials: 'include' });
      if (!res.ok) throw new Error('Failed to load');
      const data = await res.json();
      setVersions(data.versions || []);
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to load version history' });
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => { loadVersions(); }, [loadVersions]);

  const createVersion = async () => {
    setCreating(true);
    try {
      const res = await fetch(`${API}/api/kb/admin/articles/${slug}/versions`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        credentials: 'include', body: JSON.stringify({ label: newLabel.trim() || null }),
      });
      if (!res.ok) throw new Error('Save failed');
      setMessage({ type: 'success', text: 'Version saved' });
      setNewLabel('');
      setShowCreateForm(false);
      loadVersions();
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to save version' });
    } finally {
      setCreating(false);
    }
  };

  const restoreVersion = async (version) => {
    if (!window.confirm(`Restore "${version.label}"? The current content will be overwritten (an automatic backup is saved first).`)) return;
    setRestoringId(version.id);
    try {
      const res = await fetch(`${API}/api/kb/admin/articles/${slug}/versions/${version.id}/restore`, {
        method: 'POST', credentials: 'include',
      });
      if (!res.ok) throw new Error('Restore failed');
      const data = await res.json();
      setMessage({ type: 'success', text: 'Article restored' });
      onRestore && onRestore(data.article);
      loadVersions(); // reload to show the new auto-backup
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to restore version' });
    } finally {
      setRestoringId(null);
    }
  };

  const deleteVersion = async (version) => {
    if (!window.confirm('Delete this saved version? This cannot be undone.')) return;
    try {
      const res = await fetch(`${API}/api/kb/admin/articles/${slug}/versions/${version.id}`, {
        method: 'DELETE', credentials: 'include',
      });
      if (!res.ok) throw new Error('Delete failed');
      setVersions((prev) => prev.filter((v) => v.id !== version.id));
      if (selectedVersion?.id === version.id) { setSelectedVersion(null); setPreviewContent(null); }
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to delete version' });
    }
  };

  const previewVersion = async (version) => {
    if (selectedVersion?.id === version.id) { setSelectedVersion(null); setPreviewContent(null); return; }
    setSelectedVersion(version);
    try {
      const res = await fetch(`${API}/api/kb/admin/articles/${slug}/versions/${version.id}`, { credentials: 'include' });
      if (!res.ok) throw new Error('Failed to load');
      const data = await res.json();
      setPreviewContent(data.snapshot?.content_markdown || '');
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to load version preview' });
    }
  };

  const formatDate = (iso) => {
    try {
      return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch { return iso; }
  };

  const formatRelativeTime = (iso) => {
    try {
      const date = new Date(iso);
      const diffMs = Date.now() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays < 7) return `${diffDays}d ago`;
      return formatDate(iso);
    } catch { return iso; }
  };

  const panelBg = isDark ? 'bg-[#111111] border-slate-800' : 'bg-white border-gray-200';
  const textMuted = isDark ? 'text-slate-400' : 'text-gray-500';
  const text = isDark ? 'text-white' : 'text-gray-900';
  const border = isDark ? 'border-slate-800' : 'border-gray-200';
  const inputClass = `w-full px-3 py-2 rounded-lg text-sm border transition-colors focus:outline-none ${
    isDark ? 'bg-slate-800/80 border-slate-700 text-white placeholder:text-slate-600 focus:border-[#00A1B2]' : 'bg-white border-gray-300 text-gray-900 placeholder:text-gray-400 focus:border-[#00A1B2]'
  }`;

  return (
    <>
      {/* Backdrop — covers the main content area only, below the header */}
      <div
        className={`fixed z-40 transition-opacity duration-200 ${visible ? 'opacity-100' : 'opacity-0'}`}
        style={{ top: '56px', left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.25)' }}
        onClick={handleClose}
        data-testid="version-history-backdrop"
      />

      {/* Slide-in panel */}
      <div
        className={`fixed z-50 flex flex-col border-l shadow-2xl transition-transform duration-200 ease-out ${panelBg} ${visible ? 'translate-x-0' : 'translate-x-full'}`}
        style={{ top: '56px', right: 0, bottom: 0, width: '420px', maxWidth: '100vw' }}
        data-testid="version-history-panel"
      >
        {/* Header */}
        <div className={`flex items-center justify-between px-4 py-3 border-b flex-shrink-0 ${border}`}>
          <div className="flex items-center gap-2">
            <History className={`w-4 h-4 ${text}`} />
            <h2 className={`font-semibold text-sm ${text}`}>Version History</h2>
          </div>
          <button onClick={handleClose} className={`p-1.5 rounded-md transition-colors ${isDark ? 'text-slate-500 hover:text-white hover:bg-slate-800' : 'text-gray-400 hover:text-gray-900 hover:bg-gray-100'}`} data-testid="version-history-close">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Article info */}
        <div className={`px-4 py-2.5 border-b flex-shrink-0 ${border}`}>
          <div className={`flex items-center gap-2 text-sm ${textMuted}`}>
            <FileText className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="truncate">{articleTitle || slug}</span>
          </div>
        </div>

        {/* Message */}
        {message && (
          <div className={`mx-4 mt-3 px-3 py-2 rounded-lg text-sm flex items-center gap-2 flex-shrink-0 ${
            message.type === 'success' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'
          }`}>
            {message.type === 'success' ? <Check className="w-4 h-4 flex-shrink-0" /> : <AlertCircle className="w-4 h-4 flex-shrink-0" />}
            <span className="flex-1">{message.text}</span>
            <button onClick={() => setMessage(null)}><X className="w-3.5 h-3.5" /></button>
          </div>
        )}

        {/* Create version */}
        <div className={`px-4 py-3 border-b flex-shrink-0 ${border}`}>
          {showCreateForm ? (
            <div className="space-y-2">
              <input
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                placeholder="Version label (optional, e.g. 'Before rewrite')"
                className={inputClass}
                onKeyDown={(e) => e.key === 'Enter' && createVersion()}
                autoFocus
                data-testid="version-label-input"
              />
              <div className="flex gap-2">
                <button onClick={createVersion} disabled={creating}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 text-white text-sm rounded-md transition-opacity"
                  data-testid="version-save-btn">
                  {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />} Save
                </button>
                <button onClick={() => { setShowCreateForm(false); setNewLabel(''); }}
                  className={`px-3 py-1.5 text-sm rounded-md transition-colors ${textMuted} hover:${text}`}>
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button onClick={() => setShowCreateForm(true)}
              className={`w-full flex items-center justify-center gap-2 px-3 py-2 border border-dashed rounded-lg transition-colors ${border} ${textMuted} hover:${text}`}
              data-testid="version-create-btn">
              <Plus className="w-4 h-4" /> Save current version
            </button>
          )}
        </div>

        {/* Version list */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex justify-center py-8"><Loader2 className={`w-5 h-5 animate-spin ${textMuted}`} /></div>
          ) : versions.length === 0 ? (
            <div className="px-4 py-10 text-center">
              <History className={`w-10 h-10 mx-auto mb-3 opacity-40 ${textMuted}`} />
              <p className={`text-sm ${textMuted}`}>No versions yet</p>
              <p className={`text-xs mt-1 opacity-70 ${textMuted}`}>Save a version to snapshot the current state</p>
            </div>
          ) : (
            <div className={`divide-y ${isDark ? 'divide-slate-800/60' : 'divide-gray-100'}`}>
              {versions.map((version) => (
                <div key={version.id} className={`p-3 ${isDark ? 'hover:bg-slate-800/30' : 'hover:bg-gray-50'} transition-colors`} data-testid={`version-item-${version.id}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <h4 className={`text-sm font-medium truncate ${text}`}>{version.label}</h4>
                        {version.label?.startsWith('Auto-backup') && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-amber-500/15 text-amber-500 rounded flex-shrink-0">auto</span>
                        )}
                      </div>
                      <div className={`flex items-center gap-1.5 mt-0.5 text-xs ${textMuted}`}>
                        <Clock className="w-3 h-3" />
                        <span title={formatDate(version.created_at)}>{formatRelativeTime(version.created_at)}</span>
                        {version.created_by_name && <span>· {version.created_by_name}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-0.5 flex-shrink-0">
                      <button onClick={() => previewVersion(version)} title="Preview"
                        className={`p-1.5 rounded-md transition-colors ${textMuted} hover:${text} ${isDark ? 'hover:bg-slate-700' : 'hover:bg-gray-200'}`}
                        data-testid={`version-preview-${version.id}`}>
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => restoreVersion(version)} disabled={restoringId === version.id} title="Restore"
                        className="p-1.5 rounded-md text-emerald-500 hover:bg-emerald-500/10 transition-colors disabled:opacity-50"
                        data-testid={`version-restore-${version.id}`}>
                        {restoringId === version.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
                      </button>
                      <button onClick={() => deleteVersion(version)} title="Delete"
                        className="p-1.5 rounded-md text-rose-500 hover:bg-rose-500/10 transition-colors"
                        data-testid={`version-delete-${version.id}`}>
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  {selectedVersion?.id === version.id && previewContent !== null && (
                    <div className={`mt-2 p-2.5 rounded-lg border max-h-40 overflow-auto ${isDark ? 'bg-black/30 border-slate-800' : 'bg-gray-50 border-gray-200'}`}>
                      <pre className={`text-xs whitespace-pre-wrap font-mono ${textMuted}`}>
                        {previewContent.slice(0, 500)}{previewContent.length > 500 && '...'}
                      </pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className={`px-4 py-2.5 border-t flex-shrink-0 ${border} ${isDark ? 'bg-white/[0.02]' : 'bg-gray-50'}`}>
          <p className={`text-xs ${textMuted}`}>Tip: save a version before a big rewrite so you can always go back.</p>
        </div>
      </div>
    </>
  );
};

export default VersionHistoryPanel;
