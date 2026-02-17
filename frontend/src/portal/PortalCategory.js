import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ChevronRight, CreditCard, Receipt, Globe, Boxes, UserCog, ShieldCheck, Rocket, Bot, Database, Smartphone } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const ICON_MAP = {
  CreditCard, Receipt, Globe, Boxes, UserCog, ShieldCheck,
  Rocket, Bot, Database, Smartphone,
};

const PortalCategory = () => {
  const { slug } = useParams();
  const navigate = useNavigate();
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

  const toSubmit = (subtopic, item) => {
    const params = new URLSearchParams({ category: slug });
    if (subtopic) params.set('subtopic', subtopic);
    if (item) params.set('tag', item);
    navigate(`/portal/submit?${params.toString()}`);
  };

  return (
    <div className="max-w-3xl mx-auto px-6 py-10" data-testid="portal-category-page">
      {/* Back */}
      <Link to="/portal" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mb-8" data-testid="category-back-link">
        <ArrowLeft size={12} />
        <span className="font-mono">back</span>
      </Link>

      {/* Header */}
      <div className="flex items-start gap-4 mb-2">
        <div className="h-11 w-11 rounded-lg bg-muted/50 flex items-center justify-center text-foreground shrink-0">
          <Icon size={22} strokeWidth={1.5} />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-foreground mb-1">{category.title}</h1>
          <p className="text-sm text-muted-foreground">{category.description}</p>
        </div>
      </div>

      <p className="text-xs text-muted-foreground/60 mb-8 ml-15">Select the issue that best describes your problem</p>

      {/* Subtopics as triage options */}
      <div className="space-y-3">
        {(category.subtopics || []).map((sub, i) => (
          <div key={i} className="rounded-lg border border-border/40 bg-card overflow-hidden" data-testid={`subtopic-${i}`}>
            {/* Subtopic header — clickable, goes to submit */}
            <button
              onClick={() => toSubmit(sub.name)}
              className="w-full px-4 py-3.5 flex items-center justify-between hover:bg-muted/30 transition-colors group"
              data-testid={`subtopic-btn-${i}`}
            >
              <div className="flex items-center gap-3">
                <div className="h-1.5 w-1.5 rounded-full bg-foreground/30 group-hover:bg-foreground/60 transition-colors" />
                <span className="text-sm font-medium text-foreground">{sub.name}</span>
                {sub.items?.length > 0 && (
                  <span className="text-[10px] font-mono text-muted-foreground/50">{sub.items.length} items</span>
                )}
              </div>
              <ChevronRight size={14} className="text-muted-foreground/30 group-hover:text-foreground/60 transition-colors" />
            </button>

            {/* Sub-items — more specific triage */}
            {sub.items?.length > 0 && (
              <div className="border-t border-border/20 px-4 py-2.5 bg-muted/10">
                <div className="flex flex-wrap gap-2">
                  {sub.items.map((item, j) => (
                    <button
                      key={j}
                      onClick={() => toSubmit(sub.name, item)}
                      className="text-[11px] px-2.5 py-1 rounded-md bg-background border border-border/30 text-muted-foreground hover:text-foreground hover:border-foreground/20 transition-colors"
                      data-testid={`subtopic-item-${i}-${j}`}
                    >
                      {item}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* General ticket for this category */}
      <div className="mt-10 p-5 rounded-lg border border-border/30 bg-muted/10 text-center">
        <p className="text-sm text-muted-foreground mb-3">None of these match your issue?</p>
        <Link
          to={`/portal/submit?category=${slug}`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity"
          data-testid="category-submit-btn"
        >
          Describe your issue
          <ChevronRight size={14} />
        </Link>
      </div>
    </div>
  );
};

export default PortalCategory;
