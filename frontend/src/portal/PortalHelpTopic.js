import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, BookOpen, Boxes, Code, Rocket, Wrench, FileText, ChevronRight, ExternalLink } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const ICON_MAP = {
  BookOpen, Boxes, Code, Rocket, Wrench, FileText,
};

const PortalHelpTopic = () => {
  const { topicKey } = useParams();
  const [topic, setTopic] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/portal/help-topics/${topicKey}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(d => { setTopic(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [topicKey]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16" data-testid="help-topic-loading">
        <div className="h-8 w-48 bg-muted/30 rounded animate-pulse mb-4" />
        <div className="h-4 w-96 bg-muted/30 rounded animate-pulse mb-8" />
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => <div key={i} className="h-14 bg-muted/20 rounded-lg animate-pulse" />)}
        </div>
      </div>
    );
  }

  if (!topic) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center" data-testid="help-topic-not-found">
        <p className="text-muted-foreground">Topic not found</p>
        <Link to="/portal" className="text-sm text-foreground underline underline-offset-4 mt-2 inline-block">Back to home</Link>
      </div>
    );
  }

  const Icon = ICON_MAP[topic.icon] || FileText;

  return (
    <div className="max-w-3xl mx-auto px-6 py-10" data-testid="help-topic-page">
      <Link to="/portal" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mb-8" data-testid="help-topic-back">
        <ArrowLeft size={12} />
        <span className="font-mono">back</span>
      </Link>

      <div className="flex items-start gap-4 mb-2">
        <div className="h-11 w-11 rounded-lg bg-[#00A1B2]/10 flex items-center justify-center text-[#00A1B2] shrink-0">
          <Icon size={22} strokeWidth={1.5} />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-foreground mb-1" data-testid="help-topic-title">{topic.label}</h1>
          <p className="text-sm text-muted-foreground">{topic.description}</p>
        </div>
      </div>

      <p className="text-xs text-muted-foreground/60 mb-8 ml-15">
        {topic.article_count} article{topic.article_count !== 1 ? 's' : ''} across {topic.sections.length} section{topic.sections.length !== 1 ? 's' : ''}
      </p>

      <div className="space-y-8">
        {topic.sections.map((section) => (
          <div key={section.key} data-testid={`help-section-${section.key}`}>
            <h2 className="text-sm font-semibold text-foreground mb-3 uppercase tracking-wide">{section.label}</h2>
            <div className="space-y-1">
              {section.articles.map((article) => (
                <a
                  key={article.slug}
                  href={`/docs/${article.slug}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex items-center justify-between px-4 py-3 rounded-lg border border-border/40 bg-card hover:border-[#00A1B2] hover:bg-[#00A1B2]/5 transition-all"
                  data-testid={`help-article-${article.slug}`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="h-1.5 w-1.5 rounded-full bg-[#00A1B2]/40 group-hover:bg-[#00A1B2] transition-colors flex-shrink-0" />
                    <span className="text-sm font-medium text-foreground truncate">{article.title}</span>
                  </div>
                  <ExternalLink size={13} className="text-muted-foreground/30 group-hover:text-[#00A1B2] transition-colors flex-shrink-0 ml-2" />
                </a>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-10 p-5 rounded-lg border border-border/30 bg-muted/10 text-center">
        <p className="text-sm text-muted-foreground mb-3">Can't find what you're looking for?</p>
        <Link
          to="/portal/submit"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#00A1B2] text-white text-sm font-medium hover:opacity-90 transition-opacity"
          data-testid="help-topic-submit-btn"
        >
          Submit a ticket
          <ChevronRight size={14} />
        </Link>
      </div>
    </div>
  );
};

export default PortalHelpTopic;
