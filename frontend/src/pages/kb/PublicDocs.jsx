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
    textMuted: 'text-slate-400',
    textSecondary: 'text-slate-500',
    border: 'border-white/10',
    hover: 'hover:bg-white/5',
    activeBg: 'bg-[#00A1B2]',
    activeText: 'text-white',
    activeAccent: 'text-[#00A1B2]',
    inputBg: 'bg-white/5 border border-white/10',
    tocBorder: 'border-slate-800/50',
    kbdBg: 'bg-white/10 text-slate-400',
    searchDialogBg: 'bg-slate-900 border-slate-700',
    searchDialogBorder: 'border-slate-700',
    searchDialogInput: 'text-white placeholder:text-slate-500',
    searchDialogKbd: 'text-slate-400 bg-slate-800 border-slate-700',
    searchResultHover: 'hover:bg-slate-800',
    searchResultTitle: 'text-white group-hover:text-[#00A1B2]',
    searchResultMuted: 'text-slate-500',
    searchResultSnippet: 'text-slate-400',
    badgeBg: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
    badgeBorder: '1px solid rgba(255,255,255,0.1)',
    badgeText: 'text-slate-200',
    proseClass: 'prose-invert prose-pre:bg-slate-900 prose-pre:border prose-pre:border-white/10',
    logoInvert: false,
    ctaSecondaryBorder: 'border-white/10 hover:border-white/20',
    ctaSecondaryText: 'text-slate-400 hover:text-white',
    ctaPrimaryBg: 'bg-black text-white hover:bg-gray-900',
    navArrowColor: 'text-slate-500',
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
const TopNavigation = ({ config, theme, mobileMenuOpen, onMobileMenuToggle, onThemeToggle, isDark, onSearchOpen }) => {
  return (
    <header className={`fixed top-0 left-0 right-0 z-50 ${theme.navBg} border-b ${theme.border}`} data-testid="kb-header">
      <div className="h-14 px-4 sm:px-6 flex items-center justify-between">
        <a href="https://app.emergent.sh" className="flex items-center gap-2 flex-shrink-0" data-testid="logo-link">
          <img src="/images/emergent-logo-dark.png" alt="Emergent" className={`h-6 ${theme.logoInvert ? 'invert' : ''}`} />
        </a>

        <div className="hidden lg:flex flex-1 justify-center px-8">
          <button onClick={onSearchOpen} className={`w-full max-w-[548px] flex items-center gap-3 px-4 py-2 ${theme.inputBg} rounded-lg text-sm ${theme.textMuted} transition-colors`} data-testid="topnav-search">
            <Search className="w-4 h-4" />
            <span className="flex-1 text-left">Search...</span>
            <kbd className={`px-1.5 py-0.5 text-xs rounded ${theme.kbdBg}`}>&#8984;K</kbd>
          </button>
        </div>

        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          <Link to="/portal"
            className={`hidden sm:flex items-center gap-1.5 px-3 sm:px-4 py-2 text-sm font-medium rounded-lg border ${theme.ctaSecondaryBorder} ${theme.ctaSecondaryText} transition-colors`}
            data-testid="need-help-button">
            <span>Need Help</span>
          </Link>
          <a href="https://app.emergent.sh"
            className={`flex items-center gap-1.5 px-3 sm:px-4 py-2 ${theme.ctaPrimaryBg} text-sm font-medium rounded-lg transition-colors`}
            data-testid="cta-button">
            <span>Try Emergent</span>
            <ArrowRight className="w-4 h-4" />
          </a>
          <button
            onClick={onThemeToggle}
            className={`p-2 rounded-lg ${theme.textMuted} ${theme.hoverText} ${theme.hover} transition-colors`}
            data-testid="kb-theme-toggle"
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <button className={`lg:hidden p-2 rounded-lg ${theme.hover} ${theme.text}`} onClick={onMobileMenuToggle} data-testid="mobile-nav-toggle">
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </header>
  );
};

