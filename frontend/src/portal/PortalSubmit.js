import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { ArrowLeft, Send, ChevronDown, Tag } from 'lucide-react';
import { usePortalAuth } from './PortalAuthContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const PLACEHOLDERS = {
  default: 'Describe your issue in detail. Include steps to reproduce, expected vs actual behavior, etc.',
  emergency: 'Describe the issue with your deployed app. Include: app URL, when it started, error messages, and impact.',
};

// Categories where job ID is mandatory
const JOB_ID_REQUIRED = new Set(['agent-ai', 'deployments', 'database', 'mobile-builds', 'features', 'custom-domain']);
// For credits-pricing, only certain subtopics need it
const JOB_ID_SUBTOPICS = { 'credits-pricing': ['Credit Usage'] };

const needsJobId = (categorySlug, subtopic) => {
  if (JOB_ID_REQUIRED.has(categorySlug)) return true;
  const subs = JOB_ID_SUBTOPICS[categorySlug];
  return subs ? subs.some(s => subtopic?.includes(s)) : false;
};

const PortalSubmit = () => {
  const { customer, token } = usePortalAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const paramCategory = searchParams.get('category') || '';
  const paramSubtopic = searchParams.get('subtopic') || '';
  const paramTag = searchParams.get('tag') || '';
  const paramPriority = searchParams.get('priority') || '';

  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState({
    category_slug: paramCategory,
    subcategory: paramSubtopic,
    subject: '',
    description: '',
    job_id: '',
    video_link: '',
    tags: [paramCategory, paramSubtopic, paramTag].filter(Boolean),
    priority: paramPriority || 'medium',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/portal/categories`)
      .then(r => r.json())
      .then(d => setCategories(d.categories || []))
      .catch(() => {});
  }, []);

  // Build contextual subject suggestion from params
  const contextLabel = [
    categories.find(c => c.slug === form.category_slug)?.title,
    form.subcategory,
    paramTag,
  ].filter(Boolean).join(' > ');

  if (!customer) {
    const redirect = `/portal/submit?${searchParams.toString()}`;
    return (
      <div className="max-w-lg mx-auto px-6 py-16 text-center" data-testid="portal-submit-auth-wall">
        <h2 className="text-xl font-semibold mb-2">Sign in to submit a ticket</h2>
        <p className="text-sm text-muted-foreground mb-6">You need an account to submit and track tickets</p>
        <Link
          to={`/portal/login?redirect=${encodeURIComponent(redirect)}`}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#00A1B2] text-white text-sm font-medium hover:opacity-90 transition-opacity"
          data-testid="submit-signin-link"
        >
          Sign in
        </Link>
      </div>
    );
  }

  const selectedCategory = categories.find(c => c.slug === form.category_slug);
  const subtopics = selectedCategory?.subtopics || [];

  const jobIdRequired = needsJobId(form.category_slug, form.subcategory);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.category_slug || !form.subject.trim() || !form.description.trim()) {
      setError('Please fill all required fields');
      return;
    }
    if (jobIdRequired && !form.job_id.trim()) {
      setError('Job ID is required for this category');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const res = await fetch(`${BACKEND_URL}/api/portal/tickets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Submission failed');
      navigate(`/portal/my-tickets/${data.ticket_id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const isEmergency = paramPriority === 'emergency' || form.priority === 'urgent';

  return (
    <div className="max-w-2xl mx-auto px-6 py-10" data-testid="portal-submit-page">
      <Link to="/portal" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mb-8">
        <ArrowLeft size={12} />
        <span className="font-mono">back</span>
      </Link>

      <h1 className="text-2xl font-semibold mb-1">Submit a ticket</h1>
      <p className="text-sm text-muted-foreground mb-6">Describe your issue and we'll get back to you</p>

      {/* Context ribbon — shows what the user triaged through */}
      {contextLabel && (
        <div className="flex items-center gap-2 px-3 py-2 mb-6 rounded-lg bg-muted/30 border border-border/30" data-testid="submit-context-ribbon">
          <Tag size={12} className="text-muted-foreground flex-shrink-0" />
          <span className="text-xs text-muted-foreground">
            Auto-tagged: <span className="text-foreground font-medium">{contextLabel}</span>
          </span>
        </div>
      )}

      {isEmergency && (
        <div className="flex items-center gap-2 px-3 py-2 mb-6 rounded-lg bg-red-500/10 border border-red-500/20" data-testid="submit-emergency-banner">
          <span className="text-xs text-red-400 font-medium">Emergency — this ticket will be marked as urgent priority</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Category */}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">Category *</label>
          <div className="relative">
            <select
              value={form.category_slug}
              onChange={e => {
                const slug = e.target.value;
                setForm(f => ({ ...f, category_slug: slug, subcategory: '', tags: [slug, ...f.tags.filter(t => t !== f.category_slug)] }));
              }}
              className="w-full h-10 px-3 pr-8 rounded-lg border border-border bg-card text-sm text-foreground appearance-none focus:outline-none focus:ring-1 focus:ring-foreground/20 focus:border-foreground/30 transition-all"
              data-testid="submit-category-select"
            >
              <option value="">Select a category</option>
              {categories.map(c => <option key={c.slug} value={c.slug}>{c.title}</option>)}
            </select>
            <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          </div>
        </div>

        {/* Subcategory */}
        {subtopics.length > 0 && (
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Subtopic</label>
            <div className="relative">
              <select
                value={form.subcategory}
                onChange={e => setForm(f => ({ ...f, subcategory: e.target.value }))}
                className="w-full h-10 px-3 pr-8 rounded-lg border border-border bg-card text-sm text-foreground appearance-none focus:outline-none focus:ring-1 focus:ring-foreground/20 focus:border-foreground/30 transition-all"
                data-testid="submit-subcategory-select"
              >
                <option value="">Select a subtopic (optional)</option>
                {subtopics.map((s, i) => <option key={i} value={s.name}>{s.name}</option>)}
              </select>
              <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
            </div>
          </div>
        )}

        {/* Priority — visible only if emergency or user wants to set it */}
        {isEmergency && (
          <input type="hidden" value="urgent" />
        )}

        {/* Job ID — always visible, mandatory for certain categories */}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">
            Job ID {jobIdRequired ? '*' : <span className="text-muted-foreground/40">(optional)</span>}
          </label>
          <input
            type="text"
            value={form.job_id}
            onChange={e => setForm(f => ({ ...f, job_id: e.target.value }))}
            placeholder="e.g. job_abc123 — find this in your chat URL"
            className="w-full h-10 px-3 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-foreground/20 focus:border-foreground/30 transition-all"
            data-testid="submit-job-id-input"
          />
          <p className="text-[11px] text-muted-foreground/60 mt-1">The job ID from the agent chat where you experienced the issue</p>
        </div>

        {/* Video Recording Link — always optional */}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">
            Video recording link <span className="text-muted-foreground/40">(optional)</span>
          </label>
          <input
            type="url"
            value={form.video_link}
            onChange={e => setForm(f => ({ ...f, video_link: e.target.value }))}
            placeholder="e.g. https://www.loom.com/share/..."
            className="w-full h-10 px-3 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-foreground/20 focus:border-foreground/30 transition-all"
            data-testid="submit-video-link-input"
          />
          <p className="text-[11px] text-muted-foreground/60 mt-1">Loom, YouTube, or any screen recording showing the issue</p>
        </div>

        {/* Subject */}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">Subject *</label>
          <input
            type="text"
            value={form.subject}
            onChange={e => setForm(f => ({ ...f, subject: e.target.value }))}
            placeholder={paramTag ? `Issue with: ${paramTag}` : 'Brief description of your issue'}
            className="w-full h-10 px-3 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-foreground/20 focus:border-foreground/30 transition-all"
            maxLength={200}
            data-testid="submit-subject-input"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">Description *</label>
          <textarea
            value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            placeholder={isEmergency ? PLACEHOLDERS.emergency : PLACEHOLDERS.default}
            rows={6}
            className="w-full px-3 py-2.5 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-foreground/20 focus:border-foreground/30 transition-all resize-y"
            maxLength={10000}
            data-testid="submit-description-input"
          />
        </div>

        {error && (
          <p className="text-xs text-red-500" data-testid="submit-error">{error}</p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#00A1B2] text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          data-testid="submit-ticket-btn"
        >
          {submitting ? 'Submitting...' : 'Submit ticket'}
          <Send size={14} />
        </button>
      </form>
    </div>
  );
};

export default PortalSubmit;
