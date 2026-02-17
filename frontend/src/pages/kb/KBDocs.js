import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Search, ChevronRight, ChevronLeft, ChevronDown, Moon, Sun, Menu, X, BookOpen, Copy, Check, ArrowRight } from 'lucide-react';
import './KBDocs.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// ── Sidebar icons for nav groups (top nav) ──
const NAV_ICONS = {
  'beginners-guide': (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
  ),
  'features': (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
  ),
  'building-your-app': (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
  ),
  'deploy-and-manage': (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
  ),
  'troubleshooting': (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
  ),
};

// ── Per-article sidebar icons (matching help.emergent.sh) ──
const ARTICLE_ICONS = {
  'welcome': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>,
  'first-app': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>,
  'plans-and-credits': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>,
  'faqs': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
  'how-apps-work': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>,
  'voice-mode': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>,
  'github-integration': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/></svg>,
  'universal-key': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>,
  'deployment-on-emergent': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>,
  'context-limits': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  'mobile-app-development': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>,
  'teams-plan-collaboration': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>,
  'deployment-types': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>,
  'rollback-feature': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>,
  'forking-in-emergent': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9v1a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V9"/><line x1="12" y1="12" x2="12" y2="15"/></svg>,
  'mcp-model-context-protocol': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>,
  'prompting-basics': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>,
  'pre-deployment-health-check': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>,
  'fixing-design-inconsistencies': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>,
  'missing-app-functionality': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
  'deployment-related-issues': <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>,
};

const defaultArticleIcon = <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>;

