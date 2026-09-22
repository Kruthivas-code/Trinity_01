/**
 * ThemeToggle - small reusable icon button for the docs reader's light/dark
 * switch (Phase 5 of the help-doc-v3 feature port, cosmetic parity item).
 *
 * help-doc-v3's frontend/src/components/ui/theme-toggle.jsx reads/writes a
 * shared React ThemeContext. PublicDocs.jsx doesn't use that context -- it
 * already has its own working, self-contained theme state (`kbTheme`,
 * localStorage-backed, OS-preference-aware; see PublicDocs.jsx's kbTheme
 * state and its effects) that predates this port and has nothing wrong with
 * it functionally. So this component only extracts the *icon button markup*
 * that was inline in PublicDocs.jsx's TopNavigation into its own file --
 * a prop-driven (isDark, onToggle) component rather than a context
 * consumer, since introducing a context for a single call site would be
 * the "touching a lot of call sites for no real benefit" case this phase
 * says to skip.
 */
import { Sun, Moon } from 'lucide-react';

export const ThemeToggle = ({ isDark, onToggle, theme }) => (
  <button
    onClick={onToggle}
    className={`p-2 rounded-lg ${theme.textMuted} ${theme.hoverText} ${theme.hover} transition-colors`}
    data-testid="kb-theme-toggle"
    title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
  >
    {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
  </button>
);

export default ThemeToggle;
