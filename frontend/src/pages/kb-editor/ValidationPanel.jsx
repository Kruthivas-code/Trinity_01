/**
 * ValidationPanel — "Validate" action (Phase 7 of the help-doc-v3 port).
 *
 * Wires lib/mdx/validation.js (previously an orphaned utility — nothing
 * called it) into the editor. Same dropdown-button shape as AnchorsMenu.jsx
 * (Phase 4): a toolbar button with a live badge count, opening a small
 * panel that lists findings. There's no separate "run" step needed — the
 * check re-runs (via useMemo) on every keystroke against the current
 * article/link/redirect state, so the badge is always live; the button
 * just opens the list. This is a linting aid, not an enforcement gate:
 * findings NEVER block Save (see KBEditor.jsx's handleSave), matching
 * help-doc-v3's own non-blocking intent for this module.
 *
 * Props:
 *   article    — current editor form (title/slug/description/
 *                content_markdown/published, i.e. the same object
 *                validateDocument reads)
 *   documents  — known articles for internal-link checking (KBEditor's
 *                `articles` state — GET /admin/articles's list)
 *   redirects  — public-data's `redirects` list ({from_slug,to_slug}[]),
 *                for redirect-aware (warning, not error) link checking
 *   theme      — kb-editor EDITOR_THEMES entry
 */
import { useState, useMemo, useRef, useEffect } from 'react';
import { ShieldCheck, AlertTriangle, XCircle, X } from 'lucide-react';
import { validateDocument } from '../../lib/mdx/validation';

export const ValidationPanel = ({ article, documents, redirects, theme }) => {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef(null);

  const result = useMemo(
    () => validateDocument(article || {}, { documents: documents || [], redirects: redirects || [] }),
    [article, documents, redirects]
  );
  const { errors, warnings } = result;
  const issueCount = errors.length + warnings.length;

  useEffect(() => {
    const onDown = (e) => {
      if (!open) return;
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  const badgeClass = errors.length > 0
    ? 'bg-rose-500/20 text-rose-500'
    : warnings.length > 0
      ? 'bg-amber-500/20 text-amber-600 dark:text-amber-300'
      : `${theme.inputBg} ${theme.textMuted}`;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
          open ? 'bg-[#00A1B2] text-white' : `${theme.textMuted} ${theme.hoverText} ${theme.hover}`
        }`}
        title="Validate this page (links, components, required fields)"
        data-testid="validate-toggle"
      >
        {errors.length > 0
          ? <XCircle className="w-4 h-4" />
          : warnings.length > 0
            ? <AlertTriangle className="w-4 h-4" />
            : <ShieldCheck className="w-4 h-4" />}
        <span className="hidden sm:inline">Validate</span>
        {issueCount > 0 && (
          <span className={`ml-0.5 px-1.5 py-0.5 text-[10px] font-bold rounded-full ${open ? 'bg-white/20 text-white' : badgeClass}`}>
            {issueCount}
          </span>
        )}
      </button>

      {open && (
        <div
          className={`absolute right-0 mt-2 w-[380px] max-h-[70vh] rounded-xl shadow-2xl overflow-hidden z-50 flex flex-col border ${theme.dropdownBorder} ${theme.dropdownBg}`}
          style={theme.dropdownBgStyle}
          data-testid="validation-dropdown"
        >
          <div className={`px-4 py-3 border-b ${theme.border} flex items-center justify-between`}>
            <div>
              <p className={`text-[10px] uppercase tracking-wide font-semibold ${theme.textSecondary}`}>Page validation</p>
              <p className={`text-sm font-semibold mt-0.5 ${theme.text}`}>
                {issueCount === 0 ? 'No issues found' : `${errors.length} error${errors.length === 1 ? '' : 's'}, ${warnings.length} warning${warnings.length === 1 ? '' : 's'}`}
              </p>
            </div>
            <button type="button" onClick={() => setOpen(false)} className={`p-1 rounded ${theme.textMuted} ${theme.hoverText}`} aria-label="Close">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            {issueCount === 0 ? (
              <div className="px-4 py-8 text-center">
                <ShieldCheck className={`w-6 h-6 mx-auto mb-2 text-emerald-500`} />
                <p className={`text-sm ${theme.textMuted}`}>Title, slug, links and components all look good.</p>
              </div>
            ) : (
              <ul className={`divide-y ${theme.id === 'dark' ? 'divide-slate-800' : 'divide-gray-100'}`}>
                {[...errors, ...warnings].map((f, i) => (
                  <li key={`${f.type}-${i}`} className="flex items-start gap-2 px-4 py-2.5">
                    {f.severity === 'error'
                      ? <XCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-rose-500" />
                      : <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-500" />}
                    <p className={`text-sm ${theme.text}`}>{f.message}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className={`px-4 py-2 border-t ${theme.border}`}>
            <p className={`text-[11px] ${theme.textSecondary}`}>
              Advisory only — issues here never block Save.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ValidationPanel;
