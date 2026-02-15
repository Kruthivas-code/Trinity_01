import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Search, CreditCard, Receipt, Globe, Boxes, UserCog, ShieldCheck, Rocket, Bot, Database, Smartphone, ArrowRight, ChevronRight } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const ICON_MAP = {
  CreditCard, Receipt, Globe, Boxes, UserCog, ShieldCheck,
  Rocket, Bot, Database, Smartphone,
};

const PortalHome = () => {
  const [categories, setCategories] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/portal/categories`)
      .then(r => r.json())
      .then(d => { setCategories(d.categories || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const filtered = search.trim()
    ? categories.filter(c =>
        c.title.toLowerCase().includes(search.toLowerCase()) ||
        c.description?.toLowerCase().includes(search.toLowerCase()) ||
        c.subtopics?.some(s => s.name.toLowerCase().includes(search.toLowerCase()))
      )
    : categories;

  const totalSubtopics = (cat) => cat.subtopics?.length || 0;

  return (
    <div data-testid="portal-home">
      {/* Hero */}
      <div className="pt-16 pb-12 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <p className="text-[11px] font-mono uppercase tracking-[0.25em] text-muted-foreground mb-4">
            Support Center
          </p>
          <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-foreground mb-4">
            How can we help?
          </h1>
          <p className="text-base text-muted-foreground mb-8 max-w-md mx-auto">
            Search our knowledge base or browse categories below
          </p>

          {/* Search */}
          <div className="relative max-w-lg mx-auto">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="search_topics()..."
              className="w-full h-11 pl-11 pr-4 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/40 placeholder:font-mono focus:outline-none focus:ring-1 focus:ring-foreground/20 focus:border-foreground/30 transition-all"
              data-testid="portal-search"
            />
          </div>
        </div>
      </div>

      {/* Category Grid */}
      <div className="max-w-4xl mx-auto px-6 pb-16">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-32 rounded-lg bg-muted/30 animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-muted-foreground text-sm">No matching categories found</p>
            <Link to="/portal/submit" className="text-sm text-foreground underline underline-offset-4 mt-2 inline-block">
              Submit a ticket instead
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filtered.map(cat => {
              const Icon = ICON_MAP[cat.icon] || Boxes;
              return (
                <Link
                  key={cat.slug}
                  to={`/portal/category/${cat.slug}`}
                  className="group p-5 rounded-lg border border-border/50 bg-card hover:border-foreground/20 hover:shadow-sm transition-all"
                  data-testid={`category-card-${cat.slug}`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="h-9 w-9 rounded-md bg-muted/50 flex items-center justify-center text-muted-foreground group-hover:text-foreground group-hover:bg-muted transition-colors">
                      <Icon size={18} strokeWidth={1.5} />
                    </div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/50">
                      {totalSubtopics(cat)} topics
                    </span>
                  </div>
                  <h3 className="text-sm font-medium text-foreground mb-1 group-hover:translate-x-0.5 transition-transform">
                    {cat.title}
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                    {cat.description}
                  </p>
                  <div className="mt-3 flex items-center gap-1 text-[10px] font-medium text-muted-foreground/40 group-hover:text-foreground/60 transition-colors">
                    <span className="font-mono">explore</span>
                    <ChevronRight size={10} />
                  </div>
                </Link>
              );
            })}
          </div>
        )}

        {/* CTA */}
        <div className="mt-12 text-center">
          <p className="text-sm text-muted-foreground mb-3">Can't find what you're looking for?</p>
          <Link
            to="/portal/submit"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity"
            data-testid="portal-submit-cta"
          >
            Submit a ticket
            <ArrowRight size={14} />
          </Link>
        </div>
      </div>
    </div>
  );
};

export default PortalHome;
