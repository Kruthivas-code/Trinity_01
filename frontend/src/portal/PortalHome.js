import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Wrench, AlertTriangle, MessageSquare, Users,
  CreditCard, Receipt, Globe, Boxes, UserCog, ShieldCheck,
  Rocket, Bot, Database, Smartphone, BookOpen, Code, FileText,
  ArrowRight, ChevronRight, X, Clock, Zap, Video, Hash, FileCheck, Settings2,
  Send, Search, ExternalLink,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const ICON_MAP = {
  CreditCard, Receipt, Globe, Boxes, UserCog, ShieldCheck,
  Rocket, Bot, Database, Smartphone,
};

const KB_ICON_MAP = {
  BookOpen, Boxes, Code, Rocket, Wrench, FileText,
};

// ===== Modals =====
const Modal = ({ open, onClose, title, children }) => {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4" data-testid="modal-overlay">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-card border border-border rounded-xl w-full max-w-md p-6 animate-in fade-in zoom-in-95 duration-200" data-testid="modal-content">
        <button onClick={onClose} className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors" data-testid="modal-close">
          <X size={16} />
        </button>
        <h2 className="text-lg font-semibold text-foreground mb-4">{title}</h2>
        {children}
      </div>
    </div>
  );
};

const InquiryForm = ({ type, onClose }) => {
  const [form, setForm] = useState({ name: '', email: '', company: '', message: '' });
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.message.trim()) return;
    setSending(true);
    try {
      await fetch(`${BACKEND_URL}/api/portal/inquiries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, type }),
      });
    } catch { /* silent */ }
    setSending(false);
    setSent(true);
  };

  if (sent) {
    return (
      <div className="text-center py-4">
        <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-3">
          <ChevronRight className="w-5 h-5 text-emerald-500" />
        </div>
        <p className="text-sm text-foreground font-medium mb-1">Inquiry submitted</p>
        <p className="text-xs text-muted-foreground">We'll get back to you within 24 hours.</p>
        <button onClick={onClose} className="mt-4 px-4 py-2 text-sm bg-[#00A1B2] text-white rounded-lg hover:opacity-90 transition-opacity">
          Close
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <input type="text" placeholder="Your name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-foreground/20" required data-testid="inquiry-name" />
      <input type="email" placeholder="Email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-foreground/20" required data-testid="inquiry-email" />
      {type === 'partner' && (
        <input type="text" placeholder="Company name" value={form.company} onChange={e => setForm(f => ({ ...f, company: e.target.value }))}
          className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-foreground/20" data-testid="inquiry-company" />
      )}
      <textarea placeholder={type === 'partner' ? 'Tell us about your partnership goals...' : type === 'sales' ? 'Tell us about your needs...' : 'How can we help?'}
        value={form.message} onChange={e => setForm(f => ({ ...f, message: e.target.value }))} rows={3}
        className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-foreground/20 resize-none" required data-testid="inquiry-message" />
      <button type="submit" disabled={sending}
        className="w-full py-2.5 bg-[#00A1B2] text-white text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center justify-center gap-2"
        data-testid="inquiry-submit">
        {sending ? 'Sending...' : 'Submit'}
        {!sending && <Send size={14} />}
      </button>
    </form>
  );
};

// ===== Main Component =====
const PortalHome = () => {
  const [categories, setCategories] = useState([]);
  const [plans, setPlans] = useState([]);
  const [helpTopics, setHelpTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [partnerModal, setPartnerModal] = useState(false);
  const [salesModal, setSalesModal] = useState(false);
  const [engineerModal, setEngineerModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const categoriesRef = useRef(null);

  useEffect(() => {
    Promise.all([
      fetch(`${BACKEND_URL}/api/portal/categories`).then(r => r.json()),
      fetch(`${BACKEND_URL}/api/portal/engineer-plans`).then(r => r.json()),
      fetch(`${BACKEND_URL}/api/portal/help-topics`).then(r => r.json()),
    ]).then(([catData, planData, topicData]) => {
      setCategories(catData.categories || []);
      setPlans(planData.plans || []);
      setHelpTopics(topicData.topics || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const scrollToCategories = () => {
    categoriesRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const totalSubtopics = (cat) => cat.subtopics?.length || 0;

  return (
    <div data-testid="portal-home">
      {/* Hero */}
      <div className="pt-16 pb-14 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-foreground mb-4" data-testid="portal-hero-title">
            How can we help?
          </h1>
          <p className="text-base text-muted-foreground max-w-md mx-auto">
            Get help from experts, sales, or our community.
          </p>
        </div>
      </div>

      {/* Contact Cards */}
      <div className="max-w-[960px] mx-auto px-6 pb-8">
        {/* Primary Card - Product Help */}
        <button
          onClick={scrollToCategories}
          className="w-full text-left p-6 sm:p-8 rounded-2xl bg-white dark:bg-[#0a0a0a] border border-gray-200 dark:border-white/10 hover:border-[#00A1B2] dark:hover:border-[#00A1B2] transition-all group mb-4 min-h-[285px]"
          data-testid="product-help-card"
        >
          <div className="mb-5">
            <Wrench size={24} className="text-[#00A1B2]" strokeWidth={1.5} />
          </div>
          <h2 className="text-lg font-semibold text-foreground mb-1">Product help</h2>
          <p className="text-sm text-muted-foreground mb-6">Get help from an expert.</p>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-2 px-4 py-2 bg-[#00A1B2] text-white text-sm font-medium rounded-lg group-hover:opacity-90 transition-opacity">
              Browse topics
            </span>
            <span className="text-xs text-muted-foreground">For customers on paid plans</span>
          </div>
        </button>

        {/* Three Secondary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Partner Programs */}
          <button
            onClick={() => setPartnerModal(true)}
            className="text-left p-5 rounded-2xl bg-white dark:bg-[#0a0a0a] border border-gray-200 dark:border-white/10 hover:border-[#00A1B2] dark:hover:border-[#00A1B2] transition-all group"
            data-testid="partner-card"
          >
            <div className="mb-4">
              <Users size={20} className="text-[#00A1B2]" strokeWidth={1.5} />
            </div>
            <h3 className="text-sm font-semibold text-foreground mb-1">Partner programs</h3>
            <p className="text-xs text-muted-foreground leading-relaxed mb-4">Enquire about partnership opportunities.</p>
            <span className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-[#999999] rounded-lg group-hover:bg-gray-200 dark:group-hover:bg-white/15 transition-colors">
              Enquire
            </span>
          </button>

          {/* Emergency Help */}
          <Link
            to="/portal/submit?priority=emergency&category=deployments"
            className="text-left p-5 rounded-2xl bg-white dark:bg-[#0a0a0a] border border-gray-200 dark:border-white/10 hover:border-[#00A1B2] dark:hover:border-[#00A1B2] transition-all group"
            data-testid="emergency-card"
          >
            <div className="mb-4">
              <AlertTriangle size={20} className="text-[#00A1B2]" strokeWidth={1.5} />
            </div>
            <h3 className="text-sm font-semibold text-foreground mb-1">Emergency help for Deployed App</h3>
            <p className="text-xs text-muted-foreground leading-relaxed mb-4">Urgent help when your app is down.</p>
            <span className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-[#999999] rounded-lg group-hover:bg-gray-200 dark:group-hover:bg-white/15 transition-colors">
              Emergency
            </span>
          </Link>

          {/* Talk to Sales */}
          <button
            onClick={() => setSalesModal(true)}
            className="text-left p-5 rounded-2xl bg-white dark:bg-[#0a0a0a] border border-gray-200 dark:border-white/10 hover:border-[#00A1B2] dark:hover:border-[#00A1B2] transition-all group"
            data-testid="sales-card"
          >
            <div className="mb-4">
              <MessageSquare size={20} className="text-[#00A1B2]" strokeWidth={1.5} />
            </div>
            <h3 className="text-sm font-semibold text-foreground mb-1">Talk to sales</h3>
            <p className="text-xs text-muted-foreground leading-relaxed mb-4">Work with our team on enterprise solutions.</p>
            <span className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-[#999999] rounded-lg group-hover:bg-gray-200 dark:group-hover:bg-white/15 transition-colors">
              Talk to sales
            </span>
          </button>
        </div>
      </div>

      {/* Dedicated Engineer Upsell */}
      {plans.length > 0 && (
        <div className="max-w-[960px] mx-auto px-6 py-10">
          <div className="rounded-2xl bg-white dark:bg-[#0a0a0a] border border-gray-200 dark:border-white/10 overflow-hidden">
            <div className="p-6 sm:p-8">
              <div className="flex items-center gap-2 mb-1">
                <Zap size={16} className="text-amber-400" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-400">Premium</span>
              </div>
              <h2 className="text-xl font-semibold text-foreground mb-2">Need dedicated expert help?</h2>
              <p className="text-sm text-muted-foreground mb-6">Get a senior engineer assigned to your account for hands-on assistance.</p>

              <div className="space-y-4">
                {plans.map(plan => (
                  <div key={plan.plan_id} className="flex flex-col sm:flex-row sm:items-start gap-4 sm:gap-8 p-5 rounded-lg bg-muted/30 border border-border/30">
                    <div className="flex-1">
                      <h3 className="text-base font-semibold text-foreground mb-0.5">{plan.title}</h3>
                      <p className="text-sm text-muted-foreground mb-3">{plan.hours} hours of dedicated engineer time per {plan.period}</p>
                      <ul className="space-y-1.5">
                        {(plan.features || []).map((f, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                            <ChevronRight size={12} className="text-emerald-500 mt-0.5 flex-shrink-0" />
                            <span>{f}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="sm:text-right flex-shrink-0">
                      <div className="text-2xl font-bold text-foreground">${plan.price.toLocaleString()}</div>
                      <div className="text-xs text-muted-foreground mb-3">per {plan.period}</div>
                      <button
                        onClick={() => setEngineerModal(true)}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-[#00A1B2] text-white text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
                        data-testid="engineer-plan-cta"
                      >
                        Get started
                        <ArrowRight size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Documentation Topics from KB */}
      {helpTopics.length > 0 && (
        <div className="max-w-[960px] mx-auto px-6 pb-10 scroll-mt-20" data-testid="docs-topics-section" ref={categoriesRef}>
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-foreground mb-1">Browse our documentation</h2>
            <p className="text-sm text-muted-foreground">Find answers in our knowledge base — updated automatically.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {helpTopics.map(topic => {
              const TopicIcon = KB_ICON_MAP[topic.icon] || FileText;
              return (
                <Link
                  key={topic.key}
                  to={`/portal/topic/${topic.key}`}
                  className="group p-5 rounded-2xl bg-white dark:bg-[#0a0a0a] border border-gray-200 dark:border-white/10 hover:border-[#00A1B2] dark:hover:border-[#00A1B2] hover:shadow-sm transition-all flex flex-col"
                  data-testid={`docs-topic-card-${topic.key}`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="h-9 w-9 rounded-md bg-[#00A1B2]/10 flex items-center justify-center text-[#00A1B2] group-hover:bg-[#00A1B2]/20 transition-colors flex-shrink-0">
                      <TopicIcon size={18} strokeWidth={1.5} />
                    </div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/50">
                      {topic.article_count} articles
                    </span>
                  </div>
                  <h3 className="text-sm font-medium text-foreground mb-1 group-hover:translate-x-0.5 transition-transform">
                    {topic.label}
                  </h3>
                  <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2 flex-1">
                    {topic.description}
                  </p>
                  <div className="mt-3 flex items-center gap-1 text-[10px] font-medium text-[#00A1B2]/60 group-hover:text-[#00A1B2] transition-colors">
                    <span className="font-mono">browse articles</span>
                    <ChevronRight size={10} />
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* Category Grid — Support ticket categories */}
      <div className="max-w-[960px] mx-auto px-6 pb-10 scroll-mt-20" data-testid="categories-section">
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-foreground mb-1">Submit a ticket by topic</h2>
          <p className="text-sm text-muted-foreground">Can't find your answer above? Choose a category to submit a support ticket.</p>
        </div>

        {/* Search */}
        <div className="mb-6">
          <div className="relative">
            <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search topics..."
              className="w-full h-10 pl-10 pr-4 rounded-xl bg-white dark:bg-[#0a0a0a] border border-gray-200 dark:border-white/10 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-[#00A1B2] dark:focus:border-[#00A1B2] transition-colors"
              data-testid="portal-search-input"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-foreground transition-colors">
                <X size={14} />
              </button>
            )}
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-[218px] rounded-2xl bg-muted/30 animate-pulse" />
            ))}
          </div>
        ) : categories.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-muted-foreground text-sm">No categories available</p>
          </div>
        ) : (() => {
          const filtered = searchQuery.trim()
            ? categories.filter(cat =>
                cat.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                cat.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                cat.subtopics?.some(s => s.name?.toLowerCase().includes(searchQuery.toLowerCase()))
              )
            : categories;

          return filtered.length === 0 ? (
            <div className="text-center py-12 rounded-2xl border border-gray-200 dark:border-white/10 bg-white dark:bg-[#0a0a0a]">
              <p className="text-sm text-muted-foreground">No topics matching "<span className="font-medium text-foreground">{searchQuery}</span>"</p>
              <p className="text-xs text-muted-foreground/60 mt-1">Try different keywords</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map(cat => {
                const Icon = ICON_MAP[cat.icon] || Boxes;
                return (
                  <Link
                    key={cat.slug}
                    to={`/portal/category/${cat.slug}`}
                    className="group p-5 rounded-2xl bg-white dark:bg-[#0a0a0a] border border-gray-200 dark:border-white/10 hover:border-[#00A1B2] dark:hover:border-[#00A1B2] hover:shadow-sm transition-all max-h-[218px] flex flex-col"
                    data-testid={`category-card-${cat.slug}`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="h-9 w-9 rounded-md bg-[#00A1B2]/10 flex items-center justify-center text-[#00A1B2] group-hover:bg-[#00A1B2]/20 transition-colors flex-shrink-0">
                        <Icon size={18} strokeWidth={1.5} />
                      </div>
                      <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/50">
                        {totalSubtopics(cat)} topics
                      </span>
                    </div>
                    <h3 className="text-sm font-medium text-foreground mb-1 group-hover:translate-x-0.5 transition-transform">
                      {cat.title}
                    </h3>
                    <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2 flex-1">
                      {cat.description}
                    </p>
                    <div className="mt-3 flex items-center gap-1 text-[10px] font-medium text-[#00A1B2]/60 group-hover:text-[#00A1B2] transition-colors">
                      <span className="font-mono">explore</span>
                      <ChevronRight size={10} />
                    </div>
                  </Link>
                );
              })}
            </div>
          );
        })()}
      </div>

      {/* CTA */}
      <div className="max-w-[960px] mx-auto px-6 pb-16 text-center">
        <p className="text-sm text-muted-foreground mb-3">Can't find what you're looking for?</p>
        <Link
          to="/portal/submit"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#00A1B2] text-white text-sm font-medium hover:opacity-90 transition-opacity"
          data-testid="portal-submit-cta"
        >
          Submit a ticket
          <ArrowRight size={14} />
        </Link>
      </div>

      {/* Modals */}
      <Modal open={partnerModal} onClose={() => setPartnerModal(false)} title="Enquire about partner programs">
        <p className="text-sm text-muted-foreground mb-4">Tell us about your partnership goals and we'll connect you with the right team.</p>
        <InquiryForm type="partner" onClose={() => setPartnerModal(false)} />
      </Modal>

      <Modal open={salesModal} onClose={() => setSalesModal(false)} title="Talk to sales">
        <p className="text-sm text-muted-foreground mb-4">Tell us about your enterprise needs and our team will reach out.</p>
        <InquiryForm type="sales" onClose={() => setSalesModal(false)} />
      </Modal>

      <Modal open={engineerModal} onClose={() => setEngineerModal(false)} title="Get dedicated engineer time">
        <p className="text-sm text-muted-foreground mb-4">Interested in a dedicated engineer for your team? Tell us about your requirements.</p>
        <InquiryForm type="engineer" onClose={() => setEngineerModal(false)} />
      </Modal>
    </div>
  );
};

export default PortalHome;
