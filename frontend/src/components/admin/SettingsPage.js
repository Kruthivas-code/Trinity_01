import React, { useState, useEffect } from 'react';
import { ArrowLeft, Sun, Moon, Mail, CheckCircle, XCircle, Loader2, RefreshCw, ExternalLink, LogOut, Key, Copy, Trash2, Plus, Download, FileText, Users, Ticket, LayoutGrid, BookOpen } from 'lucide-react';
import PortalCategoryManager from './PortalCategoryManager';
import KBArticleManager from './KBArticleManager';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTheme } from '../../contexts/ThemeContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const SettingsPage = ({ user }) => {
  const navigate = useNavigate();
  const { theme, setThemeMode } = useTheme();
  
  const [loggingOut, setLoggingOut] = useState(false);
  
  // API Keys state
  const [apiKeys, setApiKeys] = useState([]);
  const [loadingKeys, setLoadingKeys] = useState(true);
  const [creatingKey, setCreatingKey] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [showNewKey, setShowNewKey] = useState(null);
  
  // Export state
  const [exporting, setExporting] = useState(null);

  useEffect(() => {
    if (user) {
      fetchApiKeys();
    }
  }, [user]);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await fetch(`${BACKEND_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
      
      localStorage.removeItem('theme');
      
      // Success
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
      // Error
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
      // Success
    } catch (error) {
      // Error
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
      
      // Success
      fetchApiKeys();
    } catch (error) {
      // Error
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    // Success
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
      
      // Success
    } catch (error) {
      // Error
    }
  };

  const handleExport = async (type) => {
    setExporting(type);
    try {
      let url = '';
      let filename = '';
      
      switch (type) {
        case 'tickets':
          url = `${BACKEND_URL}/api/tickets?limit=10000`;
          filename = `trinity-tickets-${new Date().toISOString().split('T')[0]}.json`;
          break;
        case 'users':
          url = `${BACKEND_URL}/api/users`;
          filename = `trinity-users-${new Date().toISOString().split('T')[0]}.json`;
          break;
        case 'teams':
          url = `${BACKEND_URL}/api/teams`;
          filename = `trinity-teams-${new Date().toISOString().split('T')[0]}.json`;
          break;
        case 'shifts':
          url = `${BACKEND_URL}/api/shifts`;
          filename = `trinity-shifts-${new Date().toISOString().split('T')[0]}.json`;
          break;
        default:
          return;
      }
      
      const response = await fetch(url, { credentials: 'include' });
      if (!response.ok) throw new Error('Export failed');
      
      let data = await response.json();
      // Handle paginated response format
      if (data.tickets) data = data.tickets;
      else if (data.items) data = data.items;
      else if (data.customers) data = data.customers;
      
      // Create and download file
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setExporting(null);
    }
  };

  const handleExportCSV = async (type) => {
    setExporting(type + '-csv');
    try {
      let url = '';
      let filename = '';
      let headers = [];
      
      switch (type) {
        case 'tickets':
          url = `${BACKEND_URL}/api/tickets?limit=10000`;
          filename = `trinity-tickets-${new Date().toISOString().split('T')[0]}.csv`;
          headers = ['ticket_id', 'title', 'status', 'priority', 'escalation_level', 'assignee_id', 'created_at'];
          break;
        case 'users':
          url = `${BACKEND_URL}/api/users`;
          filename = `trinity-users-${new Date().toISOString().split('T')[0]}.csv`;
          headers = ['user_id', 'name', 'email', 'role', 'created_at'];
          break;
        case 'teams':
          url = `${BACKEND_URL}/api/teams`;
          filename = `trinity-teams-${new Date().toISOString().split('T')[0]}.csv`;
          headers = ['team_id', 'name', 'escalation_level', 'member_count'];
          break;
        default:
          return;
      }
      
      const response = await fetch(url, { credentials: 'include' });
      if (!response.ok) throw new Error('Export failed');
      
      let data = await response.json();
      if (data.tickets) data = data.tickets;
      else if (data.items) data = data.items;
      else if (data.customers) data = data.customers;
      
      // Convert to CSV
      const csvRows = [headers.join(',')];
      data.forEach(item => {
        const row = headers.map(h => {
          const val = item[h] || '';
          // Escape commas and quotes in values
          const escaped = String(val).replace(/"/g, '""');
          return escaped.includes(',') || escaped.includes('"') ? `"${escaped}"` : escaped;
        });
        csvRows.push(row.join(','));
      });
      
      const csvContent = csvRows.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('CSV Export failed:', error);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="h-full">
      {/* Header */}
      <header className="sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150">
        <div className="px-6 h-14 flex items-center">
          <h1 className="text-lg font-semibold">Settings</h1>
        </div>
      </header>

      {/* Content */}
      <div className="p-6 space-y-6 max-w-4xl">
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
                        {key.last_used_at && ` • Last used ${new Date(key.last_used_at?.endsWith?.('Z') ? key.last_used_at : key.last_used_at + 'Z').toLocaleString('en-US', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true })}`}
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
              Customize how Trinity looks on your device.
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

          {/* Portal Categories Section */}
          <div className="glass rounded-2xl p-6 md:p-8 border border-border/60">
            <div className="flex items-center gap-3 mb-6">
              <div className="h-10 w-10 rounded-lg bg-gradient-primary flex items-center justify-center">
                <LayoutGrid size={20} className="text-white" />
              </div>
              <div>
                <h3 className="text-lg font-medium">Portal Categories</h3>
                <p className="text-sm text-muted-foreground">
                  Manage issue categories shown on the customer portal
                </p>
              </div>
            </div>
            <PortalCategoryManager />
          </div>

          {/* KB Articles Section */}
          <div className="glass rounded-2xl p-6 md:p-8 border border-border/60">
            <div className="flex items-center gap-3 mb-6">
              <div className="h-10 w-10 rounded-lg bg-gradient-primary flex items-center justify-center">
                <BookOpen size={20} className="text-white" />
              </div>
              <div>
                <h3 className="text-lg font-medium">KB Articles</h3>
                <p className="text-sm text-muted-foreground">
                  Manage documentation articles shown at /docs
                </p>
              </div>
            </div>
            <KBArticleManager />
          </div>

          {/* Data Export Section */}
          <div className="glass rounded-2xl p-6 md:p-8 border border-border/60">
            <div className="flex items-center gap-3 mb-4">
              <Download className="text-primary" size={24} />
              <div>
                <h3 className="text-lg font-medium">Data Export</h3>
                <p className="text-sm text-muted-foreground">Export your data in JSON or CSV format</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Tickets Export */}
              <div className="p-4 rounded-lg bg-secondary/30 border border-border/30">
                <div className="flex items-center gap-3 mb-3">
                  <Ticket size={20} className="text-muted-foreground" />
                  <div>
                    <p className="font-medium">Tickets</p>
                    <p className="text-xs text-muted-foreground">Export all ticket data</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleExport('tickets')}
                    disabled={exporting === 'tickets'}
                    className="flex-1 h-8 px-3 text-xs font-medium rounded-lg bg-primary/20 text-primary hover:bg-primary/30 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                    data-testid="export-tickets-json"
                  >
                    {exporting === 'tickets' ? <Loader2 size={12} className="animate-spin" /> : <FileText size={12} />}
                    JSON
                  </button>
                  <button
                    onClick={() => handleExportCSV('tickets')}
                    disabled={exporting === 'tickets-csv'}
                    className="flex-1 h-8 px-3 text-xs font-medium rounded-lg bg-secondary/50 hover:bg-secondary/70 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                    data-testid="export-tickets-csv"
                  >
                    {exporting === 'tickets-csv' ? <Loader2 size={12} className="animate-spin" /> : <FileText size={12} />}
                    CSV
                  </button>
                </div>
              </div>

              {/* Users Export */}
              <div className="p-4 rounded-lg bg-secondary/30 border border-border/30">
                <div className="flex items-center gap-3 mb-3">
                  <Users size={20} className="text-muted-foreground" />
                  <div>
                    <p className="font-medium">Users</p>
                    <p className="text-xs text-muted-foreground">Export user profiles</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleExport('users')}
                    disabled={exporting === 'users'}
                    className="flex-1 h-8 px-3 text-xs font-medium rounded-lg bg-primary/20 text-primary hover:bg-primary/30 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                    data-testid="export-users-json"
                  >
                    {exporting === 'users' ? <Loader2 size={12} className="animate-spin" /> : <FileText size={12} />}
                    JSON
                  </button>
                  <button
                    onClick={() => handleExportCSV('users')}
                    disabled={exporting === 'users-csv'}
                    className="flex-1 h-8 px-3 text-xs font-medium rounded-lg bg-secondary/50 hover:bg-secondary/70 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                    data-testid="export-users-csv"
                  >
                    {exporting === 'users-csv' ? <Loader2 size={12} className="animate-spin" /> : <FileText size={12} />}
                    CSV
                  </button>
                </div>
              </div>

              {/* Teams Export */}
              <div className="p-4 rounded-lg bg-secondary/30 border border-border/30">
                <div className="flex items-center gap-3 mb-3">
                  <Users size={20} className="text-muted-foreground" />
                  <div>
                    <p className="font-medium">Teams</p>
                    <p className="text-xs text-muted-foreground">Export team configurations</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleExport('teams')}
                    disabled={exporting === 'teams'}
                    className="flex-1 h-8 px-3 text-xs font-medium rounded-lg bg-primary/20 text-primary hover:bg-primary/30 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                    data-testid="export-teams-json"
                  >
                    {exporting === 'teams' ? <Loader2 size={12} className="animate-spin" /> : <FileText size={12} />}
                    JSON
                  </button>
                  <button
                    onClick={() => handleExportCSV('teams')}
                    disabled={exporting === 'teams-csv'}
                    className="flex-1 h-8 px-3 text-xs font-medium rounded-lg bg-secondary/50 hover:bg-secondary/70 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                    data-testid="export-teams-csv"
                  >
                    {exporting === 'teams-csv' ? <Loader2 size={12} className="animate-spin" /> : <FileText size={12} />}
                    CSV
                  </button>
                </div>
              </div>

              {/* Shifts Export */}
              <div className="p-4 rounded-lg bg-secondary/30 border border-border/30">
                <div className="flex items-center gap-3 mb-3">
                  <Download size={20} className="text-muted-foreground" />
                  <div>
                    <p className="font-medium">Shifts</p>
                    <p className="text-xs text-muted-foreground">Export shift schedules</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleExport('shifts')}
                    disabled={exporting === 'shifts'}
                    className="flex-1 h-8 px-3 text-xs font-medium rounded-lg bg-primary/20 text-primary hover:bg-primary/30 transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                    data-testid="export-shifts-json"
                  >
                    {exporting === 'shifts' ? <Loader2 size={12} className="animate-spin" /> : <FileText size={12} />}
                    JSON
                  </button>
                </div>
              </div>
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
  );
};

export default SettingsPage;
