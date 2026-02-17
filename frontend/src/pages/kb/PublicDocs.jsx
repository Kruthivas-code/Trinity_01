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
  ThumbsUp, ThumbsDown
} from 'lucide-react';
import { DocContent } from '../../components/docs/DocContent';
import { getIcon } from '../../components/docs/IconPicker';
import { search, initializeSearch } from '../../lib/search';
import './PublicDocs.css';

const API = process.env.REACT_APP_BACKEND_URL;

const THEMES = {
  dark: {
    bg: 'bg-[#0a0a0a]',
    navBg: 'bg-[#0a0a0a]',
    sidebarBg: 'bg-[#0a0a0a]',
    text: 'text-white',
    textMuted: 'text-slate-400',
    textSecondary: 'text-slate-500',
    border: 'border-white/10',
    hover: 'hover:bg-white/5',
    activeBg: 'bg-white/10',
    activeText: 'text-white',
    inputBg: 'bg-white/5 border border-white/10',
  },
};

// ============= TOP NAVIGATION =============
const TopNavigation = ({ config, tabs, activeTab, onTabChange, theme, mobileMenuOpen, onMobileMenuToggle }) => {
  const navbar = config?.navbar || {};
  const links = navbar.links || [];
  const primaryCta = navbar.primary || { label: 'Try Emergent', href: 'https://app.emergent.sh' };

  return (
    <header className={`fixed top-0 left-0 right-0 z-50 ${theme.navBg} border-b ${theme.border}`} data-testid="kb-header">
      <div className="h-14 px-4 sm:px-6 flex items-center">
        <a href="https://app.emergent.sh" className="flex items-center gap-2 flex-shrink-0 mr-4 lg:mr-8" data-testid="logo-link">
          <img src="/images/emergent-logo-dark.png" alt="Emergent" className="h-6" />
        </a>

        <nav className="hidden lg:flex items-center gap-1 flex-1 justify-center" data-testid="kb-top-nav">
          {tabs.map((tab) => {
            const TabIcon = tab.icon ? getIcon(tab.icon) : null;
            const isActive = activeTab === tab.id;
            return (
              <button key={tab.id} onClick={() => onTabChange(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${isActive ? `${theme.activeBg} ${theme.activeText}` : `${theme.textMuted} ${theme.hover}`}`}
                data-testid={`tab-${tab.id}`}>
                {TabIcon && <TabIcon className="w-4 h-4" />}
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="flex items-center gap-3 sm:gap-4 ml-auto">
          <Link to="/portal"
            className="flex items-center gap-1.5 px-3 sm:px-4 py-2 bg-[#188455] hover:bg-[#157149] text-white text-sm font-medium rounded-lg transition-colors"
            data-testid="cta-button">
            <span>Get more help</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <button className={`lg:hidden p-2 rounded-lg ${theme.hover} ${theme.text}`} onClick={onMobileMenuToggle} data-testid="mobile-nav-toggle">
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </header>
  );
};

// ============= LEFT SIDEBAR =============
const LeftSidebar = ({ activeTab, tabs, documents, selectedDocSlug, onDocSelect, onTabChange, theme, onSearchOpen, mobileOpen, onMobileClose }) => {
  const currentTab = tabs.find(t => t.id === activeTab) || tabs[0];
  const groups = currentTab?.groups || [];

  return (
    <>
      {mobileOpen && <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={onMobileClose} />}
      <aside className={`fixed top-14 bottom-0 left-0 z-40 w-72 lg:w-64 ${theme.sidebarBg} border-r ${theme.border} transform transition-transform duration-300 lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'} flex flex-col`} data-testid="kb-sidebar">
        {tabs.length > 1 && (
          <div className="lg:hidden border-b border-white/10 p-3">
            <div className="flex flex-wrap gap-2">
              {tabs.map((tab) => {
                const TabIcon = tab.icon ? getIcon(tab.icon) : null;
                const isActive = activeTab === tab.id;
                return (
                  <button key={tab.id} onClick={() => onTabChange(tab.id)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${isActive ? 'bg-[#188455] text-white' : `${theme.textMuted} ${theme.hover}`}`}>
                    {TabIcon && <TabIcon className="w-4 h-4" />}
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div className="p-4">
          <button onClick={onSearchOpen} className={`w-full flex items-center gap-3 px-3 py-2.5 ${theme.inputBg} rounded-lg text-sm ${theme.textMuted} transition-colors`} data-testid="sidebar-search">
            <Search className="w-4 h-4" />
            <span className="flex-1 text-left">Search...</span>
            <kbd className="px-1.5 py-0.5 text-xs rounded bg-white/10 text-slate-400">&#8984;K</kbd>
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 pb-4" data-testid="kb-nav-tree">
          {groups.map((group, gi) => (
            <div key={gi} className="mb-6">
              <h3 className={`px-3 mb-2 text-sm font-semibold ${theme.text}`}>{group.group}</h3>
              <div className="space-y-0.5">
                {group.pages?.map((page, pi) => {
                  const pageSlug = typeof page === 'string' ? page : page.page;
                  const doc = documents.find(d => d.slug?.toLowerCase() === pageSlug?.toLowerCase());
                  const title = typeof page === 'string' ? doc?.title || page : page.title || page.page;
                  const pageIcon = typeof page === 'object' ? page.icon : null;
                  const PageIcon = pageIcon ? getIcon(pageIcon) : null;
                  const isActive = pageSlug?.toLowerCase() === selectedDocSlug?.toLowerCase();
                  const isMissing = !doc;

                  return (
                    <button key={pi} onClick={() => { if (!isMissing) { onDocSelect(pageSlug); onMobileClose(); } }} disabled={isMissing}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${isActive ? `${theme.activeBg} ${theme.activeText} border-l-2 border-[#188455] -ml-[2px] pl-[14px]` : isMissing ? 'text-slate-600 cursor-not-allowed' : `${theme.textMuted} ${theme.hover}`}`}
                      data-testid={`sidebar-page-${pageSlug}`}>
                      {PageIcon && <PageIcon className={`w-4 h-4 flex-shrink-0 ${isMissing ? 'opacity-50' : ''}`} />}
                      <span className={`truncate ${isMissing ? 'italic opacity-50' : ''}`}>{title}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
        <div className="p-4" />
      </aside>
    </>
  );
};

// ============= RIGHT SIDEBAR (TOC) =============
const RightSidebar = ({ headings, theme }) => {
  const [activeId, setActiveId] = useState('');
  const [validHeadings, setValidHeadings] = useState([]);

  useEffect(() => {
    const existing = headings.filter(h => document.getElementById(h.id));
    setValidHeadings(existing);
  }, [headings]);

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
    <aside className="hidden xl:block fixed top-14 right-0 bottom-0 w-56 overflow-y-auto z-10 border-l border-slate-800/50" data-testid="kb-toc">
      <div className="p-4">
        <h4 className={`text-xs font-semibold ${theme.text} mb-3 uppercase tracking-wider`}>On this page</h4>
        <nav className="space-y-0.5">
          {validHeadings.map((h) => (
            <a key={h.id} href={`#${h.id}`}
              className={`block py-1 text-[13px] leading-snug transition-colors break-words ${activeId === h.id ? `${theme.text} font-medium` : `${theme.textMuted} hover:text-white`}`}
              style={{ paddingLeft: `${(h.level - 2) * 8}px` }}>
              {h.text}
            </a>
          ))}
        </nav>
      </div>
    </aside>
  );
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
          if (ps?.toLowerCase() === slug?.toLowerCase()) return `${tab.label} > ${group.group}`;
        }
      }
    }
    return null;
  };

  useEffect(() => { if (open) { setQuery(''); setResults({ documents: [], headings: [] }); setTimeout(() => inputRef.current?.focus(), 100); } }, [open]);
  useEffect(() => { if (query.length >= 2) setResults(search(query)); else setResults({ documents: [], headings: [] }); }, [query]);
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape' && open) onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;
  const hasResults = results.documents?.length > 0 || results.headings?.length > 0;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[10vh]">
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-2xl mx-4 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-4 border-b border-slate-700">
          <Search className="w-5 h-5 text-slate-400" />
          <input ref={inputRef} type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search documentation..."
            className="flex-1 bg-transparent text-white text-lg placeholder:text-slate-500 outline-none" data-testid="search-input" />
          <kbd className="px-2 py-1 text-xs text-slate-400 bg-slate-800 rounded border border-slate-700">ESC</kbd>
        </div>
        <div className="max-h-[60vh] overflow-auto">
          {hasResults ? (
            <div className="p-2">
              {results.documents?.map((r, i) => {
                const bc = getBreadcrumb(r.slug);
                return (
                  <button key={`d-${i}`} onClick={() => { onSelect(r.slug); onClose(); }} className="w-full text-left px-4 py-3 rounded-lg hover:bg-slate-800 transition-colors group">
                    {bc && <div className="text-xs text-slate-500 mb-1">{bc}</div>}
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500 text-sm">#</span>
                      <span className="font-medium text-white group-hover:text-emerald-400 transition-colors">{r.title}</span>
                    </div>
                    {r.snippet && <div className="text-sm text-slate-400 mt-1 line-clamp-2 pl-5">{r.snippet}</div>}
                  </button>
                );
              })}
              {results.headings?.map((r, i) => {
                const bc = getBreadcrumb(r.slug);
                return (
                  <button key={`h-${i}`} onClick={() => { onSelect(r.slug); onClose(); setTimeout(() => { const el = document.getElementById(r.anchor); if (el) el.scrollIntoView({ behavior: 'smooth' }); }, 300); }}
                    className="w-full text-left px-4 py-3 rounded-lg hover:bg-slate-800 transition-colors group">
                    {bc && <div className="text-xs text-slate-500 mb-1">{bc} &gt; {r.docTitle}</div>}
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500 text-sm">{'#'.repeat(r.level || 1)}</span>
                      <span className="font-medium text-white group-hover:text-emerald-400 transition-colors">{r.text}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : query.length >= 2 ? (
            <div className="px-4 py-12 text-center"><div className="text-slate-400 mb-2">No results for "{query}"</div><div className="text-sm text-slate-500">Try different keywords</div></div>
          ) : (
            <div className="px-4 py-12 text-center"><div className="text-slate-400 mb-2">Search documentation</div><div className="text-sm text-slate-500">Type at least 2 characters</div></div>
          )}
        </div>
      </div>
    </div>
  );
};

// ============= COPY BUTTON =============
const CopyButton = ({ text, theme }) => {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  return (
    <button onClick={handleCopy} className={`flex items-center gap-2 px-3 py-1.5 ${theme.inputBg} rounded-lg text-sm ${theme.textMuted} hover:text-white transition-colors`} data-testid="copy-page-btn">
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
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${theme.border} text-sm ${theme.textMuted} hover:text-emerald-400 hover:border-emerald-500/40 transition-all`}
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
        <span className={`text-sm ${submitted ? 'text-emerald-400' : 'text-slate-400'}`} data-testid="feedback-thanks">
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

  const theme = THEMES.dark;

  const tabs = useMemo(() => {
    const rawTabs = config?.navigation?.tabs || [];
    return rawTabs.length > 0
      ? rawTabs.map(t => ({ id: t.id || t.label, label: t.label || t.id, icon: t.icon, groups: t.groups || [] }))
      : [{ id: 'docs', label: 'Documentation', groups: documents.length > 0 ? [{ group: 'Documentation', pages: documents.map(d => ({ page: d.slug, title: d.title })) }] : [] }];
  }, [config?.navigation, documents]);

  useEffect(() => { document.documentElement.classList.add('dark'); }, []);

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

  const handleTabChange = useCallback((tabId) => {
    if (isNavigating) return;
    setActiveTab(tabId);
    const tab = tabs.find(t => t.id === tabId);
    if (tab?.groups) {
      for (const group of tab.groups) {
        if (group.pages?.length > 0) {
          const slug = typeof group.pages[0] === 'string' ? group.pages[0] : group.pages[0].page;
          const doc = documents.find(d => d.slug?.toLowerCase() === slug?.toLowerCase());
          if (doc && doc.id !== selectedDoc?.id) {
            setIsNavigating(true);
            setSelectedDoc(doc);
            requestAnimationFrame(() => { navigate(`/docs/${doc.slug}`); setTimeout(() => setIsNavigating(false), 100); });
            return;
          }
        }
      }
    }
  }, [tabs, documents, navigate, selectedDoc, isNavigating]);

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
        <div className="animate-spin w-8 h-8 border-2 border-[#188455] border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${theme.bg} relative`} data-testid="kb-docs">
      <div className="fixed inset-0 pointer-events-none z-0 bg-grid-pattern" />
      <div className="fixed inset-0 pointer-events-none z-0 bg-hero-glow" />

      <TopNavigation config={config} tabs={tabs} activeTab={activeTab} onTabChange={handleTabChange} theme={theme} mobileMenuOpen={mobileMenuOpen} onMobileMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)} />
      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} documents={documents} onSelect={handleDocSelect} theme={theme} config={config} />
      <LeftSidebar activeTab={activeTab} tabs={tabs} documents={documents} selectedDocSlug={selectedDoc?.slug} onDocSelect={handleDocSelect} onTabChange={handleTabChange} theme={theme} onSearchOpen={() => setSearchOpen(true)} mobileOpen={mobileMenuOpen} onMobileClose={() => setMobileMenuOpen(false)} />

      <main className="lg:ml-64 xl:mr-56 min-h-screen pt-14 relative z-10">
        {selectedDoc ? (
          <article key={selectedDoc.id} className="max-w-none xl:max-w-3xl mx-auto px-4 sm:px-6 py-10 animate-fadeIn">
            <div className={`text-sm ${theme.textMuted} mb-4`} data-testid="kb-breadcrumb">{getBreadcrumb()}</div>
            <div className="flex items-start justify-between gap-4 mb-8">
              <h1 className={`text-3xl sm:text-4xl font-bold ${theme.text} tracking-tight`} data-testid="kb-page-title">{selectedDoc.title}</h1>
              <CopyButton text={window.location.href} theme={theme} />
            </div>
            <div className="prose prose-invert max-w-none prose-headings:font-semibold prose-headings:text-inherit prose-h2:text-2xl prose-h2:mt-10 prose-h2:mb-4 prose-h3:text-xl prose-h3:mt-8 prose-h3:mb-3 prose-p:leading-7 prose-p:break-words prose-a:text-[#188455] prose-a:no-underline hover:prose-a:underline prose-code:text-[#188455] prose-code:bg-[#188455]/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:break-words prose-pre:bg-slate-900 prose-pre:border prose-pre:border-white/10 prose-pre:rounded-xl prose-pre:overflow-x-auto" data-testid="kb-article-body">
              <DocContent content={selectedDoc.content?.replace(new RegExp(`^#\\s*${selectedDoc.title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\n+`, 'i'), '') || selectedDoc.content} onHeadings={setToc} />
            </div>
            <div className={`flex flex-col sm:flex-row justify-between gap-4 mt-16 pt-8 border-t ${theme.border}`} data-testid="kb-prev-next">
              {prevDoc ? (
                <button onClick={() => handleDocSelect(prevDoc.slug)} className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${theme.border} ${theme.hover} transition-colors`} data-testid="prev-doc-btn">
                  <ArrowLeft className="w-4 h-4 text-slate-500" />
                  <div className="text-left"><span className="block text-xs text-slate-500">Previous</span><span className={`text-sm font-medium ${theme.text}`}>{prevDoc.title}</span></div>
                </button>
              ) : <div />}
              {nextDoc && (
                <button onClick={() => handleDocSelect(nextDoc.slug)} className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${theme.border} ${theme.hover} transition-colors`} data-testid="next-doc-btn">
                  <div className="text-right"><span className="block text-xs text-slate-500">Next</span><span className={`text-sm font-medium ${theme.text}`}>{nextDoc.title}</span></div>
                  <ArrowRight className="w-4 h-4 text-slate-500" />
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
        className="fixed bottom-5 right-5 z-[9999] flex items-center gap-2.5 px-3.5 py-2 rounded-[10px] no-underline shadow-lg transition-all hover:scale-105"
        style={{ background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)', border: '1px solid rgba(255,255,255,0.1)' }}
        data-testid="made-with-emergent-badge"
      >
        <img src="https://avatars.githubusercontent.com/in/1201222?s=120&u=2686cf91179bbafbc7a71bfbc43004cf9ae1acea&v=4" alt="" className="w-[22px] h-[22px] rounded" />
        <span className="text-slate-200 text-sm font-medium tracking-[0.01em]">Made with Emergent</span>
      </a>
    </div>
  );
};

export default PublicDocs;
