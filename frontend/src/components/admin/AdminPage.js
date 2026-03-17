import React, { useState, useEffect } from 'react';
import { 
  Settings, Plus, Trash2, Save, X, ChevronDown, ChevronRight,
  Type, Hash, Calendar, ToggleLeft, List, Building, User, Ticket,
  Loader2, GripVertical, Clock, Users, UserPlus, Zap, Download,
  FileJson, FileSpreadsheet, Database, Filter, CheckCircle2, AlertTriangle,
  Timer, RefreshCw, Play, Square, Activity
} from 'lucide-react';
import RoutingRulesTab from './RoutingRulesTab';
import SLAEscalationTab from './SLAEscalationTab';
import SLAPoliciesTab from './SLAPoliciesTab';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const FIELD_TYPES = [
  { value: 'text', label: 'Text', icon: Type, description: 'Single line text input' },
  { value: 'number', label: 'Number', icon: Hash, description: 'Numeric value' },
  { value: 'select', label: 'Dropdown', icon: List, description: 'Select from options' },
  { value: 'date', label: 'Date', icon: Calendar, description: 'Date picker' },
  { value: 'boolean', label: 'Yes/No', icon: ToggleLeft, description: 'Toggle switch' }
];

const DAYS_OF_WEEK = [
  { value: 1, label: 'Mon' },
  { value: 2, label: 'Tue' },
  { value: 3, label: 'Wed' },
  { value: 4, label: 'Thu' },
  { value: 5, label: 'Fri' },
  { value: 6, label: 'Sat' },
  { value: 7, label: 'Sun' }
];