// ── Markdown renderer (lightweight, Mintlify-compatible) ──
const renderMarkdown = (md) => {
  if (!md) return null;
  const lines = md.split('\n');
  const elements = [];
  let inCodeBlock = false;
  let codeLines = [];
  let listItems = [];
  let blockquoteLines = [];

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} className="kb-list">
          {listItems.map((li, i) => <li key={i}>{li}</li>)}
        </ul>
      );
      listItems = [];
    }
  };

  const flushBlockquote = () => {
    if (blockquoteLines.length > 0) {
      const text = blockquoteLines.join(' ');
      const isInfo = text.toLowerCase().startsWith('info');
      const isWarning = text.toLowerCase().startsWith('warning');
      const isSuccess = text.toLowerCase().startsWith('success');
      const type = isWarning ? 'warning' : isSuccess ? 'success' : 'info';
      const content = isInfo || isWarning || isSuccess ? text.replace(/^(info|warning|success)\s*/i, '') : text;
      elements.push(
        <div key={`bq-${elements.length}`} className={`kb-callout kb-callout-${type}`}>
          <div className="kb-callout-title">{type.charAt(0).toUpperCase() + type.slice(1)}</div>
          <div>{content}</div>
        </div>
      );
      blockquoteLines = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${elements.length}`} className="kb-code-block">
            <code>{codeLines.join('\n')}</code>
          </pre>
        );
        codeLines = [];
        inCodeBlock = false;
      } else {
        flushList();
        flushBlockquote();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    if (line.startsWith('> ')) {
      flushList();
      blockquoteLines.push(line.slice(2));
      continue;
    } else {
      flushBlockquote();
    }

    if (line.startsWith('- ') || line.startsWith('* ')) {
      listItems.push(line.slice(2));
      continue;
    } else {
      flushList();
    }

    if (line.startsWith('#### ')) {
      elements.push(<h4 key={`h4-${i}`} className="kb-h4" id={line.slice(5).toLowerCase().replace(/[^\w]+/g, '-')}>{line.slice(5)}</h4>);
    } else if (line.startsWith('### ')) {
      elements.push(<h3 key={`h3-${i}`} className="kb-h3" id={line.slice(4).toLowerCase().replace(/[^\w]+/g, '-')}>{line.slice(4)}</h3>);
    } else if (line.startsWith('## ')) {
      elements.push(<h2 key={`h2-${i}`} className="kb-h2" id={line.slice(3).toLowerCase().replace(/[^\w]+/g, '-')}>{line.slice(3)}</h2>);
    } else if (line.startsWith('# ')) {
      // Skip h1 — already rendered as page title
    } else if (line.trim()) {
      elements.push(<p key={`p-${i}`} className="kb-paragraph">{line}</p>);
    }
  }

  flushList();
  flushBlockquote();

  return elements;
};

// ── TOC from markdown headings ──
const extractTOC = (md) => {
  if (!md) return [];
  return md.split('\n')
    .filter(l => l.match(/^#{2,3} /))
    .map(l => {
      const level = l.startsWith('### ') ? 3 : 2;
      const text = l.replace(/^#{2,4} /, '');
      const id = text.toLowerCase().replace(/[^\w]+/g, '-');
      return { level, text, id };
    });
};


// ── Article with Copy Page button ──
const CopyPageArticle = ({ article, prevNext }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(article.content_markdown || '');
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) { console.error(e); }
  };

  return (
    <>
      <div className="kb-breadcrumb" data-testid="kb-breadcrumb">
        <span>{article.section_label}</span>
      </div>
      <div className="kb-title-row">
        <h1 className="kb-page-title" data-testid="kb-page-title">{article.title}</h1>
        <button onClick={handleCopy} className="kb-copy-btn" data-testid="kb-copy-page">
          {copied ? <Check size={14} /> : <Copy size={14} />}
          <span>{copied ? 'Copied!' : 'Copy page'}</span>
          {!copied && <ChevronDown size={12} />}
        </button>
      </div>
      <div className="kb-article-body" data-testid="kb-article-body">
        {renderMarkdown(article.content_markdown)}
      </div>
      <div className="kb-prev-next" data-testid="kb-prev-next">
        {prevNext.prev ? (
          <Link to={`/docs/${prevNext.prev.slug}`} className="kb-prev-next-link prev">
            <ChevronLeft size={16} />
            <div>
              <span className="kb-prev-next-label">Previous</span>
              <span className="kb-prev-next-title">{prevNext.prev.title}</span>
            </div>
          </Link>
        ) : <div />}
        {prevNext.next ? (
          <Link to={`/docs/${prevNext.next.slug}`} className="kb-prev-next-link next">
            <div>
              <span className="kb-prev-next-label">Next</span>
              <span className="kb-prev-next-title">{prevNext.next.title}</span>
            </div>
            <ChevronRight size={16} />
          </Link>
        ) : <div />}
      </div>
    </>
  );
};


const KBDocs = () => {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [nav, setNav] = useState([]);
  const [articles, setArticles] = useState([]);
  const [article, setArticle] = useState(null);
  const [prevNext, setPrevNext] = useState({ prev: null, next: null });
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('kb-theme') === 'dark');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  // Fetch nav and articles on mount
  useEffect(() => {
    const init = async () => {
      try {
        const [navRes, artRes] = await Promise.all([
          fetch(`${BACKEND_URL}/api/kb/navigation`),
          fetch(`${BACKEND_URL}/api/kb/articles`),
        ]);
        const navData = await navRes.json();
        const artData = await artRes.json();
        setNav(navData.nav_groups || []);
        setArticles(artData.articles || []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  // Fetch article content when slug changes
  useEffect(() => {
    if (!slug) {
      setArticle(null);
      return;
    }
    const fetchArticle = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/kb/articles/${slug}`);
        if (res.ok) {
          const data = await res.json();
          setArticle(data.article);
          setPrevNext({ prev: data.prev, next: data.next });
        }
      } catch (e) {
        console.error(e);
      }
    };
    fetchArticle();
    setSidebarOpen(false);
    window.scrollTo(0, 0);
  }, [slug]);

  // Search
  const handleSearch = useCallback(async (q) => {
    setSearchQuery(q);
    if (q.length < 2) {
      setSearchResults([]);
      setSearching(false);
      return;
    }
    setSearching(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/kb/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      setSearchResults(data.results || []);
    } catch (e) {
      console.error(e);
    } finally {
      setSearching(false);
    }
  }, []);

  // Theme toggle
  useEffect(() => {
    document.documentElement.classList.toggle('kb-dark', darkMode);
    localStorage.setItem('kb-theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  // Build sidebar tree: only current nav group's sections
  const activeGroupKey = article?.nav_group_key || (articles[0]?.nav_group_key) || '';
  const activeGroup = nav.find(g => g.key === activeGroupKey);
  const sidebarSections = activeGroup ? activeGroup.sections.map(sec => ({
    ...sec,
    articles: articles.filter(a => a.section_key === sec.key && a.nav_group_key === activeGroupKey),
  })) : [];

  const toc = article ? extractTOC(article.content_markdown) : [];

  // Default to first article if no slug
  useEffect(() => {
    if (!slug && articles.length > 0 && !loading) {
      navigate(`/docs/${articles[0].slug}`, { replace: true });
    }
  }, [slug, articles, loading, navigate]);

  if (loading) {
    return (
      <div className="kb-root" data-testid="kb-loading">
        <div className="kb-loading">Loading documentation...</div>
      </div>
    );
  }

  return (
    <div className={`kb-root ${darkMode ? 'kb-dark' : ''}`} data-testid="kb-docs">
      {/* Top Nav */}
      <header className="kb-header" data-testid="kb-header">
        <div className="kb-header-inner">
          <div className="kb-header-left">
            <button className="kb-mobile-menu" onClick={() => setSidebarOpen(!sidebarOpen)} data-testid="kb-mobile-menu">
              {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <Link to="/docs" className="kb-logo" data-testid="kb-logo">
              <div className="kb-logo-icon">E</div>
              <span>Docs</span>
            </Link>
          </div>

          <nav className="kb-top-nav" data-testid="kb-top-nav">
            {nav.map(group => (
              <button
                key={group.key}
                onClick={() => {
                  const firstArt = articles.find(a => a.nav_group_key === group.key);
                  if (firstArt) navigate(`/docs/${firstArt.slug}`);
                }}
                className={`kb-top-nav-item ${article?.nav_group_key === group.key ? 'active' : ''}`}
                data-testid={`kb-nav-${group.key}`}
              >
                {NAV_ICONS[group.key]}
                <span>{group.label}</span>
              </button>
            ))}
          </nav>

          <div className="kb-header-right">
            <Link to="/portal/categories" className="kb-nav-link" data-testid="kb-support-link">Help</Link>
            <button onClick={() => setDarkMode(!darkMode)} className="kb-theme-btn" data-testid="kb-theme-toggle">
              {darkMode ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <a href="https://app.emergent.sh" target="_blank" rel="noopener noreferrer" className="kb-try-btn" data-testid="kb-try-btn">
              Try Emergent <ArrowRight size={14} />
            </a>
          </div>
        </div>
      </header>

      <div className="kb-body">
        {/* Sidebar */}
        <aside className={`kb-sidebar ${sidebarOpen ? 'open' : ''}`} data-testid="kb-sidebar">
          {/* Search */}
          <div className="kb-search-wrap">
            <Search size={14} className="kb-search-icon" />
            <input
              value={searchQuery}
              onChange={e => handleSearch(e.target.value)}
              placeholder="Search..."
              className="kb-search-input"
              data-testid="kb-search-input"
            />
            <kbd className="kb-search-kbd">K</kbd>
          </div>

          {/* Search Results */}
          {searchQuery.length >= 2 && (
            <div className="kb-search-results" data-testid="kb-search-results">
              {searching ? (
                <div className="kb-search-loading">Searching...</div>
              ) : searchResults.length > 0 ? (
                searchResults.map(r => (
                  <Link
                    key={r.slug}
                    to={`/docs/${r.slug}`}
                    className="kb-search-result"
                    onClick={() => { setSearchQuery(''); setSearchResults([]); }}
                  >
                    <span className="kb-search-result-title">{r.title}</span>
                    <span className="kb-search-result-section">{r.section_label}</span>
                  </Link>
                ))
              ) : (
                <div className="kb-search-empty">No results found</div>
              )}
            </div>
          )}

          {/* Nav Tree - shows only active nav group's sections */}
          <nav className="kb-nav-tree" data-testid="kb-nav-tree">
            {sidebarSections.map(sec => (
              <div key={sec.key} className="kb-nav-section">
                <div className="kb-nav-section-label">{sec.label}</div>
                {sec.articles.map(a => (
                  <Link
                    key={a.slug}
                    to={`/docs/${a.slug}`}
                    className={`kb-nav-item ${article?.slug === a.slug ? 'active' : ''}`}
                    data-testid={`kb-sidebar-${a.slug}`}
                  >
                    <span className="kb-nav-item-icon">{ARTICLE_ICONS[a.slug] || defaultArticleIcon}</span>
                    {a.title}
                  </Link>
                ))}
              </div>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="kb-content" data-testid="kb-content">
          {article ? (
            <CopyPageArticle article={article} prevNext={prevNext} />
          ) : (
            <div className="kb-empty">
              <BookOpen size={48} strokeWidth={1} />
              <h2>Documentation</h2>
              <p>Select an article from the sidebar</p>
            </div>
          )}
        </main>

        {/* TOC (right sidebar) */}
        {article && toc.length > 0 && (
          <aside className="kb-toc" data-testid="kb-toc">
            <div className="kb-toc-title">ON THIS PAGE</div>
            {toc.map((item, i) => (
              <a
                key={i}
                href={`#${item.id}`}
                className={`kb-toc-item ${item.level === 3 ? 'sub' : ''}`}
              >
                {item.text}
              </a>
            ))}
          </aside>
        )}
      </div>

      {/* Footer */}
      <div className="kb-footer" data-testid="kb-footer">
        <a href="https://app.emergent.sh" target="_blank" rel="noopener noreferrer" className="kb-footer-badge">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
          Made with Emergent
        </a>
      </div>
    </div>
  );
};

export default KBDocs;
