import React, { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { usePortalAuth } from './PortalAuthContext';

const PortalLogin = () => {
  const { login, register } = usePortalAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirect = searchParams.get('redirect') || '/portal/my-tickets';

  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'register') {
        if (!form.name.trim()) { setError('Name is required'); setLoading(false); return; }
        await register(form.name, form.email, form.password);
      } else {
        await login(form.email, form.password);
      }
      navigate(redirect);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-sm mx-auto px-6 py-16" data-testid="portal-login-page">
      <div className="text-center mb-8">
        <div className="h-10 w-10 rounded-lg bg-[#00A1B2] flex items-center justify-center mx-auto mb-4">
          <span className="text-white text-sm font-bold">E</span>
        </div>
        <h1 className="text-xl font-semibold mb-1">
          {mode === 'login' ? 'Sign in' : 'Create an account'}
        </h1>
        <p className="text-sm text-muted-foreground">
          {mode === 'login' ? 'Track your tickets and submit new ones' : 'Sign up to submit and track tickets'}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {mode === 'register' && (
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Your name"
              className="w-full h-10 px-3 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-foreground/20 focus:border-foreground/30 transition-all"
              data-testid="login-name-input"
            />
          </div>
        )}

        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">Email</label>
          <input
            type="email"
            value={form.email}
            onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
            placeholder="you@example.com"
            required
            className="w-full h-10 px-3 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-foreground/20 focus:border-foreground/30 transition-all"
            data-testid="login-email-input"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">Password</label>
          <input
            type="password"
            value={form.password}
            onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
            placeholder={mode === 'register' ? 'Min 6 characters' : 'Your password'}
            required
            className="w-full h-10 px-3 rounded-lg border border-border bg-card text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-foreground/20 focus:border-foreground/30 transition-all"
            data-testid="login-password-input"
          />
        </div>

        {error && <p className="text-xs text-red-500" data-testid="login-error">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full h-10 rounded-lg bg-[#00A1B2] text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          data-testid="login-submit-btn"
        >
          {loading ? 'Please wait...' : mode === 'login' ? 'Sign in' : 'Create account'}
        </button>
      </form>

      <div className="mt-6 text-center">
        <button
          onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          data-testid="login-toggle-mode"
        >
          {mode === 'login' ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
        </button>
      </div>

      <div className="mt-6 text-center">
        <Link to="/portal" className="text-xs text-muted-foreground/50 hover:text-muted-foreground transition-colors font-mono">
          back to home
        </Link>
      </div>
    </div>
  );
};

export default PortalLogin;
