/**
 * PageMetaDialog — Page Meta Dialog with guarded slug-change (Phase 4 of the
 * help-doc-v3 port). Edits title / slug / icon / description for the
 * current article. Title/icon/description save the same way any other
 * content edit does (PUT /api/kb/admin/articles/{slug}, open to any
 * signed-in user — Phase 1 philosophy). A slug change is different: it's
 * owner-gated server side (routes/kb.py's update_article, Phase 4
 * extension) because it rewrites the page's public address AND every other
 * page's internal links to it. This dialog:
 *   1. debounced dry-run preview (GET .../slug-preview) as the user types a
 *      new slug, showing how many other pages/links would be touched
 *   2. requires an explicit "I understand" confirmation checkbox before Save
 *      is enabled for a changed slug
 *   3. sends title/icon/description + the new slug together in ONE PUT
 *      (matches update_article's actual design — one endpoint handles both,
 *      there's no separate change-slug endpoint to keep in sync)
 *
 * Non-owners can still open this dialog and edit title/icon/description
 * (content edit — not gated), but the slug field is read-only for them: the
 * PUT would 403 anyway, so the UI doesn't offer a control that can't work.
 *
 * Wired from PageSettingsSlider.jsx's "Title, slug & icon" button rather
 * than duplicating title/slug inputs there (see that file's comment) —
 * help-doc-v3's own PageMetaDialog is a full page-settings modal including
 * delete; Trinity already has a delete flow in PageSettingsSlider, so this
 * one stays scoped to meta + the guarded slug change.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { X, Loader2, AlertTriangle } from 'lucide-react';
import IconPicker from './components/IconPicker';

const API = process.env.REACT_APP_BACKEND_URL;

export const PageMetaDialog = ({ open, article, isOwner, isDark, onClose, onSaved }) => {
  const [title, setTitle] = useState('');
  const [slug, setSlug] = useState('');
  const [icon, setIcon] = useState('');
  const [description, setDescription] = useState('');
  const [confirmSlug, setConfirmSlug] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [preview, setPreview] = useState(null); // { pages_count, links_count, slug_valid, slug_available }
  const [previewLoading, setPreviewLoading] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (!open || !article) return;
    setTitle(article.title || '');
    setSlug(article.slug || '');
    setIcon(article.icon || '');
    setDescription(article.description || '');
    setConfirmSlug(false);
    setError(null);
    setPreview(null);
  }, [open, article]);

  const slugChanged = !!article && slug.trim() && slug.trim().toLowerCase() !== article.slug;

  // Debounced dry-run preview — only fetched while the slug actually
  // differs, and only meaningful for an owner (a non-owner can't submit a
  // slug change anyway, so the field is disabled for them below).
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!open || !isOwner || !slugChanged) { setPreview(null); return; }
    debounceRef.current = setTimeout(async () => {
      setPreviewLoading(true);
      try {
        const res = await fetch(
          `${API}/api/kb/admin/articles/${article.slug}/slug-preview?new_slug=${encodeURIComponent(slug.trim().toLowerCase())}`,
          { credentials: 'include' },
        );
        if (res.ok) setPreview(await res.json());
      } catch (e) { /* preview is best-effort */ }
      setPreviewLoading(false);
    }, 400);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [slug, slugChanged, open, isOwner, article]);

  const slugProblem = slugChanged && preview && !previewLoading
    ? (!preview.slug_valid ? 'Slug must be lowercase letters, numbers and hyphens only.'
      : !preview.slug_available ? 'That slug is already in use.' : null)
    : null;

  const canSave = title.trim().length > 0
    && (!slugChanged || (!slugProblem && confirmSlug))
    && !saving;

  const handleSave = useCallback(async () => {
    if (!canSave || !article) return;
    setSaving(true);
    setError(null);
    try {
      const payload = {
        title: title.trim() || article.title,
        icon: icon || '',
        description: description.trim(),
      };
      if (slugChanged) payload.slug = slug.trim().toLowerCase();
      const res = await fetch(`${API}/api/kb/admin/articles/${article.slug}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Save failed (${res.status})`);
      }
      const updated = await res.json();
      onSaved?.(updated);
      onClose?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }, [canSave, article, title, icon, description, slugChanged, slug, onSaved, onClose]);

  if (!open || !article) return null;

  const panelBg = isDark ? 'bg-[#111111] border-slate-800' : 'bg-white border-gray-200';
  const inputClass = `w-full px-3 py-2.5 rounded-lg text-sm border transition-colors focus:outline-none ${
    isDark ? 'bg-slate-800/80 border-slate-700 text-white placeholder:text-slate-600 focus:border-[#00A1B2]'
           : 'bg-white border-gray-300 text-gray-900 placeholder:text-gray-400 focus:border-[#00A1B2]'
  }`;
  const labelClass = `block text-xs font-medium mb-1.5 ${isDark ? 'text-slate-400' : 'text-gray-500'}`;

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 backdrop-blur-sm" data-testid="page-meta-dialog">
      <div className={`relative w-full max-w-md mx-4 rounded-2xl border shadow-2xl ${panelBg}`}>
        <div className={`flex items-center justify-between px-5 py-4 border-b ${isDark ? 'border-slate-800' : 'border-gray-200'}`}>
          <div>
            <h3 className={`text-sm font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>Page Settings</h3>
            <p className={`text-xs mt-0.5 ${isDark ? 'text-slate-500' : 'text-gray-400'}`}>Title, slug, icon &amp; description</p>
          </div>
          <button onClick={onClose} className={`p-1.5 rounded-lg ${isDark ? 'text-slate-500 hover:text-white hover:bg-slate-800' : 'text-gray-400 hover:text-gray-900 hover:bg-gray-100'}`} data-testid="meta-close-btn">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4 max-h-[70vh] overflow-y-auto">
          <div>
            <label className={labelClass}>Title</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} className={inputClass} data-testid="meta-title-input" />
          </div>

          <div>
            <label className={labelClass}>Icon</label>
            <IconPicker value={icon} onChange={setIcon} isLight={!isDark} />
          </div>

          <div>
            <label className={labelClass}>
              Slug {!isOwner && <span className="font-normal">— owner-only to change</span>}
            </label>
            <input
              value={slug}
              onChange={(e) => { setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-')); setConfirmSlug(false); }}
              disabled={!isOwner}
              className={`${inputClass} font-mono disabled:opacity-60`}
              data-testid="meta-slug-input"
            />
            {slugChanged && isOwner && (
              <div className={`mt-2 rounded-md border p-2.5 ${isDark ? 'border-amber-500/40 bg-amber-500/10' : 'border-amber-300 bg-amber-50'}`} data-testid="slug-change-disclaimer">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                  <p className={`text-[11px] leading-relaxed ${isDark ? 'text-amber-300' : 'text-amber-800'}`}>
                    Changing the slug changes this page&apos;s URL (<code>/docs/{article.slug}</code> → <code>/docs/{slug.trim().toLowerCase()}</code>).
                    A redirect from the old URL will be created automatically, and{' '}
                    {previewLoading ? 'internal links are being checked…' : preview
                      ? `${preview.links_count} internal link${preview.links_count === 1 ? '' : 's'} across ${preview.pages_count} page${preview.pages_count === 1 ? '' : 's'} will be updated`
                      : 'internal links will be updated'} automatically.
                  </p>
                </div>
                {slugProblem ? (
                  <p className="mt-2 text-[11px] font-medium text-rose-500">{slugProblem}</p>
                ) : (
                  <label className={`mt-2 flex items-center gap-2 text-[11px] font-medium cursor-pointer ${isDark ? 'text-amber-200' : 'text-amber-900'}`}>
                    <input type="checkbox" checked={confirmSlug} onChange={(e) => setConfirmSlug(e.target.checked)} data-testid="slug-change-confirm" />
                    I understand — redirect the old URL and update these links
                  </label>
                )}
              </div>
            )}
          </div>

          <div>
            <label className={labelClass}>Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              maxLength={280}
              placeholder="One-sentence summary of the page…"
              className={`${inputClass} resize-none`}
              data-testid="meta-description-input"
            />
          </div>

          {error && <p className="text-xs text-rose-500" data-testid="meta-error">{error}</p>}
        </div>

        <div className={`flex items-center justify-end gap-2 px-5 py-4 border-t ${isDark ? 'border-slate-800' : 'border-gray-200'}`}>
          <button onClick={onClose} className={`px-3 py-1.5 text-sm font-medium rounded-md ${isDark ? 'text-slate-400 hover:text-white hover:bg-slate-800' : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'}`}>
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!canSave}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-white bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 rounded-md transition-opacity"
            data-testid="meta-save-btn"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Save
          </button>
        </div>
      </div>
    </div>
  );
};

export default PageMetaDialog;
