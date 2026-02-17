import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ChevronRight, ExternalLink, CreditCard, Receipt, Globe, Boxes, UserCog, ShieldCheck, Rocket, Bot, Database, Smartphone } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const ICON_MAP = {
  CreditCard, Receipt, Globe, Boxes, UserCog, ShieldCheck,
  Rocket, Bot, Database, Smartphone,
};

const HELP_BASE = 'https://help.emergent.sh';

const PortalCategory = () => {
  const { slug } = useParams();
  const [category, setCategory] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/portal/categories/${slug}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(d => { setCategory(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16">
        <div className="h-8 w-48 bg-muted/30 rounded animate-pulse mb-4" />
        <div className="h-4 w-96 bg-muted/30 rounded animate-pulse mb-8" />
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => <div key={i} className="h-14 bg-muted/20 rounded-lg animate-pulse" />)}
        </div>
      </div>
    );
  }

  if (!category) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center">
        <p className="text-muted-foreground">Category not found</p>
        <Link to="/portal" className="text-sm text-foreground underline underline-offset-4 mt-2 inline-block">Back to home</Link>
      </div>
    );
  }

  const Icon = ICON_MAP[category.icon] || Boxes;

  return (
    <div className="max-w-3xl mx-auto px-6 py-10" data-testid="portal-category-page">
      {/* Back */}
      <Link to="/" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mb-8" data-testid="category-back-link">
        <ArrowLeft size={12} />
        <span className="font-mono">back</span>
      </Link>

      {/* Header */}
      <div className="flex items-start gap-4 mb-8">
        <div className="h-11 w-11 rounded-lg bg-muted/50 flex items-center justify-center text-foreground shrink-0">
          <Icon size={22} strokeWidth={1.5} />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-foreground mb-1">{category.title}</h1>
          <p className="text-sm text-muted-foreground">{category.description}</p>
        </div>
      </div>

      {/* Help Articles */}
      {category.help_articles?.length > 0 && (
        <div className="mt-8 mb-2">
          <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/50 mb-3">
            Related Docs
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {category.help_articles.map((article, i) => (
              <a
                key={i}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg border border-border/30 bg-card hover:border-foreground/20 hover:shadow-sm transition-all group"
                data-testid={`help-article-${i}`}
              >
                <ExternalLink size={13} className="text-muted-foreground/40 group-hover:text-foreground/60 shrink-0 transition-colors" />
                <span className="text-xs font-medium text-foreground/70 group-hover:text-foreground truncate transition-colors">
                  {article.title || article.url}
                </span>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Subtopics */}
      <div className="space-y-2">
        {(category.subtopics || []).map((sub, i) => (
          <div key={i} className="rounded-lg border border-border/40 bg-card overflow-hidden" data-testid={`subtopic-${i}`}>
            <div className="px-4 py-3.5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-1.5 w-1.5 rounded-full bg-foreground/20" />
                <span className="text-sm font-medium text-foreground">{sub.name}</span>
                {sub.items?.length > 0 && (
                  <span className="text-[10px] font-mono text-muted-foreground/50">{sub.items.length} items</span>
                )}
              </div>
              <a
                href={`${HELP_BASE}?q=${encodeURIComponent(sub.name)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground/40 hover:text-foreground transition-colors"
              >
                <ExternalLink size={13} />
              </a>
            </div>
            {sub.items?.length > 0 && (
              <div className="border-t border-border/20 px-4 py-2.5 bg-muted/20">
                <div className="flex flex-wrap gap-2">
                  {sub.items.map((item, j) => (
                    <a
                      key={j}
                      href={`${HELP_BASE}?q=${encodeURIComponent(item)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] px-2.5 py-1 rounded-md bg-background border border-border/30 text-muted-foreground hover:text-foreground hover:border-foreground/20 transition-colors"
                    >
                      {item}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Submit CTA */}
      <div className="mt-10 p-5 rounded-lg border border-border/30 bg-muted/10 text-center">
        <p className="text-sm text-muted-foreground mb-3">Still need help with {category.title.toLowerCase()}?</p>
        <Link
          to={`/portal/submit?category=${slug}`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity"
          data-testid="category-submit-btn"
        >
          Submit a ticket
          <ChevronRight size={14} />
        </Link>
      </div>
    </div>
  );
};

export default PortalCategory;
