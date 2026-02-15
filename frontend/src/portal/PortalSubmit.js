import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { ArrowLeft, Send, ChevronDown } from 'lucide-react';
import { usePortalAuth } from './PortalAuthContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const PortalSubmit = () => {
  const { customer, token } = usePortalAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState({
    category_slug: searchParams.get('category') || '',
    subcategory: '',
    subject: '',
    description: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/portal/categories`)
      .then(r => r.json())
      .then(d => setCategories(d.categories || []))
      .catch(() => {});
  }, []);

  if (!customer) {
    return (
      <div className="max-w-lg mx-auto px-6 py-16 text-center" data-testid="portal-submit-auth-wall">
        <h2 className="text-xl font-semibold mb-2">Sign in to submit a ticket</h2>
        <p className="text-sm text-muted-foreground mb-6">You need an account to submit and track tickets</p>
        <Link
          to={`/portal/login?redirect=/portal/submit${searchParams.get('category') ? `?category=${searchParams.get('category')}` : ''}`}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity"
          data-testid="submit-signin-link"
        >
          Sign in
        </Link>
      </div>
    );
  }

  const selectedCategory = categories.find(c => c.slug === form.category_slug);
  const subtopics = selectedCategory?.subtopics || [];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.category_slug || !form.subject.trim() || !form.description.trim()) {
      setError('Please fill all required fields');
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

  return (
    <div className="max-w-2xl mx-auto px-6 py-10" data-testid="portal-submit-page">
      <Link to="/" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mb-8">
        <ArrowLeft size={12} />
        <span className="font-mono">back</span>
      </Link>

      <h1 className="text-2xl font-semibold mb-1">Submit a ticket</h1>
      <p className="text-sm text-muted-foreground mb-8">Describe your issue and we'll get back to you</p>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Category */}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">Category *</label>
          <div className="relative">
            <select
              value={form.category_slug}
              onChange={e => setForm(f => ({ ...f, category_slug: e.target.value, subcategory: '' }))}
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

        {/* Subject */}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">Subject *</label>
          <input
            type="text"
            value={form.subject}
            onChange={e => setForm(f => ({ ...f, subject: e.target.value }))}
            placeholder="Brief description of your issue"
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
            placeholder="Describe your issue in detail. Include steps to reproduce, expected vs actual behavior, etc."
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
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
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
