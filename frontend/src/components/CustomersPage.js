import React, { useState, useEffect, useCallback } from 'react';
import { 
  Users, Search, Mail, Building2, TicketIcon, Clock, 
  TrendingUp, AlertCircle, ChevronRight, X, ExternalLink,
  Filter, ArrowUpDown, Loader2, Star, Plus, Link2, Unlink,
  DollarSign, UserPlus, Tag, Save, Trash2, Edit2, Crown,
  BadgeCheck, GitMerge
} from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const StatusBadge = ({ status }) => {
  const colors = {
    todo: 'bg-slate-500/20 text-slate-400',
    in_progress: 'bg-blue-500/20 text-blue-400',
    waiting: 'bg-amber-500/20 text-amber-400',
    review: 'bg-purple-500/20 text-purple-400',
    resolved: 'bg-emerald-500/20 text-emerald-400',
    closed: 'bg-gray-500/20 text-gray-400'
  };
  
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full ${colors[status] || colors.todo}`}>
      {status?.replace('_', ' ')}
    </span>
  );
};

const PriorityBadge = ({ priority }) => {
  const colors = {
    urgent: 'bg-red-500/20 text-red-400',
    high: 'bg-orange-500/20 text-orange-400',
    medium: 'bg-yellow-500/20 text-yellow-400',
    low: 'bg-green-500/20 text-green-400'
  };
  
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full ${colors[priority] || colors.medium}`}>
      {priority}
    </span>
  );
};

const PriorityLevelBadge = ({ level }) => {
  const config = {
    vip: { color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', icon: Crown, label: 'VIP' },
    priority: { color: 'bg-purple-500/20 text-purple-400 border-purple-500/30', icon: Star, label: 'Priority' },
    standard: { color: 'bg-slate-500/20 text-slate-400 border-slate-500/30', icon: null, label: 'Standard' }
  };
  
  const { color, icon: Icon, label } = config[level] || config.standard;
  
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${color} flex items-center gap-1`}>
      {Icon && <Icon size={10} />}
      {label}
    </span>
  );
};

const CustomerTypeBadge = ({ type }) => {
  const isB2B = type === 'b2b';
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full ${
      isB2B ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-500/20 text-gray-400'
    }`}>
      {isB2B ? 'B2B' : 'B2C'}
    </span>
  );
};

