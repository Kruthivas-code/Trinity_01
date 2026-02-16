import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Search, ChevronRight, ChevronLeft, Moon, Sun, ExternalLink, Menu, X, BookOpen } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// ── Sidebar icons for nav groups ──
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

  // Build sidebar tree: nav_group > section > articles
  const sidebarTree = nav.map(group => ({
    ...group,
    sections: group.sections.map(sec => ({
      ...sec,
      articles: articles.filter(a => a.section_key === sec.key),
    })),
  }));

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
            <Link to="/portal/categories" className="kb-nav-link" data-testid="kb-support-link">Support</Link>
            <button onClick={() => setDarkMode(!darkMode)} className="kb-theme-btn" data-testid="kb-theme-toggle">
              {darkMode ? <Sun size={16} /> : <Moon size={16} />}
            </button>
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

          {/* Nav Tree */}
          <nav className="kb-nav-tree" data-testid="kb-nav-tree">
            {sidebarTree.map(group => (
              <div key={group.key} className="kb-nav-group">
                {group.sections.map(sec => (
                  <div key={sec.key} className="kb-nav-section">
                    <div className="kb-nav-section-label">{sec.label}</div>
                    {sec.articles.map(a => (
                      <Link
                        key={a.slug}
                        to={`/docs/${a.slug}`}
                        className={`kb-nav-item ${article?.slug === a.slug ? 'active' : ''}`}
                        data-testid={`kb-sidebar-${a.slug}`}
                      >
                        {a.title}
                      </Link>
                    ))}
                  </div>
                ))}
              </div>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="kb-content" data-testid="kb-content">
          {article ? (
            <>
              <div className="kb-breadcrumb" data-testid="kb-breadcrumb">
                <span>{article.nav_group_label}</span>
              </div>
              <h1 className="kb-page-title" data-testid="kb-page-title">{article.title}</h1>
              <div className="kb-article-body" data-testid="kb-article-body">
                {renderMarkdown(article.content_markdown)}
              </div>

              {/* Prev/Next Navigation */}
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
    </div>
  );
};

export default KBDocs;
