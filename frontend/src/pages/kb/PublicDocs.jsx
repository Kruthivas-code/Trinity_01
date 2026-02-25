/**
 * PublicDocs - Emergent Documentation Site
 * Ported from help.emergent.sh reference
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Search, Menu, X, ChevronDown,
  ExternalLink, Copy, Check,
  ArrowLeft, ArrowRight, Sparkles,
  ThumbsUp, ThumbsDown, Sun, Moon
} from 'lucide-react';
import { DocContent } from '../../components/docs/DocContent';
import { search, initializeSearch } from '../../lib/search';
import './PublicDocs.css';

const API = process.env.REACT_APP_BACKEND_URL;

const THEMES = {
  dark: {
    id: 'dark',
    bg: 'bg-[#0a0a0a]',
    navBg: 'bg-[#0a0a0a]',
    sidebarBg: 'bg-[#0a0a0a]',
    text: 'text-white',
    textMuted: 'text-[#999999]',
    textSecondary: 'text-[#787878]',
    border: 'border-white/10',
    hover: 'hover:bg-white/5',
    activeBg: 'bg-[#00A1B2]',
    activeText: 'text-white',
    activeAccent: 'text-[#00A1B2]',
    inputBg: 'bg-white/5 border border-white/10',
    tocBorder: 'border-slate-800/50',
    kbdBg: 'bg-white/10 text-[#999999]',
    searchDialogBg: 'bg-slate-900 border-slate-700',
    searchDialogBorder: 'border-slate-700',
    searchDialogInput: 'text-white placeholder:text-[#787878]',
    searchDialogKbd: 'text-[#999999] bg-slate-800 border-slate-700',
    searchResultHover: 'hover:bg-slate-800',
    searchResultTitle: 'text-white group-hover:text-[#00A1B2]',
    searchResultMuted: 'text-[#787878]',
    searchResultSnippet: 'text-[#999999]',
    badgeBg: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
    badgeBorder: '1px solid rgba(255,255,255,0.1)',
    badgeText: 'text-[#999999]',
    proseClass: 'prose-invert prose-p:text-[#999999] prose-li:text-[#999999] prose-strong:text-white prose-pre:bg-slate-900 prose-pre:border prose-pre:border-white/10',
    logoInvert: false,
    ctaSecondaryBorder: 'border-white/10 hover:border-white/20',
    ctaSecondaryText: 'text-[#999999] hover:text-white',
    ctaPrimaryBg: 'bg-black text-white hover:bg-gray-900',
    navArrowColor: 'text-[#787878]',
    hoverText: 'hover:text-white',
  },
  light: {
    id: 'light',
    bg: 'bg-white',
    navBg: 'bg-white',
    sidebarBg: 'bg-white',
    text: 'text-gray-900',
    textMuted: 'text-gray-500',
    textSecondary: 'text-gray-400',
    border: 'border-gray-200',
    hover: 'hover:bg-gray-100',
    activeBg: 'bg-[#00A1B2]',
    activeText: 'text-white',
    activeAccent: 'text-[#00A1B2]',
    inputBg: 'bg-white border border-gray-200',
    tocBorder: 'border-gray-200',
    kbdBg: 'bg-gray-100 text-gray-400',
    searchDialogBg: 'bg-white border-gray-200',
    searchDialogBorder: 'border-gray-200',
    searchDialogInput: 'text-gray-900 placeholder:text-gray-400',
    searchDialogKbd: 'text-gray-400 bg-gray-100 border-gray-200',
    searchResultHover: 'hover:bg-gray-50',
    searchResultTitle: 'text-gray-900 group-hover:text-[#00A1B2]',
    searchResultMuted: 'text-gray-400',
    searchResultSnippet: 'text-gray-500',
    badgeBg: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
    badgeBorder: '1px solid rgba(0,0,0,0.1)',
    badgeText: 'text-gray-700',
    proseClass: 'prose-gray prose-pre:bg-gray-50 prose-pre:border prose-pre:border-gray-200',
    logoInvert: true,
    ctaSecondaryBorder: 'border-gray-200 hover:border-gray-300',
    ctaSecondaryText: 'text-gray-500 hover:text-gray-900',
    ctaPrimaryBg: 'bg-black text-white hover:bg-gray-900',
    navArrowColor: 'text-gray-400',
    hoverText: 'hover:text-gray-900',
  },
};

// ============= TOP NAVIGATION =============
const TopNavigation = ({ theme, onThemeToggle, isDark, onSearchOpen }) => {
  return (
    <header className={`fixed top-0 left-0 right-0 z-50 ${theme.navBg} border-b ${theme.border}`} data-testid="kb-header">
      <div className="h-14 px-4 sm:px-6 flex items-center justify-between">
        <a href="https://app.emergent.sh" className="flex items-center gap-2 flex-shrink-0" data-testid="logo-link">
          <img src="/images/emergent-logo-dark.png" alt="Emergent" className={`h-6 ${theme.logoInvert ? 'invert' : ''}`} />
        </a>

        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          <button
            onClick={onSearchOpen}
            className={`p-2 rounded-lg ${theme.textMuted} ${theme.hoverText} ${theme.hover} transition-colors`}
            data-testid="topnav-search"
            title="Search (⌘K)"
          >
            <Search className="w-[18px] h-[18px]" />
          </button>
          <Link to="/portal"
            className="hidden sm:flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-[#00A1B2] text-white text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
            data-testid="need-help-button">
            <span>Need Help</span>
          </Link>
          <button
            onClick={onThemeToggle}
            className={`p-2 rounded-lg ${theme.textMuted} ${theme.hoverText} ${theme.hover} transition-colors`}
            data-testid="kb-theme-toggle"
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </header>
  );
};

// ============= BREADCRUMB BAR =============
const BreadcrumbBar = ({ breadcrumb, theme, isDark, onMobileMenuToggle, mobileMenuOpen }) => {
  return (
    <div
      className={`fixed top-14 left-0 right-0 z-40 border-b ${theme.border} min-[810px]:hidden transition-opacity duration-200 ${mobileMenuOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
      style={{
        backgroundColor: isDark ? 'rgba(10,10,10,0.75)' : 'rgba(255,255,255,0.75)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
      }}
      data-testid="kb-breadcrumb-bar"
    >
      <div className="h-10 px-4 sm:px-6 lg:pl-[17.5rem] flex items-center gap-2.5">
        <button
          className={`lg:hidden p-1 rounded ${theme.textSecondary} ${theme.hoverText} transition-colors`}
          onClick={onMobileMenuToggle}
          data-testid="breadcrumb-menu-toggle"
        >
          <Menu className="w-4 h-4" />
        </button>
        {breadcrumb && (
          <nav className={`flex items-center gap-1.5 text-sm ${theme.textMuted} min-w-0`} data-testid="kb-breadcrumb">
            <span className="flex-shrink-0">{breadcrumb.section}</span>
            {breadcrumb.title && (
              <>
                <ChevronDown className="w-3 h-3 -rotate-90 flex-shrink-0" />
                <span className={`${theme.text} truncate`}>{breadcrumb.title}</span>
              </>
            )}
          </nav>
        )}
      </div>
    </div>
  );
};

// ============= LEFT SIDEBAR =============
const LeftSidebar = ({ activeTab, tabs, documents, selectedDocSlug, onDocSelect, theme, onSearchOpen, mobileOpen, onMobileClose, isDark }) => {
  const [collapsedGroups, setCollapsedGroups] = useState({});

  const toggleGroup = (key) => {
    setCollapsedGroups(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Lock body scroll when mobile sidebar is open
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [mobileOpen]);

  return (
    <>
      {/* Mobile overlay backdrop with close button */}
      {mobileOpen && (
        <div className="fixed inset-0 z-[45] lg:hidden" onClick={onMobileClose} data-testid="sidebar-backdrop">
          <div className="absolute inset-0 bg-black/40" />
          <button
            onClick={onMobileClose}
            className="absolute top-4 right-4 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-white/90 dark:bg-white/15 text-gray-600 dark:text-white shadow-lg transition-transform hover:scale-105"
            data-testid="sidebar-close-btn"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}
      {/* Desktop: below both headers. Mobile: full screen overlay from top */}
      <aside
        className={`fixed z-[46] ${theme.sidebarBg} border-r ${theme.border} flex flex-col transform transition-transform duration-300 ease-out
          lg:top-14 lg:bottom-0 lg:left-0 lg:w-64 lg:translate-x-0
          top-0 bottom-0 left-0 w-[80%] max-w-[320px]
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
        data-testid="kb-sidebar"
      >
        <div className="lg:hidden p-4 flex items-center gap-3">
          <button onClick={onSearchOpen} className={`flex-1 flex items-center gap-3 px-3 py-2.5 ${theme.inputBg} rounded-lg text-sm ${theme.textMuted} transition-colors`} data-testid="sidebar-search">
            <Search className="w-4 h-4" />
            <span className="flex-1 text-left">Search...</span>
            <kbd className={`px-1.5 py-0.5 text-xs rounded ${theme.kbdBg}`}>&#8984;K</kbd>
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto overscroll-contain px-4 pt-5 pb-6 kb-sidebar-scroll" data-testid="kb-nav-tree">
          {tabs.map((tab) => {
            const groups = tab.groups || [];

            return (
              <div key={tab.id} className="mb-4" data-testid={`sidebar-tab-${tab.id}`}>
                {tabs.length > 1 && (
                  <div className={`px-3 mb-3 text-base font-bold ${theme.text}`} data-testid={`sidebar-tab-label-${tab.id}`}>
                    {tab.label}
                  </div>
                )}

                {groups.map((group, gi) => {
                  const groupKey = `${tab.id}-${gi}`;
                  const isCollapsed = collapsedGroups[groupKey] === true;

                  return (
                    <div key={gi} className="mb-1">
                      <button
                        onClick={() => toggleGroup(groupKey)}
                        className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors ${theme.textMuted} ${theme.hoverText} ${theme.hover}`}
                        data-testid={`sidebar-group-toggle-${gi}`}
                      >
                        <span className="truncate">{group.group}</span>
                        <ChevronDown className={`w-3.5 h-3.5 flex-shrink-0 ${theme.textSecondary} transition-transform duration-200 ${isCollapsed ? '-rotate-90' : ''}`} />
                      </button>

                      {!isCollapsed && (
                        <div className="mt-0.5 space-y-px">
                          {group.pages?.map((page, pi) => {
                            const pageSlug = typeof page === 'string' ? page : page.page;
                            const doc = documents.find(d => d.slug?.toLowerCase() === pageSlug?.toLowerCase());
                            const title = typeof page === 'string' ? doc?.title || page : page.title || page.page;
                            const isActive = pageSlug?.toLowerCase() === selectedDocSlug?.toLowerCase();
                            const isMissing = !doc;

                            return (
                              <button key={pi} onClick={() => { if (!isMissing) { onDocSelect(pageSlug); onMobileClose(); } }} disabled={isMissing}
                                className={`w-full text-left pl-6 pr-3 py-2 rounded-lg text-[13.5px] leading-snug transition-colors ${isActive ? `${theme.activeBg} ${theme.activeText} font-medium` : isMissing ? 'text-gray-400 cursor-not-allowed' : `${theme.textMuted} ${theme.hover} ${theme.hoverText}`}`}
                                data-testid={`sidebar-page-${pageSlug}`}>
                                <span className={isMissing ? 'italic opacity-50' : ''}>{title}</span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </nav>
      </aside>
    </>
  );
};

// ============= RIGHT SIDEBAR (TOC) =============
const RightSidebar = ({ headings, theme }) => {
  const [activeId, setActiveId] = useState('');
  const [validHeadings, setValidHeadings] = useState([]);

  // Only show H2 headings
  const h2Headings = useMemo(() => headings.filter(h => h.level === 2), [headings]);

  useEffect(() => {
    const existing = h2Headings.filter(h => document.getElementById(h.id));
    setValidHeadings(existing);
  }, [h2Headings]);

  // Set the first heading as active by default on load
  useEffect(() => {
    if (validHeadings.length > 0 && !activeId) {
      setActiveId(validHeadings[0].id);
    }
  }, [validHeadings, activeId]);

  useEffect(() => {
    if (validHeadings.length === 0) return;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => { if (entry.isIntersecting) setActiveId(entry.target.id); });
    }, { rootMargin: '-80px 0px -80% 0px' });
    validHeadings.forEach((h) => { const el = document.getElementById(h.id); if (el) observer.observe(el); });
    return () => observer.disconnect();
  }, [validHeadings]);

  if (validHeadings.length === 0) return null;

  return (
    <aside className={`hidden xl:block fixed top-14 right-0 bottom-0 w-64 overflow-y-auto z-10`} data-testid="kb-toc">
      <div className="p-4 pt-6">
        <h4 className={`text-xs font-semibold ${theme.text} mb-4 flex items-center gap-2`}>
          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><line x1="2" y1="4" x2="14" y2="4"/><line x1="2" y1="8" x2="10" y2="8"/><line x1="2" y1="12" x2="12" y2="12"/></svg>
          On this page
        </h4>
        <nav className="relative">
          <div className="absolute left-0 top-0 bottom-0 w-px bg-gray-200 dark:bg-white/10" />
          <div className="space-y-0">
            {validHeadings.map((h) => {
              const isActive = activeId === h.id;
              return (
                <a key={h.id} href={`#${h.id}`}
                  onClick={(e) => {
                    e.preventDefault();
                    const el = document.getElementById(h.id);
                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                  }}
                  className={`relative block pl-4 py-1.5 text-[13px] leading-snug transition-colors break-words ${
                    isActive
                      ? `${theme.activeAccent} font-medium`
                      : `${theme.textMuted} hover:text-gray-800 dark:hover:text-gray-200`
                  }`}>
                  {isActive && (
                    <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-[#00A1B2] rounded-full" />
                  )}
                  {h.text}
                </a>
              );
            })}
          </div>
        </nav>
      </div>
    </aside>
  );
};

// ============= HIGHLIGHT MATCH =============
const HighlightMatch = ({ text, query }) => {
  if (!query || query.length < 2) return <>{text}</>;
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  const parts = text.split(regex);
  return <>{parts.map((part, i) => regex.test(part) ? <span key={i} className="text-[#00A1B2] font-semibold">{part}</span> : part)}</>;
};

// ============= SEARCH DIALOG =============
const SearchDialog = ({ open, onClose, documents, onSelect, theme, config }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState({ documents: [], headings: [] });
  const inputRef = useRef(null);
  const tabs = config?.navigation?.tabs || [];

  const getBreadcrumb = (slug) => {
    for (const tab of tabs) {
      for (const group of (tab.groups || [])) {
        for (const page of (group.pages || [])) {
          const ps = typeof page === 'string' ? page : page.page;
          if (ps?.toLowerCase() === slug?.toLowerCase()) return { tab: tab.label, group: group.group };
        }
      }
    }
    return null;
  };

  const getTabLabel = (slug) => {
    for (const tab of tabs) {
      const found = tab.groups?.some(g => g.pages?.some(p => (typeof p === 'string' ? p : p.page)?.toLowerCase() === slug?.toLowerCase()));
      if (found) return tab.label;
    }
    return null;
  };

  useEffect(() => {
    if (open) {
      setQuery(''); setResults({ documents: [], headings: [] });
      setTimeout(() => inputRef.current?.focus(), 100);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [open]);
  useEffect(() => { if (query.length >= 2) setResults(search(query)); else setResults({ documents: [], headings: [] }); }, [query]);
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape' && open) onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;
  const hasResults = results.documents?.length > 0 || results.headings?.length > 0;
  const isDark = theme.id === 'dark';

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[12vh]">
      <div className={`fixed inset-0 ${isDark ? 'bg-black/70' : 'bg-white/70'} backdrop-blur-md`} onClick={onClose} />
      <div className={`relative w-full max-w-[620px] mx-4 ${isDark ? 'bg-[#1a1a1a] border-white/10' : 'bg-white border-gray-200'} border rounded-2xl shadow-2xl overflow-hidden`}>
        <div className={`flex items-center gap-3 px-5 py-4 ${hasResults || query.length >= 2 ? `border-b ${isDark ? 'border-white/10' : 'border-gray-100'}` : ''}`}>
          <Search className={`w-5 h-5 flex-shrink-0 ${isDark ? 'text-[#999999]' : 'text-gray-400'}`} />
          <input ref={inputRef} type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search..."
            className={`flex-1 bg-transparent text-base outline-none ${isDark ? 'text-white placeholder:text-[#787878]' : 'text-gray-900 placeholder:text-gray-400'}`} data-testid="search-input" />
          <div className="flex items-center gap-2 flex-shrink-0">
            <kbd className={`px-2 py-0.5 text-[11px] font-medium rounded border ${isDark ? 'text-[#999999] bg-white/5 border-white/10' : 'text-gray-400 bg-gray-100 border-gray-200'}`}>ESC</kbd>
            <button onClick={onClose} className={`p-1 rounded ${isDark ? 'text-[#999999] hover:text-white' : 'text-gray-400 hover:text-gray-900'} transition-colors`}>
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
        {(hasResults || query.length >= 2) && (
          <div className="max-h-[55vh] overflow-auto">
            {hasResults ? (
              <div className="py-2">
                {results.documents?.map((r, i) => {
                  const bc = getBreadcrumb(r.slug);
                  const tabLabel = getTabLabel(r.slug);
                  const snippet = r.snippet || (documents.find(d => d.slug === r.slug)?.content?.substring(0, 120) + '...');
                  return (
                    <button key={`d-${i}`} onClick={() => { onSelect(r.slug); onClose(); }}
                      className={`w-full text-left px-5 py-3.5 ${isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'} transition-colors border-b ${isDark ? 'border-white/5' : 'border-gray-50'} last:border-0`}>
                      {bc && <div className={`text-[11px] uppercase tracking-wider mb-1.5 ${isDark ? 'text-[#787878]' : 'text-gray-400'}`}>{bc.tab} &gt; {bc.group}</div>}
                      <div className={`text-sm font-semibold mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        <HighlightMatch text={r.title} query={query} />
                      </div>
                      {tabLabel && <div className={`text-xs mb-1 ${isDark ? 'text-[#787878]' : 'text-gray-400'}`}>{tabLabel}</div>}
                      {snippet && <div className={`text-xs leading-relaxed line-clamp-2 ${isDark ? 'text-[#999999]' : 'text-gray-500'}`}><HighlightMatch text={snippet} query={query} /></div>}
                    </button>
                  );
                })}
                {results.headings?.map((r, i) => {
                  const bc = getBreadcrumb(r.slug);
                  return (
                    <button key={`h-${i}`} onClick={() => { onSelect(r.slug); onClose(); setTimeout(() => { const el = document.getElementById(r.anchor); if (el) el.scrollIntoView({ behavior: 'smooth' }); }, 300); }}
                      className={`w-full text-left px-5 py-3.5 ${isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'} transition-colors border-b ${isDark ? 'border-white/5' : 'border-gray-50'} last:border-0`}>
                      {bc && <div className={`text-[11px] uppercase tracking-wider mb-1.5 ${isDark ? 'text-[#787878]' : 'text-gray-400'}`}>{bc.tab} &gt; {r.docTitle || bc.group}</div>}
                      <div className={`text-sm font-semibold mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        <HighlightMatch text={r.text} query={query} />
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="px-5 py-10 text-center">
                <div className={`text-sm ${isDark ? 'text-[#999999]' : 'text-gray-500'}`}>No results for "<span className="font-medium">{query}</span>"</div>
                <div className={`text-xs mt-1 ${isDark ? 'text-[#787878]' : 'text-gray-400'}`}>Try different keywords</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ============= COPY BUTTON =============
const CopyButton = ({ text, theme }) => {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  return (
    <button onClick={handleCopy} className={`flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1.5 ${theme.inputBg} rounded-lg text-sm ${theme.textMuted} ${theme.hoverText} transition-colors flex-shrink-0`} data-testid="copy-page-btn">
      {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
      <span className="hidden sm:inline">{copied ? 'Copied!' : 'Copy page'}</span>
      <ChevronDown className="w-3 h-3 hidden sm:block" />
    </button>
  );
};

const FeedbackWidget = ({ slug, theme }) => {
  const [submitted, setSubmitted] = useState(null);
  const [sending, setSending] = useState(false);

  useEffect(() => { setSubmitted(null); }, [slug]);

  const submit = async (helpful) => {
    if (sending || submitted !== null) return;
    setSending(true);
    try {
      await fetch(`${API}/api/kb/articles/${slug}/feedback`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ helpful }),
      });
      setSubmitted(helpful);
    } catch { /* silent */ }
    setSending(false);
  };

  return (
    <div className={`flex flex-col items-center gap-3 mt-14 pt-8 border-t ${theme.border}`} data-testid="kb-feedback-widget">
      {submitted === null ? (
        <>
          <span className={`text-sm ${theme.textMuted}`}>Was this article helpful?</span>
          <div className="flex items-center gap-3">
            <button onClick={() => submit(true)} disabled={sending}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${theme.border} text-sm ${theme.textMuted} hover:text-[#00A1B2] hover:border-[#00A1B2]/40 transition-all`}
              data-testid="feedback-helpful-btn">
              <ThumbsUp className="w-4 h-4" />Yes
            </button>
            <button onClick={() => submit(false)} disabled={sending}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${theme.border} text-sm ${theme.textMuted} hover:text-red-400 hover:border-red-500/40 transition-all`}
              data-testid="feedback-unhelpful-btn">
              <ThumbsDown className="w-4 h-4" />No
            </button>
          </div>
        </>
      ) : (
        <span className={`text-sm ${submitted ? 'text-[#00A1B2]' : 'text-[#999999]'}`} data-testid="feedback-thanks">
          {submitted ? 'Glad this helped!' : 'Thanks for letting us know. We\'ll improve this article.'}
        </span>
      )}
    </div>
  );
};

// ============= SOCIAL LINKS =============
const SOCIAL_ICONS = {
  twitter: (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  ),
  linkedin: (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  ),
  discord: (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189z" />
    </svg>
  ),
  youtube: (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
    </svg>
  ),
  reddit: (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M12 0A12 12 0 000 12a12 12 0 0012 12 12 12 0 0012-12A12 12 0 0012 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 01-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 01.042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 014.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 01.14-.197.35.35 0 01.238-.042l2.906.617a1.214 1.214 0 011.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 00-.231.094.33.33 0 000 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 00.029-.463.33.33 0 00-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 00-.232-.095z" />
    </svg>
  ),
};

const SocialLinks = ({ theme }) => {
  const [links, setLinks] = useState({});
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/kb/social-links`)
      .then(r => r.json())
      .then(d => { setLinks(d.links || {}); setLoaded(true); })
      .catch(() => setLoaded(true));
  }, []);

  if (!loaded) return null;

  const activeLinks = Object.entries(links).filter(([, url]) => url && url.trim());
  if (activeLinks.length === 0) return null;

  const isDark = theme.id === 'dark';

  return (
    <div className="flex items-center gap-4 mt-10" data-testid="kb-social-links">
      {activeLinks.map(([platform, url]) => (
        <a
          key={platform}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className={`transition-all duration-200 ${
            isDark
              ? 'text-[#525252] hover:text-white'
              : 'text-gray-350 hover:text-gray-900'
          }`}
          style={isDark ? {} : { color: '#b0b0b0' }}
          data-testid={`social-link-${platform}`}
          title={platform.charAt(0).toUpperCase() + platform.slice(1)}
        >
          {SOCIAL_ICONS[platform]}
        </a>
      ))}
    </div>
  );
};

// ============= MAIN COMPONENT =============
const PublicDocs = () => {
  const { slug: docSlug } = useParams();
  const navigate = useNavigate();

  const [config, setConfig] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [toc, setToc] = useState([]);
  const [activeTab, setActiveTab] = useState('');
  const [isNavigating, setIsNavigating] = useState(false);
  const [kbTheme, setKbTheme] = useState(() => {
    return localStorage.getItem('kb-theme') || 'light';
  });

  const isDark = kbTheme === 'dark';
  const theme = isDark ? THEMES.dark : THEMES.light;

  const toggleKbTheme = useCallback(() => {
    setKbTheme(prev => {
      const next = prev === 'dark' ? 'light' : 'dark';
      localStorage.setItem('kb-theme', next);
      return next;
    });
  }, []);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    return () => { document.documentElement.classList.remove('dark'); };
  }, [isDark]);

  const tabs = useMemo(() => {
    const rawTabs = config?.navigation?.tabs || [];
    return rawTabs.length > 0
      ? rawTabs.map(t => ({ id: t.id || t.label, label: t.label || t.id, icon: t.icon, groups: t.groups || [] }))
      : [{ id: 'docs', label: 'Documentation', groups: documents.length > 0 ? [{ group: 'Documentation', pages: documents.map(d => ({ page: d.slug, title: d.title })) }] : [] }];
  }, [config?.navigation, documents]);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/kb/public-data`);
      const data = await res.json();
      setConfig(data.config);
      setDocuments(data.documents);
      const navTabs = data.config?.navigation?.tabs;
      if (navTabs?.length > 0) setActiveTab(navTabs[0].id);
      if (data.documents.length > 0) initializeSearch(data.documents);
    } catch (e) { console.error('Failed to fetch:', e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const getFirstNavDocument = useCallback(() => {
    for (const tab of tabs) {
      for (const group of (tab.groups || [])) {
        for (const page of (group.pages || [])) {
          const slug = typeof page === 'string' ? page : page.page;
          const doc = documents.find(d => d.slug?.toLowerCase() === slug?.toLowerCase());
          if (doc) return doc;
        }
      }
    }
    return null;
  }, [tabs, documents]);

  useEffect(() => {
    if (isNavigating) return;
    if (documents.length > 0 && !selectedDoc) {
      if (docSlug) {
        const doc = documents.find(d => d.slug?.toLowerCase() === docSlug?.toLowerCase());
        setSelectedDoc(doc || getFirstNavDocument() || documents[0]);
      } else {
        setSelectedDoc(getFirstNavDocument() || documents[0]);
      }
    } else if (documents.length > 0 && docSlug && selectedDoc?.slug?.toLowerCase() !== docSlug?.toLowerCase()) {
      const doc = documents.find(d => d.slug?.toLowerCase() === docSlug?.toLowerCase());
      if (doc) setSelectedDoc(doc);
    }
  }, [documents, docSlug, selectedDoc, getFirstNavDocument, isNavigating]);

  const handleDocSelect = useCallback((slug) => {
    if (isNavigating) return;
    const doc = documents.find(d => d.slug?.toLowerCase() === slug?.toLowerCase());
    if (doc && doc.id !== selectedDoc?.id) {
      setIsNavigating(true);
      setSelectedDoc(doc);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      requestAnimationFrame(() => { navigate(`/docs/${slug}`); setTimeout(() => setIsNavigating(false), 100); });
    }
  }, [documents, navigate, selectedDoc, isNavigating]);

  useEffect(() => {
    const handler = (e) => { if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); setSearchOpen(prev => !prev); } };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  useEffect(() => {
    if (selectedDoc && tabs.length > 0) {
      for (const tab of tabs) {
        const found = tab.groups?.some(g => g.pages?.some(p => (typeof p === 'string' ? p : p.page)?.toLowerCase() === selectedDoc.slug?.toLowerCase()));
        if (found) { setActiveTab(tab.id); break; }
      }
    }
  }, [selectedDoc, tabs]);

  const getBreadcrumb = () => {
    const currentTab = tabs.find(t => t.id === activeTab);
    if (!currentTab || !selectedDoc) return null;
    for (const group of currentTab.groups || []) {
      const page = group.pages?.find(p => (typeof p === 'string' ? p : p.page)?.toLowerCase() === selectedDoc?.slug?.toLowerCase());
      if (page) return { section: group.group, title: selectedDoc.title };
    }
    return { section: currentTab.label, title: selectedDoc?.title };
  };

  const currentIndex = documents.findIndex(d => d.id === selectedDoc?.id);

  // Global prev/next: flatten all tabs → groups → pages for seamless cross-category navigation
  const allNavSlugs = useMemo(() => {
    const slugs = [];
    for (const tab of tabs) {
      for (const group of tab.groups || []) {
        for (const page of group.pages || []) {
          slugs.push((typeof page === 'string' ? page : page.page)?.toLowerCase());
        }
      }
    }
    return slugs;
  }, [tabs]);

  const navIndex = allNavSlugs.indexOf(selectedDoc?.slug?.toLowerCase());
  const prevDoc = navIndex > 0 ? documents.find(d => d.slug?.toLowerCase() === allNavSlugs[navIndex - 1]) : null;
  const nextDoc = navIndex < allNavSlugs.length - 1 ? documents.find(d => d.slug?.toLowerCase() === allNavSlugs[navIndex + 1]) : null;

  if (loading) {
    return (
      <div className={`min-h-screen ${theme.bg} flex items-center justify-center`}>
        <div className="animate-spin w-8 h-8 border-2 border-[#00A1B2] border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${theme.bg} relative`} data-testid="kb-docs">

      <TopNavigation theme={theme} onThemeToggle={toggleKbTheme} isDark={isDark} onSearchOpen={() => setSearchOpen(true)} />
      <BreadcrumbBar breadcrumb={getBreadcrumb()} theme={theme} isDark={isDark} onMobileMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)} mobileMenuOpen={mobileMenuOpen} />
      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} documents={documents} onSelect={handleDocSelect} theme={theme} config={config} />
      <LeftSidebar activeTab={activeTab} tabs={tabs} documents={documents} selectedDocSlug={selectedDoc?.slug} onDocSelect={handleDocSelect} theme={theme} onSearchOpen={() => setSearchOpen(true)} mobileOpen={mobileMenuOpen} onMobileClose={() => setMobileMenuOpen(false)} isDark={isDark} />

      <main className="lg:ml-64 xl:mr-64 min-h-screen pt-24 min-[810px]:pt-14 relative z-10 overflow-x-hidden">
        {selectedDoc ? (
          <article key={selectedDoc.id} className="max-w-[800px] mx-auto px-4 sm:px-6 py-8 sm:py-10 pb-20 animate-fadeIn">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-4 mb-8">
              <h1 className={`font-bold ${theme.text}`} style={{ fontFamily: "'Brockmann', sans-serif", fontSize: '30px', lineHeight: '36px', letterSpacing: '-0.01em' }} data-testid="kb-page-title">{selectedDoc.title}</h1>
              <CopyButton text={window.location.href} theme={theme} />
            </div>
            <div className={`docs-prose prose ${theme.proseClass} max-w-none overflow-hidden prose-headings:font-semibold prose-headings:text-inherit prose-h2:text-xl prose-h2:sm:text-2xl prose-h2:mt-10 prose-h2:mb-4 prose-h3:text-lg prose-h3:sm:text-xl prose-h3:mt-8 prose-h3:mb-3 prose-p:text-[15px] prose-p:sm:text-base prose-p:leading-7 prose-p:break-words prose-a:text-[#00A1B2] prose-a:no-underline hover:prose-a:underline prose-code:text-[#00A1B2] prose-code:bg-[#00A1B2]/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:break-words prose-code:text-[13px] prose-code:sm:text-sm prose-pre:rounded-xl prose-pre:overflow-x-auto prose-pre:text-[13px] prose-pre:sm:text-sm prose-img:rounded-lg prose-img:max-w-full prose-img:h-auto prose-table:overflow-x-auto prose-table:block prose-table:w-full`} data-testid="kb-article-body">
              <DocContent content={selectedDoc.content?.replace(new RegExp(`^#\\s*${selectedDoc.title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\n+`, 'i'), '') || selectedDoc.content} onHeadings={setToc} />
            </div>
            <FeedbackWidget slug={selectedDoc.slug} theme={theme} />
            <div className={`flex flex-col sm:flex-row justify-between gap-3 sm:gap-4 mt-12 sm:mt-16 pt-8 border-t ${theme.border}`} data-testid="kb-prev-next">
              {prevDoc ? (
                <button onClick={() => handleDocSelect(prevDoc.slug)} className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${theme.border} ${theme.hover} transition-colors w-full sm:w-auto`} data-testid="prev-doc-btn">
                  <ArrowLeft className={`w-4 h-4 flex-shrink-0 ${theme.navArrowColor}`} />
                  <div className="text-left min-w-0"><span className={`block text-xs ${theme.navArrowColor}`}>Previous</span><span className={`text-sm font-medium ${theme.text} truncate block`}>{prevDoc.title}</span></div>
                </button>
              ) : <div />}
              {nextDoc && (
                <button onClick={() => handleDocSelect(nextDoc.slug)} className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${theme.border} ${theme.hover} transition-colors w-full sm:w-auto sm:ml-auto`} data-testid="next-doc-btn">
                  <div className="text-right min-w-0 flex-1 sm:flex-initial"><span className={`block text-xs ${theme.navArrowColor}`}>Next</span><span className={`text-sm font-medium ${theme.text} truncate block`}>{nextDoc.title}</span></div>
                  <ArrowRight className={`w-4 h-4 flex-shrink-0 ${theme.navArrowColor}`} />
                </button>
              )}
            </div>
            <SocialLinks theme={theme} />
          </article>
        ) : (
          <div className="flex items-center justify-center h-[60vh]"><p className={theme.textMuted}>Select a document</p></div>
        )}
      </main>

      <RightSidebar headings={toc} theme={theme} />

      {/* Made with Emergent badge */}
      <a
        href="https://app.emergent.sh/?utm_source=emergent-badge"
        target="_blank"
        rel="noopener noreferrer"
        className={`fixed bottom-4 right-4 sm:bottom-5 sm:right-5 z-[9999] flex items-center gap-2 sm:gap-2.5 px-2.5 sm:px-3.5 py-1.5 sm:py-2 rounded-[10px] no-underline shadow-lg transition-all hover:scale-105`}
        style={{ background: theme.badgeBg, border: theme.badgeBorder }}
        data-testid="made-with-emergent-badge"
      >
        <img src="https://avatars.githubusercontent.com/in/1201222?s=120&u=2686cf91179bbafbc7a71bfbc43004cf9ae1acea&v=4" alt="" className="w-[18px] h-[18px] sm:w-[22px] sm:h-[22px] rounded" />
        <span className={`${theme.badgeText} text-xs sm:text-sm font-medium tracking-[0.01em]`}>Made with Emergent</span>
      </a>
    </div>
  );
};

export default PublicDocs;