// Customer Detail Drawer
const CustomerDetailDrawer = ({ customerId, onClose, onUpdate }) => {
  const navigate = useNavigate();
  const [customer, setCustomer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState({});
  const [saving, setSaving] = useState(false);
  const [linkEmailInput, setLinkEmailInput] = useState('');
  const [linkingEmail, setLinkingEmail] = useState(false);
  const [agents, setAgents] = useState([]);
  const [showAgentSelect, setShowAgentSelect] = useState(false);
  
  const fetchCustomer = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/customers/${customerId}`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setCustomer(data);
        setEditData({
          name: data.name,
          company_name: data.company_name || '',
          priority_level: data.priority_level,
          net_payments: data.net_payments || 0,
          notes: data.notes || ''
        });
      }
    } catch (error) {
      console.error('Failed to fetch customer:', error);
    }
    setLoading(false);
  }, [customerId]);

  const fetchAgents = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/users`, { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setAgents(data.filter(u => u.role !== 'customer'));
      }
    } catch (error) {
      console.error('Failed to fetch agents:', error);
    }
  }, []);

  useEffect(() => {
    if (customerId) {
      fetchCustomer();
      fetchAgents();
    }
  }, [customerId, fetchCustomer, fetchAgents]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/customers/${customerId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(editData)
      });
      if (response.ok) {
        const updated = await response.json();
        setCustomer(prev => ({ ...prev, ...updated }));
        setEditing(false);
        onUpdate && onUpdate();
      }
    } catch (error) {
      console.error('Failed to save:', error);
    }
    setSaving(false);
  };

  const handleLinkEmail = async () => {
    if (!linkEmailInput.trim()) return;
    setLinkingEmail(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/customers/${customerId}/link-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: linkEmailInput.trim() })
      });
      if (response.ok) {
        const updated = await response.json();
        setCustomer(prev => ({ ...prev, linked_emails: updated.linked_emails }));
        setLinkEmailInput('');
        onUpdate && onUpdate();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to link email');
      }
    } catch (error) {
      console.error('Failed to link email:', error);
    }
    setLinkingEmail(false);
  };

  const handleUnlinkEmail = async (email) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/customers/${customerId}/unlink-email/${encodeURIComponent(email)}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      if (response.ok) {
        const updated = await response.json();
        setCustomer(prev => ({ ...prev, linked_emails: updated.linked_emails }));
        onUpdate && onUpdate();
      }
    } catch (error) {
      console.error('Failed to unlink email:', error);
    }
  };

  const handleAssignAgent = async (agentId) => {
    try {
      const currentAgents = customer.assigned_agents || [];
      const newAgents = currentAgents.includes(agentId) 
        ? currentAgents.filter(id => id !== agentId)
        : [...currentAgents, agentId];
      
      const response = await fetch(`${BACKEND_URL}/api/customers/${customerId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ assigned_agents: newAgents })
      });
      if (response.ok) {
        const updated = await response.json();
        setCustomer(prev => ({ ...prev, assigned_agents: updated.assigned_agents }));
        onUpdate && onUpdate();
      }
    } catch (error) {
      console.error('Failed to update agents:', error);
    }
    setShowAgentSelect(false);
  };

  const handleTicketClick = (ticketId) => {
    navigate(`/ticket/${ticketId}`);
    onClose();
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex justify-end">
        <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
        <div className="relative w-full max-w-2xl bg-background border-l border-border flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (!customer) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      
      <div className="relative w-full max-w-2xl bg-background border-l border-border shadow-2xl flex flex-col h-full animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="p-6 border-b border-border bg-secondary/20">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-gradient-to-br from-primary/40 to-accent/40 flex items-center justify-center text-xl font-semibold text-white">
                {customer.name?.charAt(0).toUpperCase() || customer.primary_email?.charAt(0).toUpperCase()}
              </div>
              <div>
                {editing ? (
                  <Input
                    value={editData.name}
                    onChange={(e) => setEditData(prev => ({ ...prev, name: e.target.value }))}
                    className="text-xl font-semibold h-8 mb-1"
                  />
                ) : (
                  <h2 className="text-xl font-semibold">{customer.name}</h2>
                )}
                <p className="text-sm text-muted-foreground">{customer.primary_email}</p>
                <div className="flex items-center gap-2 mt-1">
                  <CustomerTypeBadge type={customer.customer_type} />
                  <PriorityLevelBadge level={customer.priority_level} />
                  <span className="text-xs text-muted-foreground font-mono">{customer.customer_id}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {editing ? (
                <>
                  <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
                  <Button size="sm" onClick={handleSave} disabled={saving}>
                    {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                    Save
                  </Button>
                </>
              ) : (
                <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>
                  <Edit2 size={14} />
                </Button>
              )}
              <button onClick={onClose} className="p-2 hover:bg-secondary rounded-lg">
                <X size={18} />
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-4 gap-3">
            <div className="p-3 rounded-lg bg-secondary/30 border border-border/50">
              <div className="text-2xl font-bold">{customer.stats?.total_tickets || 0}</div>
              <div className="text-xs text-muted-foreground">Total Tickets</div>
            </div>
            <div className="p-3 rounded-lg bg-secondary/30 border border-border/50">
              <div className="text-2xl font-bold text-amber-400">{customer.stats?.open_tickets || 0}</div>
              <div className="text-xs text-muted-foreground">Open</div>
            </div>
            <div className="p-3 rounded-lg bg-secondary/30 border border-border/50">
              <div className="text-2xl font-bold text-emerald-400">
                {customer.stats?.avg_csat ? `${customer.stats.avg_csat}/5` : '-'}
              </div>
              <div className="text-xs text-muted-foreground">Avg CSAT</div>
            </div>
            <div className="p-3 rounded-lg bg-secondary/30 border border-border/50">
              <div className="text-2xl font-bold text-green-400">
                ${(customer.net_payments || 0).toLocaleString()}
              </div>
              <div className="text-xs text-muted-foreground">Net Payments</div>
            </div>
          </div>

          {/* Company & Priority */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase">Company</label>
              {editing ? (
                <Input
                  value={editData.company_name}
                  onChange={(e) => setEditData(prev => ({ ...prev, company_name: e.target.value }))}
                  placeholder="Company name..."
                />
              ) : (
                <div className="flex items-center gap-2 text-sm">
                  <Building2 size={14} className="text-muted-foreground" />
                  {customer.company_name || customer.company_domain || 'Not set'}
                </div>
              )}
            </div>
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase">Priority Level</label>
              {editing ? (
                <Select value={editData.priority_level} onValueChange={(v) => setEditData(prev => ({ ...prev, priority_level: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standard">Standard</SelectItem>
                    <SelectItem value="priority">Priority</SelectItem>
                    <SelectItem value="vip">VIP</SelectItem>
                  </SelectContent>
                </Select>
              ) : (
                <PriorityLevelBadge level={customer.priority_level} />
              )}
            </div>
          </div>

          {/* Net Payments (when editing) */}
          {editing && (
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase">Net Payments ($)</label>
              <Input
                type="number"
                value={editData.net_payments}
                onChange={(e) => setEditData(prev => ({ ...prev, net_payments: parseFloat(e.target.value) || 0 }))}
              />
            </div>
          )}

          {/* Linked Emails */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-muted-foreground uppercase">Linked Emails</label>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2 p-2 bg-primary/10 rounded-lg">
                <Mail size={14} className="text-primary" />
                <span className="text-sm">{customer.primary_email}</span>
                <Badge variant="outline" className="text-[10px]">Primary</Badge>
              </div>
              {customer.linked_emails?.map(email => (
                <div key={email} className="flex items-center justify-between p-2 bg-secondary/30 rounded-lg group">
                  <div className="flex items-center gap-2">
                    <Mail size={14} className="text-muted-foreground" />
                    <span className="text-sm">{email}</span>
                  </div>
                  <button 
                    onClick={() => handleUnlinkEmail(email)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 rounded transition-all"
                  >
                    <Unlink size={12} className="text-red-400" />
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <Input
                  placeholder="Add email..."
                  value={linkEmailInput}
                  onChange={(e) => setLinkEmailInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleLinkEmail()}
                />
                <Button size="sm" onClick={handleLinkEmail} disabled={linkingEmail}>
                  {linkingEmail ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                </Button>
              </div>
            </div>
          </div>

          {/* Assigned Agents */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-muted-foreground uppercase">Assigned Agents</label>
              <Button size="sm" variant="ghost" onClick={() => setShowAgentSelect(!showAgentSelect)}>
                <UserPlus size={14} />
              </Button>
            </div>
            {showAgentSelect && (
              <div className="p-3 bg-secondary/30 rounded-lg border border-border/50 space-y-2 max-h-40 overflow-y-auto">
                {agents.map(agent => (
                  <button
                    key={agent.user_id}
                    onClick={() => handleAssignAgent(agent.user_id)}
                    className={`w-full flex items-center gap-2 p-2 rounded hover:bg-secondary text-left text-sm ${
                      customer.assigned_agents?.includes(agent.user_id) ? 'bg-primary/20' : ''
                    }`}
                  >
                    {customer.assigned_agents?.includes(agent.user_id) && <BadgeCheck size={14} className="text-primary" />}
                    <span>{agent.name}</span>
                    <span className="text-muted-foreground text-xs">({agent.email})</span>
                  </button>
                ))}
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              {customer.assigned_agents_details?.map(agent => (
                <div key={agent.user_id} className="flex items-center gap-2 px-2 py-1 bg-secondary/50 rounded-full text-xs">
                  <div className="w-5 h-5 rounded-full bg-primary/30 flex items-center justify-center text-[10px]">
                    {agent.name?.charAt(0)}
                  </div>
                  {agent.name}
                </div>
              ))}
              {(!customer.assigned_agents_details || customer.assigned_agents_details.length === 0) && (
                <span className="text-xs text-muted-foreground">No agents assigned</span>
              )}
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground uppercase">Notes</label>
            {editing ? (
              <textarea
                value={editData.notes}
                onChange={(e) => setEditData(prev => ({ ...prev, notes: e.target.value }))}
                className="w-full h-24 p-3 bg-secondary/30 border border-border rounded-lg text-sm resize-none"
                placeholder="Add notes about this customer..."
              />
            ) : (
              <div className="p-3 bg-secondary/30 rounded-lg text-sm min-h-[60px]">
                {customer.notes || <span className="text-muted-foreground">No notes</span>}
              </div>
            )}
          </div>

          {/* Recent Tickets */}
          <div className="space-y-3">
            <label className="text-xs font-medium text-muted-foreground uppercase">Recent Tickets</label>
            <div className="space-y-2">
              {customer.recent_tickets?.map(ticket => (
                <button
                  key={ticket.ticket_id}
                  onClick={() => handleTicketClick(ticket.ticket_id)}
                  className="w-full flex items-center justify-between p-3 bg-secondary/30 rounded-lg hover:bg-secondary/50 transition-colors text-left"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-muted-foreground">{ticket.ticket_id}</span>
                      <StatusBadge status={ticket.status} />
                      <PriorityBadge priority={ticket.priority} />
                    </div>
                    <p className="text-sm truncate mt-1">{ticket.title}</p>
                  </div>
                  <ChevronRight size={16} className="text-muted-foreground" />
                </button>
              ))}
              {(!customer.recent_tickets || customer.recent_tickets.length === 0) && (
                <div className="text-center py-4 text-muted-foreground text-sm">No tickets yet</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Main Customers Page
const CustomersPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [filterPriority, setFilterPriority] = useState('all');
  const [selectedCustomerId, setSelectedCustomerId] = useState(null);
  const [total, setTotal] = useState(0);
  const [b2bProspects, setB2bProspects] = useState([]);
  const [showProspects, setShowProspects] = useState(false);

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (filterType !== 'all') params.append('customer_type', filterType);
      if (filterPriority !== 'all') params.append('priority_level', filterPriority);
      
      const response = await fetch(`${BACKEND_URL}/api/customers?${params}`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setCustomers(data.customers || []);
        setTotal(data.total || 0);
      }
    } catch (error) {
      console.error('Failed to fetch customers:', error);
    }
    setLoading(false);
  }, [search, filterType, filterPriority]);

  const fetchB2BProspects = useCallback(async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/customers/b2b-prospects?limit=10`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setB2bProspects(data);
      }
    } catch (error) {
      console.error('Failed to fetch B2B prospects:', error);
    }
  }, []);

  useEffect(() => {
    fetchCustomers();
    fetchB2BProspects();
  }, [fetchCustomers, fetchB2BProspects]);

  useEffect(() => {
    const customerId = searchParams.get('customer');
    if (customerId) {
      setSelectedCustomerId(customerId);
    }
  }, [searchParams]);

  const handleCustomerClick = (customerId) => {
    setSelectedCustomerId(customerId);
    setSearchParams({ customer: customerId });
  };

  const handleCloseDrawer = () => {
    setSelectedCustomerId(null);
    setSearchParams({});
  };

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="p-6 border-b border-border bg-secondary/10">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Users className="text-primary" />
              Customers
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              {total} customers • Manage profiles, link emails, assign agents
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant={showProspects ? "default" : "outline"} 
              size="sm"
              onClick={() => setShowProspects(!showProspects)}
            >
              <TrendingUp size={14} />
              B2B Prospects ({b2bProspects.length})
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
            <Input
              placeholder="Search by name, email, company..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="b2b">B2B</SelectItem>
              <SelectItem value="b2c">B2C</SelectItem>
            </SelectContent>
          </Select>
          <Select value={filterPriority} onValueChange={setFilterPriority}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Priority</SelectItem>
              <SelectItem value="vip">VIP</SelectItem>
              <SelectItem value="priority">Priority</SelectItem>
              <SelectItem value="standard">Standard</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* B2B Prospects Panel */}
      {showProspects && b2bProspects.length > 0 && (
        <div className="p-4 bg-blue-500/5 border-b border-blue-500/20">
          <h3 className="text-sm font-medium text-blue-400 mb-3 flex items-center gap-2">
            <TrendingUp size={14} />
            Top B2B Prospects (by engagement)
          </h3>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {b2bProspects.map(prospect => (
              <button
                key={prospect.customer_id}
                onClick={() => handleCustomerClick(prospect.customer_id)}
                className="flex-shrink-0 p-3 bg-background rounded-lg border border-border hover:border-blue-500/50 transition-colors min-w-[200px]"
              >
                <div className="font-medium text-sm">{prospect.name}</div>
                <div className="text-xs text-muted-foreground">{prospect.company_name || prospect.company_domain}</div>
                <div className="flex items-center gap-2 mt-2 text-xs">
                  <span className="text-blue-400">{prospect.ticket_count} tickets</span>
                  <span className="text-green-400">${(prospect.net_payments || 0).toLocaleString()}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Customer List */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : customers.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
            <Users size={48} className="mb-4 opacity-50" />
            <p>No customers found</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {customers.map(customer => (
              <button
                key={customer.customer_id}
                onClick={() => handleCustomerClick(customer.customer_id)}
                className="w-full flex items-center justify-between p-4 bg-secondary/20 rounded-lg border border-border/50 hover:bg-secondary/40 hover:border-border transition-all text-left"
                data-testid={`customer-${customer.customer_id}`}
              >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/30 to-accent/30 flex items-center justify-center text-sm font-medium">
                    {customer.name?.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{customer.name}</span>
                      <CustomerTypeBadge type={customer.customer_type} />
                      <PriorityLevelBadge level={customer.priority_level} />
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                      <span className="flex items-center gap-1">
                        <Mail size={10} />
                        {customer.primary_email}
                        {customer.linked_emails?.length > 0 && (
                          <span className="text-primary">+{customer.linked_emails.length}</span>
                        )}
                      </span>
                      {customer.company_name && (
                        <span className="flex items-center gap-1">
                          <Building2 size={10} />
                          {customer.company_name}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-6 text-sm">
                  <div className="text-center">
                    <div className="font-bold">{customer.stats?.total_tickets || 0}</div>
                    <div className="text-xs text-muted-foreground">Tickets</div>
                  </div>
                  <div className="text-center">
                    <div className="font-bold text-amber-400">{customer.stats?.open_tickets || 0}</div>
                    <div className="text-xs text-muted-foreground">Open</div>
                  </div>
                  <div className="text-center">
                    <div className="font-bold text-emerald-400">
                      {customer.stats?.avg_csat ? customer.stats.avg_csat.toFixed(1) : '-'}
                    </div>
                    <div className="text-xs text-muted-foreground">CSAT</div>
                  </div>
                  <div className="text-center min-w-[80px]">
                    <div className="font-bold text-green-400">${(customer.net_payments || 0).toLocaleString()}</div>
                    <div className="text-xs text-muted-foreground">Payments</div>
                  </div>
                  <ChevronRight size={18} className="text-muted-foreground" />
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Customer Detail Drawer */}
      {selectedCustomerId && (
        <CustomerDetailDrawer
          customerId={selectedCustomerId}
          onClose={handleCloseDrawer}
          onUpdate={fetchCustomers}
        />
      )}
    </div>
  );
};

export default CustomersPage;