// ============= LEFT SIDEBAR =============
const LeftSidebar = ({ activeTab, tabs, documents, selectedDocSlug, onDocSelect, theme, onSearchOpen, mobileOpen, onMobileClose }) => {
  const [collapsedGroups, setCollapsedGroups] = useState({});

  const toggleGroup = (key) => {
    setCollapsedGroups(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <>
      {mobileOpen && <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={onMobileClose} />}
      <aside className={`fixed top-14 bottom-0 left-0 z-40 w-64 ${theme.sidebarBg} border-r ${theme.border} transform transition-transform duration-300 lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'} flex flex-col`} data-testid="kb-sidebar">
        <div className="lg:hidden p-4">
          <button onClick={onSearchOpen} className={`w-full flex items-center gap-3 px-3 py-2.5 ${theme.inputBg} rounded-lg text-sm ${theme.textMuted} transition-colors`} data-testid="sidebar-search">
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
                        className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors ${theme.text} ${theme.hover}`}
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
          <Search className={`w-5 h-5 flex-shrink-0 ${isDark ? 'text-slate-400' : 'text-gray-400'}`} />
          <input ref={inputRef} type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search..."
            className={`flex-1 bg-transparent text-base outline-none ${isDark ? 'text-white placeholder:text-slate-500' : 'text-gray-900 placeholder:text-gray-400'}`} data-testid="search-input" />
          <div className="flex items-center gap-2 flex-shrink-0">
            <kbd className={`px-2 py-0.5 text-[11px] font-medium rounded border ${isDark ? 'text-slate-400 bg-white/5 border-white/10' : 'text-gray-400 bg-gray-100 border-gray-200'}`}>ESC</kbd>
            <button onClick={onClose} className={`p-1 rounded ${isDark ? 'text-slate-400 hover:text-white' : 'text-gray-400 hover:text-gray-900'} transition-colors`}>
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
                      {bc && <div className={`text-[11px] uppercase tracking-wider mb-1.5 ${isDark ? 'text-slate-500' : 'text-gray-400'}`}>{bc.tab} &gt; {bc.group}</div>}
                      <div className={`text-sm font-semibold mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        <HighlightMatch text={r.title} query={query} />
                      </div>
                      {tabLabel && <div className={`text-xs mb-1 ${isDark ? 'text-slate-500' : 'text-gray-400'}`}>{tabLabel}</div>}
                      {snippet && <div className={`text-xs leading-relaxed line-clamp-2 ${isDark ? 'text-slate-400' : 'text-gray-500'}`}><HighlightMatch text={snippet} query={query} /></div>}
                    </button>
                  );
                })}
                {results.headings?.map((r, i) => {
                  const bc = getBreadcrumb(r.slug);
                  return (
                    <button key={`h-${i}`} onClick={() => { onSelect(r.slug); onClose(); setTimeout(() => { const el = document.getElementById(r.anchor); if (el) el.scrollIntoView({ behavior: 'smooth' }); }, 300); }}
                      className={`w-full text-left px-5 py-3.5 ${isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'} transition-colors border-b ${isDark ? 'border-white/5' : 'border-gray-50'} last:border-0`}>
                      {bc && <div className={`text-[11px] uppercase tracking-wider mb-1.5 ${isDark ? 'text-slate-500' : 'text-gray-400'}`}>{bc.tab} &gt; {r.docTitle || bc.group}</div>}
                      <div className={`text-sm font-semibold mb-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        <HighlightMatch text={r.text} query={query} />
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="px-5 py-10 text-center">
                <div className={`text-sm ${isDark ? 'text-slate-400' : 'text-gray-500'}`}>No results for "<span className="font-medium">{query}</span>"</div>
                <div className={`text-xs mt-1 ${isDark ? 'text-slate-500' : 'text-gray-400'}`}>Try different keywords</div>
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
    <button onClick={handleCopy} className={`flex items-center gap-2 px-3 py-1.5 ${theme.inputBg} rounded-lg text-sm ${theme.textMuted} ${theme.hoverText} transition-colors`} data-testid="copy-page-btn">
      {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
      <span>{copied ? 'Copied!' : 'Copy page'}</span>
      <ChevronDown className="w-3 h-3" />
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
        <span className={`text-sm ${submitted ? 'text-[#00A1B2]' : 'text-slate-400'}`} data-testid="feedback-thanks">
          {submitted ? 'Glad this helped!' : 'Thanks for letting us know. We\'ll improve this article.'}
        </span>
      )}
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
    if (!currentTab) return null;
    for (const group of currentTab.groups || []) {
      const page = group.pages?.find(p => (typeof p === 'string' ? p : p.page)?.toLowerCase() === selectedDoc?.slug?.toLowerCase());
      if (page) return group.group;
    }
    return currentTab.label;
  };

  const currentIndex = documents.findIndex(d => d.id === selectedDoc?.id);

  // Tab-scoped prev/next: navigate within the active tab's articles only
  const tabDocSlugs = useMemo(() => {
    const currentTab = tabs.find(t => t.id === activeTab);
    if (!currentTab) return [];
    const slugs = [];
    for (const group of currentTab.groups || []) {
      for (const page of group.pages || []) {
        slugs.push(typeof page === 'string' ? page : page.page);
      }
    }
    return slugs;
  }, [tabs, activeTab]);

  const tabDocIndex = tabDocSlugs.indexOf(selectedDoc?.slug);
  const prevDoc = tabDocIndex > 0 ? documents.find(d => d.slug === tabDocSlugs[tabDocIndex - 1]) : null;
  const nextDoc = tabDocIndex < tabDocSlugs.length - 1 ? documents.find(d => d.slug === tabDocSlugs[tabDocIndex + 1]) : null;

  if (loading) {
    return (
      <div className={`min-h-screen ${theme.bg} flex items-center justify-center`}>
        <div className="animate-spin w-8 h-8 border-2 border-[#00A1B2] border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${theme.bg} relative`} data-testid="kb-docs">

      <TopNavigation config={config} theme={theme} mobileMenuOpen={mobileMenuOpen} onMobileMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)} onThemeToggle={toggleKbTheme} isDark={isDark} onSearchOpen={() => setSearchOpen(true)} />
      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} documents={documents} onSelect={handleDocSelect} theme={theme} config={config} />
      <LeftSidebar activeTab={activeTab} tabs={tabs} documents={documents} selectedDocSlug={selectedDoc?.slug} onDocSelect={handleDocSelect} theme={theme} onSearchOpen={() => setSearchOpen(true)} mobileOpen={mobileMenuOpen} onMobileClose={() => setMobileMenuOpen(false)} />

      <main className="lg:ml-64 xl:mr-64 min-h-screen pt-14 relative z-10 overflow-x-hidden">
        {selectedDoc ? (
          <article key={selectedDoc.id} className="max-w-[800px] mx-auto px-4 sm:px-6 py-10 animate-fadeIn">
            <div className={`text-sm ${theme.textMuted} mb-4`} data-testid="kb-breadcrumb">{getBreadcrumb()}</div>
            <div className="flex items-start justify-between gap-4 mb-8">
              <h1 className={`text-3xl sm:text-4xl font-bold ${theme.text} tracking-tight`} data-testid="kb-page-title">{selectedDoc.title}</h1>
              <CopyButton text={window.location.href} theme={theme} />
            </div>
            <div className={`prose ${theme.proseClass} max-w-none overflow-hidden prose-headings:font-semibold prose-headings:text-inherit prose-h2:text-2xl prose-h2:mt-10 prose-h2:mb-4 prose-h3:text-xl prose-h3:mt-8 prose-h3:mb-3 prose-p:leading-7 prose-p:break-words prose-a:text-[#00A1B2] prose-a:no-underline hover:prose-a:underline prose-code:text-[#00A1B2] prose-code:bg-[#00A1B2]/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:break-words prose-pre:rounded-xl prose-pre:overflow-x-auto`} data-testid="kb-article-body">
              <DocContent content={selectedDoc.content?.replace(new RegExp(`^#\\s*${selectedDoc.title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\n+`, 'i'), '') || selectedDoc.content} onHeadings={setToc} />
            </div>
            <FeedbackWidget slug={selectedDoc.slug} theme={theme} />
            <div className={`flex flex-col sm:flex-row justify-between gap-4 mt-16 pt-8 border-t ${theme.border}`} data-testid="kb-prev-next">
              {prevDoc ? (
                <button onClick={() => handleDocSelect(prevDoc.slug)} className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${theme.border} ${theme.hover} transition-colors`} data-testid="prev-doc-btn">
                  <ArrowLeft className={`w-4 h-4 ${theme.navArrowColor}`} />
                  <div className="text-left"><span className={`block text-xs ${theme.navArrowColor}`}>Previous</span><span className={`text-sm font-medium ${theme.text}`}>{prevDoc.title}</span></div>
                </button>
              ) : <div />}
              {nextDoc && (
                <button onClick={() => handleDocSelect(nextDoc.slug)} className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${theme.border} ${theme.hover} transition-colors`} data-testid="next-doc-btn">
                  <div className="text-right"><span className={`block text-xs ${theme.navArrowColor}`}>Next</span><span className={`text-sm font-medium ${theme.text}`}>{nextDoc.title}</span></div>
                  <ArrowRight className={`w-4 h-4 ${theme.navArrowColor}`} />
                </button>
              )}
            </div>
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
        className={`fixed bottom-5 right-5 z-[9999] flex items-center gap-2.5 px-3.5 py-2 rounded-[10px] no-underline shadow-lg transition-all hover:scale-105`}
        style={{ background: theme.badgeBg, border: theme.badgeBorder }}
        data-testid="made-with-emergent-badge"
      >
        <img src="https://avatars.githubusercontent.com/in/1201222?s=120&u=2686cf91179bbafbc7a71bfbc43004cf9ae1acea&v=4" alt="" className="w-[22px] h-[22px] rounded" />
        <span className={`${theme.badgeText} text-sm font-medium tracking-[0.01em]`}>Made with Emergent</span>
      </a>
    </div>
  );
};

export default PublicDocs;
