import React, { useState, useEffect } from 'react';
import { ArrowLeft, Sun, Moon, Mail, CheckCircle, XCircle, Loader2, RefreshCw, ExternalLink, LogOut, Key, Copy, Trash2, Plus } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const SettingsPage = ({ user }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { theme, setThemeMode } = useTheme();
  
  // Gmail state
  const [gmailStatus, setGmailStatus] = useState({
    connected: false,
    watch_email: null,
    configured: true,
    loading: true
  });
  const [connecting, setConnecting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  
  // API Keys state
  const [apiKeys, setApiKeys] = useState([]);
  const [loadingKeys, setLoadingKeys] = useState(true);
  const [creatingKey, setCreatingKey] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [showNewKey, setShowNewKey] = useState(null);

  useEffect(() => {
    if (user) {
      fetchGmailStatus();
      fetchApiKeys();
    }
    
    // Check URL params for OAuth callback result
    const gmailConnected = searchParams.get('gmail_connected');
    const gmailError = searchParams.get('gmail_error');
    
    if (gmailConnected === 'true') {
      toast.success('Gmail connected successfully!');
      window.history.replaceState({}, '', '/settings');
      fetchGmailStatus();
    } else if (gmailError) {
      toast.error(`Gmail connection failed: ${gmailError}`);
      window.history.replaceState({}, '', '/settings');
    }
  }, [searchParams, user]);

  const fetchGmailStatus = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/gmail/status`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        console.log('Gmail status:', data);
        setGmailStatus({ ...data, loading: false });
      } else {
        console.error('Gmail status fetch failed:', response.status);
        // Keep configured as true since credentials exist in backend
        setGmailStatus(prev => ({ ...prev, loading: false, configured: true }));
      }
    } catch (error) {
      console.error('Failed to fetch Gmail status:', error);
      // Keep configured as true since credentials exist in backend
      setGmailStatus(prev => ({ ...prev, loading: false, configured: true }));
    }
  };

  const handleConnectGmail = async () => {
    setConnecting(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/gmail/connect`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to initiate Gmail connection');
      }
      
      const data = await response.json();
      console.log('Redirecting to:', data.authorization_url);
      window.location.href = data.authorization_url;
    } catch (error) {
      console.error('Gmail connect error:', error);
      toast.error(error.message || 'Failed to connect Gmail');
      setConnecting(false);
    }
  };

  const handleDisconnectGmail = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/gmail/disconnect`, {
        method: 'POST',
        credentials: 'include'
      });
      
      if (response.ok) {
        toast.success('Gmail disconnected');
        setGmailStatus(prev => ({ ...prev, connected: false, watch_email: null }));
      }
    } catch (error) {
      toast.error('Failed to disconnect Gmail');
    }
  };

  const handleSyncEmails = async () => {
    setSyncing(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/gmail/sync?max_emails=10`, {
        method: 'POST',
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error('Failed to sync emails');
      }
      
      const data = await response.json();
      if (data.created > 0) {
        toast.success(`Created ${data.created} ticket(s) from emails`);
      } else {
        toast.info('No new emails to process');
      }
    } catch (error) {
      toast.error('Failed to sync emails');
    } finally {
      setSyncing(false);
    }
  };

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await fetch(`${BACKEND_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
      
      localStorage.removeItem('theme');
      
      toast.success('Logged out successfully');
      navigate('/login', { replace: true });
    } catch (error) {
      console.error('Logout error:', error);
      navigate('/login', { replace: true });
    }
  };

  // API Keys functions
  const fetchApiKeys = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/api-keys`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setApiKeys(data);
      }
    } catch (error) {
      console.error('Failed to fetch API keys:', error);
    } finally {
      setLoadingKeys(false);
    }
  };

  const handleCreateApiKey = async () => {
    if (!newKeyName.trim()) {
      toast.error('Please enter a name for the API key');
      return;
    }
    
    setCreatingKey(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/api-keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name: newKeyName })
      });
      
      if (!response.ok) throw new Error('Failed to create API key');
      
      const data = await response.json();
      setShowNewKey(data.key);
      setNewKeyName('');
      fetchApiKeys();
      toast.success('API key created!');
    } catch (error) {
      toast.error('Failed to create API key');
    } finally {
      setCreatingKey(false);
    }
  };

  const handleRevokeKey = async (keyId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/api-keys/${keyId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (!response.ok) throw new Error('Failed to revoke');
      
      toast.success('API key revoked');
      fetchApiKeys();
    } catch (error) {
      toast.error('Failed to revoke API key');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-primary" />
      </div>
    );
  }

  const handleThemeChange = async (newTheme) => {
    try {
      setThemeMode(newTheme);

      const response = await fetch(`${BACKEND_URL}/api/users/me/preferences`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ theme: newTheme })
      });

      if (!response.ok) throw new Error('Failed to save preferences');
      
      toast.success(`Theme changed to ${newTheme} mode`);
    } catch (error) {
      toast.error('Failed to save theme preference');
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="gradient-overlay" />
      <div className="content-wrapper relative z-10">
        {/* Header */}
        <header className="sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150">
          <div className="mx-auto max-w-[1200px] px-4 h-16 flex items-center gap-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="h-9 w-9 flex items-center justify-center rounded-lg hover:bg-white/10 transition-interactive"
              data-testid="back-button"
            >
              <ArrowLeft size={20} />
            </button>
            <h1 className="text-xl font-semibold">Settings</h1>
          </div>
        </header>

        {/* Content */}
        <div className="mx-auto max-w-[1200px] px-4 py-8 space-y-6">
          {/* Email Integration Section */}
          <div className="glass rounded-2xl p-6 md:p-8 border border-border/60">
            <div className="flex items-center gap-3 mb-6">
              <div className="h-10 w-10 rounded-lg bg-gradient-primary flex items-center justify-center">
                <Mail size={20} className="text-white" />
              </div>
              <div>
                <h3 className="text-lg font-medium">Email Integration</h3>
                <p className="text-sm text-muted-foreground">
                  Connect Gmail to create tickets from incoming emails
                </p>
              </div>
            </div>

            {gmailStatus.loading ? (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 size={16} className="animate-spin" />
                <span>Loading status...</span>
              </div>
            ) : gmailStatus.connected ? (
              <div className="space-y-4">
                {/* Connected Status */}
                <div className="flex items-center gap-2 p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                  <CheckCircle size={20} className="text-green-500" />
                  <div className="flex-1">
                    <p className="font-medium text-green-500">Gmail Connected</p>
                    {gmailStatus.watch_email && (
                      <p className="text-sm text-muted-foreground">
                        Account: {gmailStatus.watch_email}
                      </p>
                    )}
                  </div>
                </div>

                {/* Mock Mode Indicator */}
                {gmailStatus.mock_mode && (
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                    <span className="text-yellow-500 text-sm">
                      📧 <strong>Mock Mode:</strong> Replies are saved but not actually sent
                    </span>
                  </div>
                )}

                {/* Sync Query Info */}
                {gmailStatus.sync_query && (
                  <div className="p-3 rounded-lg bg-secondary/30 border border-border/40">
                    <p className="text-xs text-muted-foreground mb-1">Sync Filter:</p>
                    <code className="text-xs text-primary break-all">{gmailStatus.sync_query}</code>
                  </div>
                )}

                {/* Actions */}
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={handleSyncEmails}
                    disabled={syncing}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary transition-interactive disabled:opacity-50"
                    data-testid="sync-emails-button"
                  >
                    {syncing ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <RefreshCw size={16} />
                    )}
                    <span>{syncing ? 'Syncing...' : 'Sync Emails Now'}</span>
                  </button>
                  
                  <button
                    onClick={() => navigate('/emails')}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary/50 hover:bg-secondary/70 transition-interactive"
                    data-testid="view-emails-button"
                  >
                    <ExternalLink size={16} />
                    <span>View Emails</span>
                  </button>
                  
                  <button
                    onClick={handleDisconnectGmail}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg border border-destructive/50 text-destructive hover:bg-destructive/10 transition-interactive"
                    data-testid="disconnect-gmail-button"
                  >
                    <XCircle size={16} />
                    <span>Disconnect</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Not Connected */}
                <div className="flex items-center gap-2 p-4 rounded-lg bg-secondary/30 border border-border/40">
                  <XCircle size={20} className="text-muted-foreground" />
                  <p className="text-muted-foreground">Gmail not connected</p>
                </div>

                {gmailStatus.configured ? (
                  <button
                    onClick={handleConnectGmail}
                    disabled={connecting}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-primary text-white hover:opacity-90 transition-interactive disabled:opacity-50"
                    data-testid="connect-gmail-button"
                  >
                    {connecting ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Mail size={16} />
                    )}
                    <span>{connecting ? 'Connecting...' : 'Connect Gmail'}</span>
                  </button>
                ) : (
                  <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                    <p className="text-sm text-yellow-500">
                      Gmail integration is not configured. Please ensure Gmail API credentials are set in the backend.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* API Keys Section */}
          <div className="glass rounded-2xl p-6 md:p-8 border border-border/60">
            <div className="flex items-center gap-3 mb-6">
              <div className="h-10 w-10 rounded-lg bg-gradient-primary flex items-center justify-center">
                <Key size={20} className="text-white" />
              </div>
              <div>
                <h3 className="text-lg font-medium">API Keys</h3>
                <p className="text-sm text-muted-foreground">
                  Manage API keys for programmatic access
                </p>
              </div>
            </div>

            {/* New Key Created Alert */}
            {showNewKey && (
              <div className="mb-4 p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                <p className="text-sm text-green-500 mb-2 font-medium">
                  🎉 New API Key Created - Copy it now (won't be shown again!)
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-2 rounded bg-black/20 text-xs font-mono break-all">
                    {showNewKey}
                  </code>
                  <button
                    onClick={() => copyToClipboard(showNewKey)}
                    className="p-2 rounded hover:bg-white/10"
                  >
                    <Copy size={16} />
                  </button>
                </div>
                <button
                  onClick={() => setShowNewKey(null)}
                  className="mt-2 text-xs text-muted-foreground hover:text-foreground"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Create New Key */}
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="Key name (e.g., Production API)"
                className="flex-1 px-3 py-2 rounded-lg bg-secondary/30 border border-border/40 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                data-testid="api-key-name-input"
              />
              <button
                onClick={handleCreateApiKey}
                disabled={creatingKey || !newKeyName.trim()}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-primary text-white hover:opacity-90 transition-interactive disabled:opacity-50"
                data-testid="create-api-key-button"
              >
                {creatingKey ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                <span>Create</span>
              </button>
            </div>

            {/* Keys List */}
            {loadingKeys ? (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 size={16} className="animate-spin" />
                <span>Loading keys...</span>
              </div>
            ) : apiKeys.length === 0 ? (
              <p className="text-sm text-muted-foreground">No API keys created yet.</p>
            ) : (
              <div className="space-y-2">
                {apiKeys.map((key) => (
                  <div
                    key={key.key_id}
                    className="flex items-center justify-between p-3 rounded-lg bg-secondary/30 border border-border/40"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm">{key.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {key.key_prefix}... • Used {key.usage_count || 0} times
                        {key.last_used_at && ` • Last used ${new Date(key.last_used_at).toLocaleDateString()}`}
                      </p>
                    </div>
                    <button
                      onClick={() => handleRevokeKey(key.key_id)}
                      className="p-2 rounded hover:bg-destructive/10 text-destructive"
                      title="Revoke key"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Appearance Section */}
          <div className="glass rounded-2xl p-6 md:p-8 border border-border/60">
            <h3 className="text-lg font-medium mb-4">Appearance</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Customize how TickFlow looks on your device.
            </p>

            <div className="space-y-3">
              {/* Dark Mode */}
              <button
                onClick={() => handleThemeChange('dark')}
                className={`w-full flex items-center justify-between p-4 rounded-lg border transition-interactive ${
                  theme === 'dark'
                    ? 'bg-primary/10 border-primary'
                    : 'bg-secondary/30 border-border/40 hover:border-border/60'
                }`}
                data-testid="theme-dark-button"
              >
                <div className="flex items-center gap-3">
                  <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                    theme === 'dark' ? 'bg-primary/20 text-primary' : 'bg-secondary/50'
                  }`}>
                    <Moon size={20} />
                  </div>
                  <div className="text-left">
                    <p className="font-medium">Dark Mode</p>
                    <p className="text-sm text-muted-foreground">Sleek glassmorphism dark theme</p>
                  </div>
                </div>
                {theme === 'dark' && (
                  <div className="h-5 w-5 rounded-full bg-primary flex items-center justify-center">
                    <svg
                      className="w-3 h-3 text-primary-foreground"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={3}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                )}
              </button>

              {/* Light Mode */}
              <button
                onClick={() => handleThemeChange('light')}
                className={`w-full flex items-center justify-between p-4 rounded-lg border transition-interactive ${
                  theme === 'light'
                    ? 'bg-primary/10 border-primary'
                    : 'bg-secondary/30 border-border/40 hover:border-border/60'
                }`}
                data-testid="theme-light-button"
              >
                <div className="flex items-center gap-3">
                  <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                    theme === 'light' ? 'bg-primary/20 text-primary' : 'bg-secondary/50'
                  }`}>
                    <Sun size={20} />
                  </div>
                  <div className="text-left">
                    <p className="font-medium">Light Mode</p>
                    <p className="text-sm text-muted-foreground">Clean and bright interface</p>
                  </div>
                </div>
                {theme === 'light' && (
                  <div className="h-5 w-5 rounded-full bg-primary flex items-center justify-center">
                    <svg
                      className="w-3 h-3 text-primary-foreground"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={3}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                )}
              </button>
            </div>
          </div>

          {/* Account Section */}
          <div className="glass rounded-2xl p-6 md:p-8 border border-border/60">
            <h3 className="text-lg font-medium mb-4">Account</h3>
            
            <div className="space-y-4">
              <div className="glass rounded-lg p-4 bg-secondary/30">
                <p className="text-sm text-muted-foreground mb-2">Signed in as</p>
                <div className="flex items-center gap-3">
                  {user.picture ? (
                    <img src={user.picture} alt={user.name} className="w-10 h-10 rounded-full" />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-gradient-primary flex items-center justify-center text-white font-medium">
                      {user.name?.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div>
                    <p className="font-medium">{user.name}</p>
                    <p className="text-sm text-muted-foreground">{user.email}</p>
                  </div>
                </div>
              </div>

              <button
                onClick={handleLogout}
                disabled={loggingOut}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-destructive/50 text-destructive hover:bg-destructive/10 transition-interactive disabled:opacity-50"
                data-testid="logout-button"
              >
                {loggingOut ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <LogOut size={16} />
                )}
                <span>{loggingOut ? 'Logging out...' : 'Sign Out'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