// Export Data Tab Component
const ExportDataTab = () => {
  const [exportFormat, setExportFormat] = useState('json');
  const [exportType, setExportType] = useState('full');
  const [includeNotes, setIncludeNotes] = useState(true);
  const [includeChangelog, setIncludeChangelog] = useState(true);
  const [includeCsat, setIncludeCsat] = useState(true);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [statusFilter, setStatusFilter] = useState([]);
  const [exporting, setExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(null);

  const handleExport = async () => {
    setExporting(true);
    setExportSuccess(null);
    
    try {
      let endpoint = '';
      let method = 'POST';
      let body = null;
      
      switch (exportType) {
        case 'full':
          endpoint = `${BACKEND_URL}/api/admin/export/full`;
          body = JSON.stringify({
            format: exportFormat,
            include_notes: includeNotes,
            include_changelog: includeChangelog,
            include_csat: includeCsat
          });
          break;
        case 'tickets':
          endpoint = `${BACKEND_URL}/api/admin/export/tickets`;
          body = JSON.stringify({
            format: exportFormat,
            include_notes: includeNotes,
            include_changelog: includeChangelog,
            include_csat: includeCsat,
            date_from: dateFrom || null,
            date_to: dateTo || null,
            status_filter: statusFilter.length > 0 ? statusFilter : null
          });
          break;
        case 'customers':
          endpoint = `${BACKEND_URL}/api/admin/export/customers?format=${exportFormat}`;
          method = 'GET';
          break;
        case 'analytics':
          endpoint = `${BACKEND_URL}/api/admin/export/analytics?days=90&format=${exportFormat}`;
          method = 'GET';
          break;
        default:
          endpoint = `${BACKEND_URL}/api/admin/export/full`;
      }
      
      const options = {
        method,
        credentials: 'include',
        headers: body ? { 'Content-Type': 'application/json' } : {}
      };
      if (body) options.body = body;
      
      const response = await fetch(endpoint, options);
      
      if (!response.ok) throw new Error('Export failed');
      
      // Get filename from Content-Disposition header or generate one
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `export_${exportType}_${new Date().toISOString().split('T')[0]}.${exportFormat}`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=([^;]+)/);
        if (match) filename = match[1].trim();
      }
      
      // Download the file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      setExportSuccess(`Export downloaded: ${filename}`);
    } catch (error) {
      console.error('Export failed:', error);
      setExportSuccess('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const exportTypes = [
    { 
      id: 'full', 
      label: 'Full System Export', 
      description: 'All data including tickets, users, teams, settings',
      icon: Database
    },
    { 
      id: 'tickets', 
      label: 'Tickets Only', 
      description: 'All tickets with notes, changelog, and CSAT',
      icon: Ticket
    },
    { 
      id: 'customers', 
      label: 'Customers', 
      description: 'Customer data with ticket history summary',
      icon: Users
    },
    { 
      id: 'analytics', 
      label: 'Analytics Report', 
      description: 'Performance metrics and statistics',
      icon: Download
    }
  ];

  const statuses = [
    { value: 'todo', label: 'Open' },
    { value: 'waiting', label: 'Waiting' },
    { value: 'closed', label: 'Closed' }
  ];

  return (
    <div className="max-w-4xl">
      <div className="mb-6">
        <h2 className="text-lg font-medium">Data Export</h2>
        <p className="text-sm text-muted-foreground">
          Export your data in JSON or CSV format for backup, analysis, or migration
        </p>
      </div>

      {/* Export Type Selection */}
      <div className="mb-8">
        <h3 className="text-sm font-medium mb-3">What do you want to export?</h3>
        <div className="grid grid-cols-2 gap-4">
          {exportTypes.map(type => (
            <button
              key={type.id}
              onClick={() => setExportType(type.id)}
              className={`p-4 rounded-xl border text-left transition-all ${
                exportType === type.id
                  ? 'border-primary bg-primary/10'
                  : 'border-border hover:border-primary/50 hover:bg-secondary/30'
              }`}
              data-testid={`export-type-${type.id}`}
            >
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg ${
                  exportType === type.id ? 'bg-primary/20 text-primary' : 'bg-secondary/50 text-muted-foreground'
                }`}>
                  <type.icon size={20} />
                </div>
                <div>
                  <div className="font-medium">{type.label}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{type.description}</div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Format Selection */}
      <div className="mb-8">
        <h3 className="text-sm font-medium mb-3">Export Format</h3>
        <div className="flex gap-4">
          <button
            onClick={() => setExportFormat('json')}
            className={`flex-1 p-4 rounded-xl border flex items-center gap-3 transition-all ${
              exportFormat === 'json'
                ? 'border-primary bg-primary/10'
                : 'border-border hover:border-primary/50'
            }`}
            data-testid="export-format-json"
          >
            <FileJson size={24} className={exportFormat === 'json' ? 'text-primary' : 'text-muted-foreground'} />
            <div className="text-left">
              <div className="font-medium">JSON</div>
              <div className="text-xs text-muted-foreground">Structured data, best for imports</div>
            </div>
          </button>
          <button
            onClick={() => setExportFormat('csv')}
            className={`flex-1 p-4 rounded-xl border flex items-center gap-3 transition-all ${
              exportFormat === 'csv'
                ? 'border-primary bg-primary/10'
                : 'border-border hover:border-primary/50'
            }`}
            data-testid="export-format-csv"
          >
            <FileSpreadsheet size={24} className={exportFormat === 'csv' ? 'text-primary' : 'text-muted-foreground'} />
            <div className="text-left">
              <div className="font-medium">CSV</div>
              <div className="text-xs text-muted-foreground">Spreadsheet compatible</div>
            </div>
          </button>
        </div>
      </div>

      {/* Options for Tickets Export */}
      {(exportType === 'tickets' || exportType === 'full') && (
        <div className="mb-8 p-4 rounded-xl bg-secondary/20 border border-border/30">
          <h3 className="text-sm font-medium mb-4">Include Related Data</h3>
          <div className="space-y-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={includeNotes}
                onChange={(e) => setIncludeNotes(e.target.checked)}
                className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
              />
              <span className="text-sm">Notes & Replies</span>
              <span className="text-xs text-muted-foreground">Internal notes and customer replies</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={includeChangelog}
                onChange={(e) => setIncludeChangelog(e.target.checked)}
                className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
              />
              <span className="text-sm">Changelog</span>
              <span className="text-xs text-muted-foreground">All field change history</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={includeCsat}
                onChange={(e) => setIncludeCsat(e.target.checked)}
                className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
              />
              <span className="text-sm">CSAT Responses</span>
              <span className="text-xs text-muted-foreground">Customer satisfaction ratings</span>
            </label>
          </div>
        </div>
      )}

      {/* Filters for Tickets Export */}
      {exportType === 'tickets' && (
        <div className="mb-8 p-4 rounded-xl bg-secondary/20 border border-border/30">
          <h3 className="text-sm font-medium mb-4 flex items-center gap-2">
            <Filter size={16} />
            Filters (Optional)
          </h3>
          
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium mb-1.5 text-muted-foreground">From Date</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5 text-muted-foreground">To Date</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-xs font-medium mb-1.5 text-muted-foreground">Status Filter</label>
            <div className="flex flex-wrap gap-2">
              {statuses.map(status => (
                <button
                  key={status.value}
                  onClick={() => {
                    if (statusFilter.includes(status.value)) {
                      setStatusFilter(statusFilter.filter(s => s !== status.value));
                    } else {
                      setStatusFilter([...statusFilter, status.value]);
                    }
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    statusFilter.includes(status.value)
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary/50 text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {status.label}
                </button>
              ))}
              {statusFilter.length > 0 && (
                <button
                  onClick={() => setStatusFilter([])}
                  className="px-3 py-1.5 rounded-lg text-xs text-muted-foreground hover:text-foreground"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Export Button */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleExport}
          disabled={exporting}
          className="h-12 px-8 flex items-center gap-2 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          data-testid="export-button"
        >
          {exporting ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              Exporting...
            </>
          ) : (
            <>
              <Download size={18} />
              Export Data
            </>
          )}
        </button>
        
        {exportSuccess && (
          <div className={`flex items-center gap-2 text-sm ${
            exportSuccess.includes('failed') ? 'text-red-400' : 'text-emerald-400'
          }`}>
            <CheckCircle2 size={16} />
            {exportSuccess}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="mt-8 p-4 rounded-xl bg-blue-500/10 border border-blue-500/20">
        <h4 className="text-sm font-medium text-blue-400 mb-2">Export Information</h4>
        <ul className="text-xs text-muted-foreground space-y-1">
          <li>• Full export includes: tickets, users, teams, customers, settings, CSAT, leaves</li>
          <li>• Large exports may take a few moments to generate</li>
          <li>• JSON format preserves all data structure and relationships</li>
          <li>• CSV format flattens nested data into columns</li>
        </ul>
      </div>
    </div>
  );
};

// Atlas Control Panel Tab
const AtlasSyncTab = () => {
  const [syncStatus, setSyncStatus] = useState(null);
  const [parity, setParity] = useState(null);
  const [healthReport, setHealthReport] = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [apiTest, setApiTest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [testingApi, setTestingApi] = useState(false);
  const [pollInterval, setPollInterval] = useState(60);
  const [lookbackMinutes, setLookbackMinutes] = useState(60);
  const [activeSection, setActiveSection] = useState('health');

  const fetchStatus = async () => {
    try {
      const [syncRes, parityRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/admin/atlas/sync/status`, { credentials: 'include' }),
        fetch(`${BACKEND_URL}/api/admin/atlas/parity`, { credentials: 'include' }),
      ]);
      if (syncRes.ok) {
        const data = await syncRes.json();
        setSyncStatus(data);
        setPollInterval(data.poll_interval || 60);
        setLookbackMinutes(data.lookback_minutes || 60);
      }
      if (parityRes.ok) setParity(await parityRes.json());
    } catch (e) {
      console.error('Failed to fetch status:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchHealth = async () => {
    setHealthLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/atlas/sync-health`, { credentials: 'include' });
      if (res.ok) setHealthReport(await res.json());
    } catch (e) {
      console.error('Health audit failed:', e);
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchHealth();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (action) => {
    setActionLoading(true);
    try {
      await fetch(`${BACKEND_URL}/api/admin/atlas/sync/${action}`, { method: 'POST', credentials: 'include' });
      await fetchStatus();
    } finally { setActionLoading(false); }
  };

  const handleConfigSave = async () => {
    setActionLoading(true);
    try {
      await fetch(`${BACKEND_URL}/api/admin/atlas/sync/config`, {
        method: 'PATCH', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ poll_interval: pollInterval, lookback_minutes: lookbackMinutes }),
      });
      await fetchStatus();
    } finally { setActionLoading(false); }
  };

  const handleTestApi = async () => {
    setTestingApi(true);
    setApiTest(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/atlas/test`, { credentials: 'include' });
      if (res.ok) setApiTest(await res.json());
    } catch (e) {
      setApiTest({ connection: 'error', error: e.message });
    } finally { setTestingApi(false); }
  };

  const isRunning = syncStatus?.is_running;
  const fs = syncStatus?.full_sync || parity?.full_sync || {};
  const fsPct = fs.total > 0 ? Math.round((fs.cursor / fs.total) * 100) : 0;
  const fsEta = fs.total > 0 && fs.cursor > 0
    ? `~${Math.round(((fs.total - fs.cursor) / 100) * (pollInterval / 60))} min`
    : '';

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="animate-spin text-muted-foreground" size={24} />
      </div>
    );
  }

  const sections = [
    { id: 'health', label: 'Sync Health', icon: CheckCircle2 },
    { id: 'dashboard', label: 'Sync Engine', icon: Activity },
    { id: 'api-health', label: 'API Health', icon: Zap },
    { id: 'parity', label: 'Data Parity', icon: Database },
    { id: 'config', label: 'Configuration', icon: Settings },
  ];

  return (
    <div className="max-w-5xl" data-testid="atlas-control-panel">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-medium">Atlas Control Panel</h2>
          <p className="text-sm text-muted-foreground">
            Manage sync, monitor parity, and test connectivity
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${isRunning ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-500'}`} />
          <span className="text-sm font-medium" data-testid="atlas-sync-status">
            {isRunning ? 'Sync Running' : 'Sync Stopped'}
          </span>
          {isRunning ? (
            <button onClick={() => handleAction('stop')} disabled={actionLoading}
              className="ml-2 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 text-xs font-medium"
              data-testid="atlas-sync-stop-btn">
              {actionLoading ? <Loader2 size={12} className="animate-spin" /> : <Square size={12} />} Stop
            </button>
          ) : (
            <button onClick={() => handleAction('start')} disabled={actionLoading}
              className="ml-2 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25 text-xs font-medium"
              data-testid="atlas-sync-start-btn">
              {actionLoading ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />} Start
            </button>
          )}
        </div>
      </div>

      {/* Section Tabs */}
      <div className="flex items-center gap-1 mb-6 p-1 rounded-lg bg-secondary/30 border border-border/30 w-fit">
        {sections.map(s => (
          <button key={s.id} onClick={() => setActiveSection(s.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              activeSection === s.id ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:text-foreground'
            }`} data-testid={`atlas-section-${s.id}`}>
            <s.icon size={13} /> {s.label}
          </button>
        ))}
      </div>

      {/* ─── Sync Health Audit ─── */}
      {activeSection === 'health' && (
        <div className="space-y-4" data-testid="sync-health-panel">
          {/* Grade + Overall Score */}
          <div className="p-5 rounded-xl border border-border/40 bg-card/50">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-medium">Live Sync Health Audit</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Samples 200 conversations from Atlas and compares field-by-field with Trinity
                </p>
              </div>
              <button onClick={fetchHealth} disabled={healthLoading}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary/20 text-primary hover:bg-primary/30 text-sm font-medium transition-colors"
                data-testid="run-health-audit-btn">
                {healthLoading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                {healthLoading ? 'Auditing...' : 'Run Audit'}
              </button>
            </div>

            {healthReport && (
              <div className="space-y-4">
                {/* Grade badge */}
                <div className="flex items-center gap-4">
                  <div className={`text-4xl font-black px-4 py-2 rounded-xl ${
                    healthReport.grade === 'A' ? 'bg-emerald-500/15 text-emerald-400' :
                    healthReport.grade === 'B' ? 'bg-amber-500/15 text-amber-400' :
                    'bg-red-500/15 text-red-400'
                  }`} data-testid="health-grade">
                    {healthReport.grade}
                  </div>
                  <div>
                    <p className="text-2xl font-bold tabular-nums" data-testid="health-pct">
                      {healthReport.overall_pct}%
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {healthReport.total_clean}/{healthReport.total_checked} clean · {healthReport.total_diffs} diffs · {healthReport.total_missing} missing
                    </p>
                  </div>
                </div>

                {/* Per-window breakdown */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {healthReport.windows?.map((w, i) => (
                    <div key={i} className="p-3 rounded-lg bg-secondary/20 border border-border/20">
                      <p className="text-[10px] text-muted-foreground mb-1">{w.label}</p>
                      {w.error ? (
                        <p className="text-xs text-red-400">{w.error}</p>
                      ) : (
                        <>
                          <p className={`text-lg font-bold tabular-nums ${
                            w.pct >= 98 ? 'text-emerald-400' : w.pct >= 80 ? 'text-amber-400' : 'text-red-400'
                          }`}>{w.pct}%</p>
                          <p className="text-[10px] text-muted-foreground">
                            {w.clean}/{w.checked} clean · {w.diffs}d · {w.missing}m
                          </p>
                        </>
                      )}
                    </div>
                  ))}
                </div>

                {/* Sync Engine Status */}
                <div className="p-4 rounded-lg bg-secondary/10 border border-border/20">
                  <h4 className="text-xs font-medium mb-2">Sync Engine</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                    <div>
                      <p className="text-[10px] text-muted-foreground">Status</p>
                      <div className="flex items-center gap-1.5">
                        <div className={`w-2 h-2 rounded-full ${healthReport.engine?.is_running ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-500'}`} />
                        <p className="text-xs font-medium">{healthReport.engine?.is_running ? 'Running' : 'Stopped'}</p>
                      </div>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground">Phase 2</p>
                      <p className="text-xs font-medium">{healthReport.engine?.phase2_pct}% ({healthReport.engine?.phase2_cursor?.toLocaleString()}/{healthReport.engine?.phase2_total?.toLocaleString()})</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground">ETA</p>
                      <p className="text-xs font-medium">{healthReport.engine?.phase2_eta_minutes > 0 ? `~${healthReport.engine.phase2_eta_minutes}m` : 'Complete'}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground">Passes</p>
                      <p className="text-xs font-medium">#{healthReport.engine?.phase2_passes}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground">Cycles</p>
                      <p className="text-xs font-medium">{healthReport.engine?.cycles?.toLocaleString()}</p>
                    </div>
                  </div>
                  {/* Phase 2 progress bar */}
                  <div className="mt-2 h-1.5 bg-secondary/40 rounded-full overflow-hidden">
                    <div className="h-full bg-amber-500 rounded-full transition-all" style={{ width: `${healthReport.engine?.phase2_pct || 0}%` }} />
                  </div>
                </div>

                {/* Open Ticket Breakdown */}
                <div className="p-4 rounded-lg bg-secondary/10 border border-border/20">
                  <h4 className="text-xs font-medium mb-2">Open Tickets</h4>
                  <div className="grid grid-cols-4 gap-3">
                    <StatCard label="Total Open" value={healthReport.open_tickets?.total} />
                    <StatCard label="Zeus (AI)" value={healthReport.open_tickets?.zeus} />
                    <StatCard label="Human Assigned" value={healthReport.open_tickets?.human_assigned} />
                    <StatCard label="Human Unassigned" value={healthReport.open_tickets?.human_unassigned}
                      isError={healthReport.open_tickets?.human_unassigned > 50} />
                  </div>
                </div>

                {/* Linking */}
                <div className="p-4 rounded-lg bg-secondary/10 border border-border/20">
                  <h4 className="text-xs font-medium mb-2">Atlas Linking</h4>
                  <div className="grid grid-cols-3 gap-3">
                    <StatCard label="Linked" value={`${healthReport.linking?.linked_pct}%`} />
                    <StatCard label="Total" value={healthReport.linking?.total_tickets?.toLocaleString()} />
                    <StatCard label="Unlinked (open)" value={healthReport.linking?.non_closed_unlinked}
                      isError={healthReport.linking?.non_closed_unlinked > 10} />
                  </div>
                </div>

                {/* Diffs table */}
                {healthReport.diffs?.length > 0 && (
                  <div className="p-4 rounded-lg bg-red-500/5 border border-red-500/20">
                    <h4 className="text-xs font-medium text-red-400 mb-2">Field Differences ({healthReport.total_diffs})</h4>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {healthReport.diffs.map((d, i) => (
                        <div key={i} className="p-2 rounded bg-secondary/30 text-xs">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium">{d.ticket} <span className="text-muted-foreground">(#{d.atlas_num})</span></span>
                            <span className="text-[10px] text-muted-foreground">
                              {d.synced_minutes_ago != null ? `synced ${d.synced_minutes_ago}m ago` : 'never synced'}
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {d.issues.map((issue, j) => (
                              <span key={j} className="px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 text-[10px]">
                                {issue.field}: {issue.trinity} ≠ {issue.atlas}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Timestamp */}
                <p className="text-[10px] text-muted-foreground text-right">
                  Audit ran at {new Date(healthReport.timestamp).toLocaleString()}
                </p>
              </div>
            )}

            {!healthReport && !healthLoading && (
              <p className="text-sm text-muted-foreground">Click "Run Audit" to check sync health, or it will auto-run on page load.</p>
            )}
          </div>
        </div>
      )}

      {/* ─── Sync Dashboard ─── */}
      {activeSection === 'dashboard' && (
        <div className="space-y-4">
          {/* Phase 1: Realtime */}
          <div className="p-4 rounded-xl border border-border/40 bg-card/50">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-blue-400" />
              <h3 className="text-sm font-medium">Phase 1 — Realtime Sync</h3>
              <span className="text-[10px] text-muted-foreground ml-auto">every {syncStatus?.poll_interval || 60}s · last {syncStatus?.lookback_minutes || 15} min</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatCard label="Conversations" value={syncStatus?.conversations_checked || 0} />
              <StatCard label="New Tickets" value={syncStatus?.new_tickets_created || 0} />
              <StatCard label="Messages" value={syncStatus?.messages_synced || 0} />
              <StatCard label="Field Updates" value={syncStatus?.field_updates || 0} />
            </div>
          </div>

          {/* Phase 2: Full Sync */}
          <div className="p-4 rounded-xl border border-border/40 bg-card/50">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-amber-400" />
              <h3 className="text-sm font-medium">Phase 2 — Full Comprehensive Sync</h3>
              <span className="text-[10px] text-muted-foreground ml-auto">
                pass #{fs.completed_passes || 0} · 100/cycle · 45-day window
              </span>
            </div>
            {/* Progress bar */}
            <div className="mb-3">
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                <span>{(fs.cursor || 0).toLocaleString()} / {(fs.total || 0).toLocaleString()} conversations</span>
                <span>{fsPct}% {fsEta && `· ETA ${fsEta}`}</span>
              </div>
              <div className="h-2 bg-secondary/40 rounded-full overflow-hidden">
                <div className="h-full bg-amber-500 rounded-full transition-all duration-500"
                  style={{ width: `${fsPct}%` }} data-testid="full-sync-progress" />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <StatCard label="Passes Done" value={fs.completed_passes || 0} />
              <StatCard label="Sidebars" value={syncStatus?.sidebars_synced || 0} />
              <StatCard label="Conflicts" value={syncStatus?.conflicts_skipped || 0} />
            </div>
            {fs.last_completed_at && (
              <p className="text-[10px] text-muted-foreground mt-2">
                Last full pass: {new Date(fs.last_completed_at).toLocaleString()}
              </p>
            )}
          </div>

          {/* Cycle + Timing */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-lg bg-secondary/20 border border-border/20 text-center">
              <p className="text-xs text-muted-foreground">Cycles</p>
              <p className="text-xl font-semibold tabular-nums">{(syncStatus?.cycles_completed || 0).toLocaleString()}</p>
            </div>
            <div className="p-3 rounded-lg bg-secondary/20 border border-border/20 text-center">
              <p className="text-xs text-muted-foreground">Last Sync</p>
              <p className="text-sm font-medium">{syncStatus?.last_sync_at ? new Date(syncStatus.last_sync_at).toLocaleTimeString() : '—'}</p>
            </div>
            <div className="p-3 rounded-lg bg-secondary/20 border border-border/20 text-center">
              <p className="text-xs text-muted-foreground">Errors</p>
              <p className={`text-xl font-semibold ${(syncStatus?.errors?.length || 0) > 0 ? 'text-red-400' : ''}`}>
                {(syncStatus?.errors || []).length}
              </p>
            </div>
          </div>

          {/* Recent Errors */}
          {syncStatus?.errors?.length > 0 && (
            <div className="p-3 rounded-xl border border-red-500/20 bg-red-500/5">
              <h4 className="text-xs font-medium text-red-400 mb-2">Recent Errors</h4>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {syncStatus.errors.slice(-5).reverse().map((err, i) => (
                  <div key={i} className="text-[11px] text-muted-foreground p-1.5 rounded bg-secondary/30">
                    <span className="text-red-400 mr-2">{new Date(err.time).toLocaleTimeString()}</span>
                    {err.error}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ─── API Health ─── */}
      {activeSection === 'api-health' && (
        <div className="space-y-4">
          <div className="p-5 rounded-xl border border-border/40 bg-card/50">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium">Atlas API Connection Test</h3>
              <button onClick={handleTestApi} disabled={testingApi}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary/20 text-primary hover:bg-primary/30 text-sm font-medium transition-colors"
                data-testid="atlas-test-btn">
                {testingApi ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                {testingApi ? 'Testing...' : 'Test Connection'}
              </button>
            </div>

            {apiTest && (
              <div className="space-y-3">
                {/* Status badge */}
                <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium ${
                  apiTest.connection === 'healthy' ? 'bg-emerald-500/15 text-emerald-400' :
                  apiTest.connection === 'auth_failed' ? 'bg-red-500/15 text-red-400' :
                  'bg-amber-500/15 text-amber-400'
                }`} data-testid="atlas-test-result">
                  {apiTest.connection === 'healthy' ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
                  {apiTest.connection === 'healthy' ? 'Connected' :
                   apiTest.connection === 'auth_failed' ? 'Authentication Failed' :
                   apiTest.connection === 'timeout' ? 'Timeout' : 'Error'}
                </div>

                {/* Details */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 rounded-lg bg-secondary/20">
                    <p className="text-[10px] text-muted-foreground">Status Code</p>
                    <p className="text-sm font-medium">{apiTest.status_code || '—'}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/20">
                    <p className="text-[10px] text-muted-foreground">Response Time</p>
                    <p className="text-sm font-medium">{apiTest.response_time_ms ? `${apiTest.response_time_ms}ms` : '—'}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/20">
                    <p className="text-[10px] text-muted-foreground">Atlas Conversations</p>
                    <p className="text-sm font-medium">{apiTest.total_conversations?.toLocaleString() || '—'}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/20">
                    <p className="text-[10px] text-muted-foreground">API Key</p>
                    <p className="text-sm font-mono font-medium">{apiTest.key_masked || '—'}</p>
                  </div>
                </div>

                {apiTest.error && (
                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                    {apiTest.error}
                  </div>
                )}
              </div>
            )}

            {!apiTest && !testingApi && (
              <p className="text-sm text-muted-foreground">Click "Test Connection" to verify Atlas API connectivity, key validity, and response time.</p>
            )}
          </div>
        </div>
      )}

      {/* ─── Data Parity ─── */}
      {activeSection === 'parity' && parity && (
        <div className="space-y-4">
          {/* Parity Score */}
          <div className="p-5 rounded-xl border border-border/40 bg-card/50">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium">Data Parity Score</h3>
              <div className={`text-2xl font-bold tabular-nums ${
                parity.parity_pct >= 98 ? 'text-emerald-400' :
                parity.parity_pct >= 90 ? 'text-amber-400' : 'text-red-400'
              }`} data-testid="parity-score">
                {parity.parity_pct}%
              </div>
            </div>
            <div className="h-2 bg-secondary/40 rounded-full overflow-hidden mb-4">
              <div className={`h-full rounded-full transition-all ${
                parity.parity_pct >= 98 ? 'bg-emerald-500' :
                parity.parity_pct >= 90 ? 'bg-amber-500' : 'bg-red-500'
              }`} style={{ width: `${parity.parity_pct}%` }} />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatCard label="Trinity Total" value={parity.trinity_total} />
              <StatCard label="Atlas Total" value={parity.atlas_total} />
              <StatCard label="Linked" value={parity.atlas_linked} />
              <StatCard label="Missing" value={parity.missing_from_trinity} isError={parity.missing_from_trinity > 0} />
            </div>
          </div>

          {/* Ticket IDs */}
          <div className="p-5 rounded-xl border border-border/40 bg-card/50">
            <h3 className="text-sm font-medium mb-3">Ticket ID Alignment</h3>
            <div className="grid grid-cols-3 gap-3">
              <StatCard label="ID Match" value={parity.ticket_ids_matched} />
              <StatCard label="ID Mismatch" value={parity.ticket_ids_mismatched} isError={parity.ticket_ids_mismatched > 0} />
              <StatCard label="IMAP-Only" value={parity.imap_only} />
            </div>
          </div>

          {/* Users */}
          <div className="p-5 rounded-xl border border-border/40 bg-card/50">
            <h3 className="text-sm font-medium mb-3">Users</h3>
            <div className="grid grid-cols-2 gap-3">
              <StatCard label="Total Users" value={parity.users?.total || 0} />
              <StatCard label="Placeholder Emails" value={parity.users?.imported_local_emails || 0}
                isError={(parity.users?.imported_local_emails || 0) > 0} />
            </div>
          </div>

          {/* Full Sync Progress */}
          <div className="p-5 rounded-xl border border-border/40 bg-card/50">
            <h3 className="text-sm font-medium mb-3">Full Sync Progress</h3>
            <div className="grid grid-cols-4 gap-3">
              <StatCard label="Cursor" value={parity.full_sync?.cursor || 0} />
              <StatCard label="Total" value={parity.full_sync?.total || 0} />
              <StatCard label="Passes" value={parity.full_sync?.completed_passes || 0} />
              <div className="p-3 rounded-lg bg-secondary/30 border border-border/20">
                <p className="text-xs text-muted-foreground mb-1">Last Pass</p>
                <p className="text-sm font-medium">
                  {parity.full_sync?.last_completed_at
                    ? new Date(parity.full_sync.last_completed_at).toLocaleDateString()
                    : 'In progress'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── Configuration ─── */}
      {activeSection === 'config' && (
        <div className="space-y-4">
          <div className="p-5 rounded-xl border border-border/40 bg-card/50">
            <h3 className="text-sm font-medium mb-4">Sync Configuration</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Poll Interval (seconds)</label>
                <input type="number" value={pollInterval}
                  onChange={(e) => setPollInterval(parseInt(e.target.value) || 60)}
                  min={10} max={600}
                  className="w-full px-3 py-2 rounded-lg bg-secondary/50 border border-border/40 text-sm"
                  data-testid="atlas-sync-poll-interval" />
                <p className="text-[10px] text-muted-foreground mt-1">How often the sync daemon runs (10-600s)</p>
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Lookback Window (minutes)</label>
                <input type="number" value={lookbackMinutes}
                  onChange={(e) => setLookbackMinutes(parseInt(e.target.value) || 15)}
                  min={5} max={120}
                  className="w-full px-3 py-2 rounded-lg bg-secondary/50 border border-border/40 text-sm"
                  data-testid="atlas-sync-lookback" />
                <p className="text-[10px] text-muted-foreground mt-1">Phase 1 fetches conversations updated in last N minutes</p>
              </div>
            </div>
            <button onClick={handleConfigSave} disabled={actionLoading}
              className="mt-4 flex items-center gap-2 px-4 py-2 rounded-lg bg-primary/20 text-primary hover:bg-primary/30 text-sm font-medium transition-colors"
              data-testid="atlas-sync-save-config">
              {actionLoading ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              Save Config
            </button>
          </div>

          {/* Info */}
          <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20">
            <h4 className="text-xs font-medium text-blue-400 mb-2">How 2-Phase Sync Works</h4>
            <ul className="text-[11px] text-muted-foreground space-y-1">
              <li><strong className="text-blue-300">Phase 1 (Realtime):</strong> Fetches conversations updated in the last {lookbackMinutes} minutes. Runs every {pollInterval}s. Keeps Trinity in near-real-time with Atlas.</li>
              <li><strong className="text-amber-300">Phase 2 (Full):</strong> Walks ALL conversations from the last 45 days (including CLOSED). Processes 100/cycle. When it reaches the end, starts a new pass. Catches everything Phase 1 might miss.</li>
              <li><strong className="text-foreground">Protection:</strong> Trinity-made changes (assignments, status) are protected for 5 minutes to prevent Atlas sync from overwriting them.</li>
            </ul>
          </div>
        </div>
      )}

      {/* Attachment Migration */}
      <AttachmentMigrationSection />
    </div>
  );
};

const AttachmentMigrationSection = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/atlas/attachments/status`, { credentials: 'include' });
      if (res.ok) setStatus(await res.json());
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (action) => {
    setActionLoading(true);
    try {
      await fetch(`${BACKEND_URL}/api/admin/atlas/attachments/${action}`, { method: 'POST', credentials: 'include' });
      await fetchStatus();
    } finally { setActionLoading(false); }
  };

  if (loading) return null;

  const isRunning = status?.is_running;
  const pct = status?.total_attachments > 0 ? Math.round((status.migrated / status.total_attachments) * 100) : 0;
  const mbTransferred = ((status?.bytes_transferred || 0) / (1024 * 1024)).toFixed(1);

  return (
    <div className="mt-8 pt-6 border-t border-border/20" data-testid="attachment-migration-section">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-medium">Attachment Migration</h3>
          <p className="text-xs text-muted-foreground">Migrate files from Atlas CDN to Emergent storage</p>
        </div>
        <div className="flex items-center gap-2">
          {isRunning ? (
            <button onClick={() => handleAction('stop')} disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 text-xs font-medium"
              data-testid="attachment-stop-btn">
              {actionLoading ? <Loader2 size={12} className="animate-spin" /> : <Square size={12} />} Stop
            </button>
          ) : (
            <button onClick={() => handleAction('start')} disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 text-xs font-medium"
              data-testid="attachment-start-btn">
              {actionLoading ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />} Start
            </button>
          )}
        </div>
      </div>

      {/* Progress */}
      {status?.total_attachments > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
            <span>{status.migrated.toLocaleString()} / {status.total_attachments.toLocaleString()} files</span>
            <span>{pct}% · {mbTransferred} MB</span>
          </div>
          <div className="h-1.5 bg-secondary/30 rounded-full overflow-hidden">
            <div className="h-full bg-emerald-500 rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}

      {/* Compact stats */}
      <div className="grid grid-cols-4 gap-3">
        <div className="text-center p-2 rounded-lg bg-secondary/20">
          <p className="text-xs text-muted-foreground">Status</p>
          <p className="text-sm font-medium">{status?.status || 'idle'}</p>
        </div>
        <div className="text-center p-2 rounded-lg bg-secondary/20">
          <p className="text-xs text-muted-foreground">Migrated</p>
          <p className="text-sm font-medium">{(status?.migrated || 0).toLocaleString()}</p>
        </div>
        <div className="text-center p-2 rounded-lg bg-secondary/20">
          <p className="text-xs text-muted-foreground">Skipped</p>
          <p className="text-sm font-medium">{(status?.skipped || 0).toLocaleString()}</p>
        </div>
        <div className="text-center p-2 rounded-lg bg-secondary/20">
          <p className="text-xs text-muted-foreground">Failed</p>
          <p className={`text-sm font-medium ${status?.failed > 0 ? 'text-red-400' : ''}`}>{(status?.failed || 0).toLocaleString()}</p>
        </div>
      </div>

      {status?.errors?.length > 0 && (
        <div className="mt-3 p-3 rounded-lg border border-red-500/20 bg-red-500/5 max-h-32 overflow-y-auto">
          {status.errors.slice(-5).reverse().map((err, i) => (
            <div key={i} className="text-[10px] text-muted-foreground py-0.5">
              <span className="text-red-400 mr-1">{new Date(err.time).toLocaleTimeString()}</span>
              {err.error}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const StatCard = ({ label, value, isError }) => (
  <div className="p-3 rounded-lg bg-secondary/30 border border-border/20">
    <p className="text-xs text-muted-foreground mb-1">{label}</p>
    <p className={`text-lg font-semibold ${isError && value > 0 ? 'text-red-400' : ''}`} data-testid={`atlas-sync-stat-${label.toLowerCase().replace(/\s+/g, '-')}`}>
      {typeof value === 'number' ? value.toLocaleString() : value}
    </p>
  </div>
);

const AdminPage = ({ user }) => {
  const [activeTab, setActiveTab] = useState('custom-fields');
  const [customFields, setCustomFields] = useState([]);
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [entityFilter, setEntityFilter] = useState('all');
  const [savingSettings, setSavingSettings] = useState(false);
  
  // Shifts state
  const [shifts, setShifts] = useState([]);
  const [teams, setTeams] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [showShiftModal, setShowShiftModal] = useState(false);
  const [selectedTeamForShifts, setSelectedTeamForShifts] = useState('all');
  const [showAssignUserModal, setShowAssignUserModal] = useState(false);
  const [selectedShiftForAssign, setSelectedShiftForAssign] = useState(null);
  
  // Form state for new field
  const [newField, setNewField] = useState({
    name: '',
    field_type: 'text',
    entity_type: 'ticket',
    options: '',
    required: false,
    description: ''
  });
  const [creatingField, setCreatingField] = useState(false);
  
  // Form state for new shift
  const [newShift, setNewShift] = useState({
    team_id: '',
    name: '',
    start_time: '09:00',
    end_time: '17:00',
    days_of_week: [1, 2, 3, 4, 5]
  });
  const [creatingShift, setCreatingShift] = useState(false);

  useEffect(() => {
    fetchCustomFields();
    fetchSettings();
    fetchShifts();
    fetchTeams();
    fetchAllUsers();
  }, []);

  const fetchCustomFields = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/custom-fields`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setCustomFields(data);
      }
    } catch (error) {
      console.error('Failed to fetch custom fields:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchShifts = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/shifts`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setShifts(data);
      }
    } catch (error) {
      console.error('Failed to fetch shifts:', error);
    }
  };
  
  const fetchTeams = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/teams`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setTeams(data);
      }
    } catch (error) {
      console.error('Failed to fetch teams:', error);
    }
  };
  
  const fetchAllUsers = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/users`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setAllUsers(Array.isArray(data) ? data : (data.items || []));
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };
  
  const handleCreateShift = async (e) => {
    e.preventDefault();
    if (!newShift.team_id || !newShift.name) return;
    
    setCreatingShift(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/shifts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(newShift)
      });
      
      if (response.ok) {
        await fetchShifts();
        setShowShiftModal(false);
        setNewShift({
          team_id: '',
          name: '',
          start_time: '09:00',
          end_time: '17:00',
          days_of_week: [1, 2, 3, 4, 5]
        });
      }
    } catch (error) {
      console.error('Failed to create shift:', error);
    } finally {
      setCreatingShift(false);
    }
  };
  
  const handleDeleteShift = async (shiftId) => {
    if (!window.confirm('Are you sure you want to delete this shift?')) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/shifts/${shiftId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        await fetchShifts();
      }
    } catch (error) {
      console.error('Failed to delete shift:', error);
    }
  };
  
  const handleAssignUserToShift = async (userId) => {
    if (!selectedShiftForAssign) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/users/${userId}/shifts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          shift_id: selectedShiftForAssign.shift_id,
          is_primary: true
        })
      });
      
      if (response.ok) {
        await fetchShifts();
        setShowAssignUserModal(false);
        setSelectedShiftForAssign(null);
      }
    } catch (error) {
      console.error('Failed to assign user to shift:', error);
    }
  };
  
  const handleRemoveUserFromShift = async (userId, shiftId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/users/${userId}/shifts/${shiftId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        await fetchShifts();
      }
    } catch (error) {
      console.error('Failed to remove user from shift:', error);
    }
  };
  
  const toggleDayOfWeek = (day) => {
    setNewShift(prev => {
      const days = prev.days_of_week.includes(day)
        ? prev.days_of_week.filter(d => d !== day)
        : [...prev.days_of_week, day].sort((a, b) => a - b);
      return { ...prev, days_of_week: days };
    });
  };
  
  const filteredShifts = selectedTeamForShifts === 'all' 
    ? shifts 
    : shifts.filter(s => s.team_id === selectedTeamForShifts);

  const fetchSettings = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/settings`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    }
  };

  const handleCreateField = async (e) => {
    e.preventDefault();
    setCreatingField(true);
    try {
      const fieldData = {
        ...newField,
        options: newField.field_type === 'select' 
          ? newField.options.split(',').map(o => o.trim()).filter(Boolean)
          : []
      };
      
      const response = await fetch(`${BACKEND_URL}/api/admin/custom-fields`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(fieldData)
      });
      
      if (response.ok) {
        setShowCreateModal(false);
        setNewField({
          name: '',
          field_type: 'text',
          entity_type: 'ticket',
          options: '',
          required: false,
          description: ''
        });
        fetchCustomFields();
      }
    } catch (error) {
      console.error('Failed to create field:', error);
    } finally {
      setCreatingField(false);
    }
  };

  const handleDeleteField = async (fieldId) => {
    if (!window.confirm('Are you sure you want to delete this field?')) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/custom-fields/${fieldId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        fetchCustomFields();
      }
    } catch (error) {
      console.error('Failed to delete field:', error);
    }
  };

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(settings)
      });
      
      if (response.ok) {
        // Settings saved
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
    } finally {
      setSavingSettings(false);
    }
  };

  const filteredFields = customFields.filter(f => 
    entityFilter === 'all' || f.entity_type === entityFilter
  );

  const getFieldTypeIcon = (type) => {
    const fieldType = FIELD_TYPES.find(t => t.value === type);
    return fieldType?.icon || Type;
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="h-14 px-6 flex items-center justify-between border-b border-border/40 shrink-0 glass">
        <div className="flex items-center gap-3">
          <Settings size={20} className="text-primary" />
          <h1 className="text-lg font-semibold">Admin</h1>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
          {/* Admin Sidebar */}
          <aside className="w-56 border-r border-border/40 p-4 shrink-0 bg-card/50">
            <nav className="space-y-1">
              <button
                onClick={() => setActiveTab('custom-fields')}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'custom-fields'
                    ? 'bg-primary/20 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                }`}
              >
                <List size={16} />
                Custom Fields
              </button>
              <button
                onClick={() => setActiveTab('routing')}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'routing'
                    ? 'bg-primary/20 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                }`}
              >
                <Zap size={16} />
                Routing Rules
              </button>
              <button
                onClick={() => setActiveTab('sla-policies')}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'sla-policies'
                    ? 'bg-primary/20 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                }`}
                data-testid="tab-sla-policies"
              >
                <Timer size={16} />
                SLA Policies
              </button>
              <button
                onClick={() => setActiveTab('sla-escalation')}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'sla-escalation'
                    ? 'bg-primary/20 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                }`}
              >
                <AlertTriangle size={16} />
                SLA Escalation
              </button>
              <button
                onClick={() => setActiveTab('shifts')}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'shifts'
                    ? 'bg-primary/20 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                }`}
              >
                <Clock size={16} />
                Shifts & Schedules
              </button>
              <button
                onClick={() => setActiveTab('general')}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'general'
                    ? 'bg-primary/20 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                }`}
              >
                <Building size={16} />
                General Settings
              </button>
              <button
                onClick={() => setActiveTab('export')}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'export'
                    ? 'bg-primary/20 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                }`}
              >
                <Download size={16} />
                Data Export
              </button>
              <button
                onClick={() => setActiveTab('atlas-sync')}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === 'atlas-sync'
                    ? 'bg-primary/20 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                }`}
                data-testid="tab-atlas-sync"
              >
                <RefreshCw size={16} />
                Atlas Sync
              </button>
            </nav>
          </aside>

          {/* Main Content */}
          <main className="flex-1 overflow-y-auto p-6">
            {activeTab === 'custom-fields' && (
              <div className="max-w-4xl">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-lg font-medium">Custom Fields</h2>
                    <p className="text-sm text-muted-foreground">
                      Create custom fields to capture additional data on tickets and users
                    </p>
                  </div>
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="h-9 px-4 flex items-center gap-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
                  >
                    <Plus size={16} />
                    New Field
                  </button>
                </div>

                {/* Filter Tabs */}
                <div className="flex items-center gap-2 mb-4">
                  {['all', 'ticket', 'user'].map(filter => (
                    <button
                      key={filter}
                      onClick={() => setEntityFilter(filter)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        entityFilter === filter
                          ? 'bg-secondary text-foreground'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {filter === 'all' ? 'All Fields' : filter === 'ticket' ? 'Ticket Fields' : 'User Fields'}
                    </button>
                  ))}
                </div>

                {/* Fields List */}
                <div className="space-y-3">
                  {filteredFields.length === 0 ? (
                    <div className="text-center py-16 card-premium border-dashed rounded-xl">
                      <div className="w-14 h-14 mx-auto mb-4 rounded-xl empty-state-icon flex items-center justify-center">
                        <List size={28} className="text-muted-foreground/50" />
                      </div>
                      <p className="font-medium text-foreground">No custom fields yet</p>
                      <p className="text-sm mt-1 text-muted-foreground">Create your first custom field to get started</p>
                      <button
                        onClick={() => setShowCreateModal(true)}
                        className="mt-5 h-10 px-5 inline-flex items-center gap-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-interactive shadow-md shadow-primary/20"
                      >
                        <Plus size={16} />
                        Create Field
                      </button>
                    </div>
                  ) : (
                    filteredFields.map(field => {
                      const Icon = getFieldTypeIcon(field.field_type);
                      return (
                        <div
                          key={field.field_id}
                          className="flex items-center justify-between p-5 rounded-xl card-premium group"
                        >
                          <div className="flex items-center gap-4">
                            <div className="w-11 h-11 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center group-hover:bg-primary/15 transition-interactive">
                              <Icon size={20} className="text-primary" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2.5">
                                <span className="font-semibold text-foreground">{field.name}</span>
                                {field.required && (
                                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-destructive/10 text-destructive font-semibold border border-destructive/20">
                                    Required
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-2 mt-1.5">
                                <span className="text-xs text-muted-foreground capitalize bg-secondary/50 px-2 py-0.5 rounded">
                                  {FIELD_TYPES.find(t => t.value === field.field_type)?.label || field.field_type}
                                </span>
                                <span className="text-muted-foreground/40">•</span>
                                <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                                  field.entity_type === 'ticket' 
                                    ? 'text-primary bg-primary/10' 
                                    : 'text-amber-500 bg-amber-500/10'
                                }`}>
                                  {field.entity_type === 'ticket' ? 'Ticket' : 'User'}
                                </span>
                                {field.options?.length > 0 && (
                                  <>
                                    <span className="text-muted-foreground/40">•</span>
                                    <span className="text-xs text-muted-foreground">
                                      {field.options.length} options
                                    </span>
                                  </>
                                )}
                              </div>
                              {field.description && (
                                <p className="text-xs text-muted-foreground mt-2">{field.description}</p>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleDeleteField(field.field_id)}
                              className="h-9 w-9 flex items-center justify-center rounded-lg btn-destructive-subtle opacity-0 group-hover:opacity-100 transition-interactive"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            )}

            {/* Routing Rules Tab */}
            {activeTab === 'routing' && (
              <RoutingRulesTab teams={teams} users={allUsers} />
            )}

            {/* SLA Policies Tab */}
            {activeTab === 'sla-policies' && (
              <SLAPoliciesTab />
            )}

            {/* SLA Escalation Tab */}
            {activeTab === 'sla-escalation' && (
              <SLAEscalationTab teams={teams} users={allUsers} />
            )}

            {/* Shifts Tab */}
            {activeTab === 'shifts' && (
              <div className="max-w-5xl">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-lg font-medium">Shifts & Schedules</h2>
                    <p className="text-sm text-muted-foreground mt-1">Manage team shifts and assign users to schedules</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <select
                      value={selectedTeamForShifts}
                      onChange={(e) => setSelectedTeamForShifts(e.target.value)}
                      className="h-9 px-3 rounded-lg bg-secondary/50 border border-border/50 text-sm"
                    >
                      <option value="all">All Teams</option>
                      {teams.map(team => (
                        <option key={team.team_id} value={team.team_id}>
                          {team.name} ({team.escalation_level || 'N/A'})
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={() => setShowShiftModal(true)}
                      className="h-9 px-4 flex items-center gap-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
                      data-testid="new-shift-button"
                    >
                      <Plus size={16} />
                      New Shift
                    </button>
                  </div>
                </div>

                {/* Shifts Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                  {filteredShifts.length === 0 ? (
                    <div className="col-span-2 text-center py-16 card-premium rounded-xl">
                      <div className="w-14 h-14 mx-auto mb-4 rounded-xl empty-state-icon flex items-center justify-center">
                        <Clock size={28} className="text-muted-foreground/50" />
                      </div>
                      <p className="text-foreground font-medium">No shifts configured</p>
                      <p className="text-sm text-muted-foreground mt-1">Create a shift to start managing schedules</p>
                    </div>
                  ) : (
                    filteredShifts.map(shift => (
                      <div key={shift.shift_id} className="card-premium rounded-xl overflow-hidden">
                        {/* Shift Header */}
                        <div className="p-5 border-b border-border/30 bg-gradient-subtle">
                          <div className="flex items-start justify-between">
                            <div>
                              <h3 className="font-semibold text-foreground">{shift.name}</h3>
                              <p className="text-sm text-muted-foreground mt-1">
                                {shift.team_name} • {shift.team_escalation_level || 'N/A'}
                              </p>
                            </div>
                            <button
                              onClick={() => handleDeleteShift(shift.shift_id)}
                              className="p-2 rounded-lg btn-destructive-subtle transition-interactive"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                          <div className="flex items-center gap-4 mt-4 text-sm">
                            <div className="flex items-center gap-2 text-muted-foreground bg-secondary/40 px-3 py-1.5 rounded-lg">
                              <Clock size={14} className="text-primary" />
                              <span>{shift.start_time} - {shift.end_time} IST</span>
                            </div>
                            <div className="flex gap-1">
                              {DAYS_OF_WEEK.map(day => (
                                <span
                                  key={day.value}
                                  className={`w-7 h-7 flex items-center justify-center text-[10px] rounded-md font-medium transition-interactive ${
                                    shift.days_of_week?.includes(day.value)
                                      ? 'bg-primary/20 text-primary border border-primary/30'
                                      : 'bg-secondary/40 text-muted-foreground/50 border border-transparent'
                                  }`}
                                >
                                  {day.label[0]}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                        
                        {/* Assigned Users */}
                        <div className="p-5">
                          <div className="flex items-center justify-between mb-3">
                            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                              Assigned Users ({shift.assigned_users_count || 0})
                            </span>
                            <button
                              onClick={() => {
                                setSelectedShiftForAssign(shift);
                                setShowAssignUserModal(true);
                              }}
                              className="text-xs text-primary hover:text-primary/80 flex items-center gap-1.5 font-medium transition-interactive"
                            >
                              <UserPlus size={12} />
                              Add User
                            </button>
                          </div>
                          
                          {shift.assigned_users?.length > 0 ? (
                            <div className="space-y-2">
                              {shift.assigned_users.map(user => (
                                <div key={user.user_id} className="flex items-center justify-between p-2.5 rounded-lg bg-secondary/30 border border-border/30 hover:border-border/50 transition-interactive">
                                  <div className="flex items-center gap-2.5">
                                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary/40 to-accent/40 flex items-center justify-center text-[11px] font-semibold text-primary">
                                      {user.name?.charAt(0).toUpperCase()}
                                    </div>
                                    <span className="text-sm font-medium">{user.name}</span>
                                  </div>
                                  <button
                                    onClick={() => handleRemoveUserFromShift(user.user_id, shift.shift_id)}
                                    className="p-1.5 rounded-md hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-interactive"
                                  >
                                    <X size={12} />
                                  </button>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-center py-6 rounded-lg border border-dashed border-border/50">
                              <p className="text-sm text-muted-foreground">No users assigned to this shift</p>
                            </div>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {activeTab === 'general' && (
              <div className="max-w-2xl">
                <h2 className="text-lg font-medium mb-6">General Settings</h2>
                
                <div className="space-y-6 bg-card p-6 rounded-xl border border-border/50">
                  <div>
                    <label className="block text-sm font-medium mb-2">Company Name</label>
                    <input
                      type="text"
                      value={settings.company_name || ''}
                      onChange={(e) => setSettings({ ...settings, company_name: e.target.value })}
                      className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                      placeholder="Your company name"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Help Email</label>
                    <input
                      type="email"
                      value={settings.support_email || ''}
                      onChange={(e) => setSettings({ ...settings, support_email: e.target.value })}
                      className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                      placeholder="help@company.com"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Default Priority</label>
                    <select
                      value={settings.default_priority || 'medium'}
                      onChange={(e) => setSettings({ ...settings, default_priority: e.target.value })}
                      className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="urgent">Urgent</option>
                    </select>
                  </div>

                  <div className="flex items-center justify-between p-4 rounded-lg bg-secondary/30 border border-border/50">
                    <div>
                      <label className="block text-sm font-medium">Auto Assignment</label>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Automatically assign new tickets using round-robin
                      </p>
                    </div>
                    <button
                      onClick={() => setSettings({ ...settings, auto_assignment: !settings.auto_assignment })}
                      className={`w-12 h-6 rounded-full transition-colors relative ${
                        settings.auto_assignment ? 'bg-primary' : 'bg-secondary border border-border'
                      }`}
                      data-testid="auto-assignment-toggle"
                    >
                      <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                        settings.auto_assignment ? 'translate-x-6' : 'translate-x-0.5'
                      }`} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-4 rounded-lg bg-secondary/30 border border-border/50">
                    <div>
                      <label className="block text-sm font-medium">Auto-Reassign Reopened Tickets</label>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        When a ticket is reopened and the original assignee is not on shift,
                        automatically reassign to an agent who is on shift (round-robin).
                        If no agents are on shift, the ticket will be unassigned.
                      </p>
                    </div>
                    <button
                      onClick={() => setSettings({ ...settings, auto_reassign_reopened: !settings.auto_reassign_reopened })}
                      className={`w-12 h-6 rounded-full transition-colors relative shrink-0 ${
                        settings.auto_reassign_reopened ? 'bg-primary' : 'bg-secondary border border-border'
                      }`}
                      data-testid="auto-reassign-reopened-toggle"
                    >
                      <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                        settings.auto_reassign_reopened ? 'translate-x-6' : 'translate-x-0.5'
                      }`} />
                    </button>
                  </div>

                  <button
                    onClick={handleSaveSettings}
                    disabled={savingSettings}
                    className="h-10 px-6 flex items-center gap-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
                  >
                    {savingSettings ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Save size={16} />
                    )}
                    Save Settings
                  </button>
                </div>
              </div>
            )}
            
            {/* Export Tab */}
            {activeTab === 'export' && (
              <ExportDataTab />
            )}
            {activeTab === 'atlas-sync' && (
              <AtlasSyncTab />
            )}
          </main>
        </div>
      
      {/* Create Field Modal */}
      {showCreateModal && (
        <>
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={() => setShowCreateModal(false)}
          />
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <div className="bg-card rounded-2xl border border-border w-full max-w-lg shadow-2xl">
              <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                <div>
                  <h3 className="font-semibold text-lg">Create Custom Field</h3>
                  <p className="text-sm text-muted-foreground">Add a new field for tickets or users</p>
                </div>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-secondary transition-colors"
                >
                  <X size={18} />
                </button>
              </div>
              
              <form onSubmit={handleCreateField} className="p-6 space-y-5">
                {/* Field Name */}
                <div>
                  <label className="block text-sm font-medium mb-2">Field Name</label>
                  <input
                    type="text"
                    value={newField.name}
                    onChange={(e) => setNewField({ ...newField, name: e.target.value })}
                    className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                    placeholder="e.g., Customer Type"
                    required
                  />
                </div>

                {/* Apply To */}
                <div>
                  <label className="block text-sm font-medium mb-2">Apply To</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setNewField({ ...newField, entity_type: 'ticket' })}
                      className={`flex-1 h-11 flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-all ${
                        newField.entity_type === 'ticket'
                          ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/25'
                          : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                      }`}
                    >
                      <Ticket size={16} />
                      Ticket
                    </button>
                    <button
                      type="button"
                      onClick={() => setNewField({ ...newField, entity_type: 'user' })}
                      className={`flex-1 h-11 flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-all ${
                        newField.entity_type === 'user'
                          ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/25'
                          : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                      }`}
                    >
                      <User size={16} />
                      User
                    </button>
                  </div>
                </div>

                {/* Field Type */}
                <div>
                  <label className="block text-sm font-medium mb-2">Field Type</label>
                  <div className="grid grid-cols-5 gap-2">
                    {FIELD_TYPES.map(type => {
                      const Icon = type.icon;
                      return (
                        <button
                          key={type.value}
                          type="button"
                          onClick={() => setNewField({ ...newField, field_type: type.value })}
                          className={`h-16 flex flex-col items-center justify-center gap-1 rounded-lg text-xs transition-all ${
                            newField.field_type === type.value
                              ? 'bg-primary/20 text-primary border-2 border-primary'
                              : 'bg-secondary text-muted-foreground hover:text-foreground border-2 border-transparent hover:border-border'
                          }`}
                        >
                          <Icon size={18} />
                          <span className="font-medium">{type.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Options for Select */}
                {newField.field_type === 'select' && (
                  <div>
                    <label className="block text-sm font-medium mb-2">Options</label>
                    <input
                      type="text"
                      value={newField.options}
                      onChange={(e) => setNewField({ ...newField, options: e.target.value })}
                      className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                      placeholder="Option 1, Option 2, Option 3"
                    />
                    <p className="text-xs text-muted-foreground mt-1.5">Separate options with commas</p>
                  </div>
                )}

                {/* Description */}
                <div>
                  <label className="block text-sm font-medium mb-2">Description (optional)</label>
                  <input
                    type="text"
                    value={newField.description}
                    onChange={(e) => setNewField({ ...newField, description: e.target.value })}
                    className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                    placeholder="What is this field for?"
                  />
                </div>

                {/* Required Checkbox */}
                <label className="flex items-center gap-3 cursor-pointer p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors">
                  <input
                    type="checkbox"
                    checked={newField.required}
                    onChange={(e) => setNewField({ ...newField, required: e.target.checked })}
                    className="w-5 h-5 rounded border-border text-primary focus:ring-primary/50"
                  />
                  <div>
                    <span className="text-sm font-medium">Required field</span>
                    <p className="text-xs text-muted-foreground">Users must fill this field</p>
                  </div>
                </label>

                {/* Actions */}
                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 h-11 rounded-lg border border-border font-medium hover:bg-secondary transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creatingField || !newField.name.trim()}
                    className="flex-1 h-11 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {creatingField ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Plus size={16} />
                    )}
                    Create Field
                  </button>
                </div>
              </form>
            </div>
          </div>
        </>
      )}

      {/* Create Shift Modal */}
      {showShiftModal && (
        <>
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={() => setShowShiftModal(false)}
          />
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <div className="bg-card rounded-2xl border border-border w-full max-w-lg shadow-2xl">
              <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                <div>
                  <h3 className="font-semibold text-lg">Create New Shift</h3>
                  <p className="text-sm text-muted-foreground">Define a shift schedule for a team</p>
                </div>
                <button
                  onClick={() => setShowShiftModal(false)}
                  className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-secondary transition-colors"
                >
                  <X size={18} />
                </button>
              </div>
              
              <form onSubmit={handleCreateShift} className="p-6 space-y-5">
                {/* Team Selection */}
                <div>
                  <label className="block text-sm font-medium mb-2">Team</label>
                  <select
                    value={newShift.team_id}
                    onChange={(e) => setNewShift({ ...newShift, team_id: e.target.value })}
                    className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                    required
                  >
                    <option value="">Select a team</option>
                    {teams.map(team => (
                      <option key={team.team_id} value={team.team_id}>
                        {team.name} ({team.escalation_level || 'N/A'})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Shift Name */}
                <div>
                  <label className="block text-sm font-medium mb-2">Shift Name</label>
                  <input
                    type="text"
                    value={newShift.name}
                    onChange={(e) => setNewShift({ ...newShift, name: e.target.value })}
                    className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                    placeholder="e.g., Morning Shift, Night Shift"
                    required
                  />
                </div>

                {/* Time Range */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Start Time (IST)</label>
                    <input
                      type="time"
                      value={newShift.start_time}
                      onChange={(e) => setNewShift({ ...newShift, start_time: e.target.value })}
                      className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">End Time (IST)</label>
                    <input
                      type="time"
                      value={newShift.end_time}
                      onChange={(e) => setNewShift({ ...newShift, end_time: e.target.value })}
                      className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                      required
                    />
                  </div>
                </div>

                {/* Days of Week */}
                <div>
                  <label className="block text-sm font-medium mb-2">Working Days</label>
                  <div className="flex gap-2">
                    {DAYS_OF_WEEK.map(day => (
                      <button
                        key={day.value}
                        type="button"
                        onClick={() => toggleDayOfWeek(day.value)}
                        className={`flex-1 h-10 rounded-lg text-sm font-medium transition-colors ${
                          newShift.days_of_week.includes(day.value)
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-secondary/50 text-muted-foreground hover:bg-secondary'
                        }`}
                      >
                        {day.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowShiftModal(false)}
                    className="flex-1 h-11 rounded-lg border border-border font-medium hover:bg-secondary transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creatingShift || !newShift.team_id || !newShift.name.trim()}
                    className="flex-1 h-11 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {creatingShift ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Plus size={16} />
                    )}
                    Create Shift
                  </button>
                </div>
              </form>
            </div>
          </div>
        </>
      )}

      {/* Assign User to Shift Modal */}
      {showAssignUserModal && selectedShiftForAssign && (
        <>
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={() => {
              setShowAssignUserModal(false);
              setSelectedShiftForAssign(null);
            }}
          />
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <div className="bg-card rounded-2xl border border-border w-full max-w-md shadow-2xl">
              <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                <div>
                  <h3 className="font-semibold text-lg">Assign User to Shift</h3>
                  <p className="text-sm text-muted-foreground">{selectedShiftForAssign.name} • {selectedShiftForAssign.team_name}</p>
                </div>
                <button
                  onClick={() => {
                    setShowAssignUserModal(false);
                    setSelectedShiftForAssign(null);
                  }}
                  className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-secondary transition-colors"
                >
                  <X size={18} />
                </button>
              </div>
              
              <div className="p-4 max-h-80 overflow-y-auto">
                {allUsers.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">No users available</p>
                ) : (
                  <div className="space-y-2">
                    {allUsers.map(user => {
                      const isAssigned = selectedShiftForAssign.assigned_users?.some(u => u.user_id === user.user_id);
                      return (
                        <button
                          key={user.user_id}
                          onClick={() => !isAssigned && handleAssignUserToShift(user.user_id)}
                          disabled={isAssigned}
                          className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors ${
                            isAssigned 
                              ? 'bg-primary/10 text-primary cursor-default' 
                              : 'hover:bg-secondary/50'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary/50 to-accent/50 flex items-center justify-center text-xs font-medium">
                              {user.name?.charAt(0).toUpperCase()}
                            </div>
                            <div className="text-left">
                              <div className="text-sm font-medium">{user.name}</div>
                              <div className="text-xs text-muted-foreground">{user.email}</div>
                            </div>
                          </div>
                          {isAssigned && (
                            <span className="text-xs bg-primary/20 px-2 py-1 rounded">Assigned</span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default AdminPage;
