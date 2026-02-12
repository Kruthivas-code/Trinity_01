import React, { useState, useEffect } from 'react';
import { 
  Plus, Trash2, X, Loader2, Play, Clock, AlertTriangle, 
  Bell, ArrowUpCircle, Tag, Users
} from 'lucide-react';


const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const TRIGGER_TYPES = [
  { value: 'first_response_warning', label: 'First Response Warning', description: 'Before first response SLA breaches' },
  { value: 'first_response_breach', label: 'First Response Breach', description: 'When first response SLA is breached' },
  { value: 'resolution_warning', label: 'Resolution Warning', description: 'Before resolution SLA breaches' },
  { value: 'resolution_breach', label: 'Resolution Breach', description: 'When resolution SLA is breached' },
  { value: 'idle_ticket', label: 'Idle Ticket', description: 'When ticket has no activity for X minutes' }
];

const ACTION_TYPES = [
  { value: 'set_priority', label: 'Set Priority', icon: AlertTriangle, needsValue: 'priority' },
  { value: 'escalate_level', label: 'Escalate Level', icon: ArrowUpCircle, needsValue: 'escalation' },
  { value: 'reassign_team', label: 'Reassign to Team', icon: Users, needsValue: 'team' },
  { value: 'add_tag', label: 'Add Tag', icon: Tag, needsValue: 'text' },
  { value: 'notify_user', label: 'Notify User', icon: Bell, needsValue: 'user' }
];

const PRIORITIES = ['low', 'medium', 'high', 'urgent'];
const ESCALATION_LEVELS = ['L1', 'L2', 'L3'];

const SLAEscalationTab = ({ teams = [], users = [] }) => {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [saving, setSaving] = useState(false);
  const [runningCheck, setRunningCheck] = useState(false);
  const [checkResults, setCheckResults] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    trigger_type: 'first_response_warning',
    trigger_threshold: 80,
    priority_filter: null,
    escalation_level_filter: null,
    actions: [{ type: 'set_priority', value: 'high' }],
    priority: 0,
    is_active: true
  });

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/sla-escalation-rules`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setRules(data);
      } else {
      }
    } catch (error) {
      console.error('Failed to fetch SLA rules:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!formData.name.trim()) return;
    
    setSaving(true);
    try {
      const url = editingRule 
        ? `${BACKEND_URL}/api/admin/sla-escalation-rules/${editingRule.rule_id}`
        : `${BACKEND_URL}/api/admin/sla-escalation-rules`;
      
      const response = await fetch(url, {
        method: editingRule ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData)
      });
      
      if (response.ok) {
        await fetchRules();
        setShowCreateModal(false);
        setEditingRule(null);
        resetForm();
      } else {
        const errorData = await response.json().catch(() => ({}));
      }
    } catch (error) {
      console.error('Failed to save rule:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (ruleId) => {
    if (!window.confirm('Are you sure you want to delete this rule?')) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/sla-escalation-rules/${ruleId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        await fetchRules();
      } else {
      }
    } catch (error) {
      console.error('Failed to delete rule:', error);
    }
  };

  const handleToggleActive = async (rule) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/sla-escalation-rules/${rule.rule_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ is_active: !rule.is_active })
      });
      
      if (response.ok) {
        await fetchRules();
      } else {
      }
    } catch (error) {
      console.error('Failed to toggle rule:', error);
    }
  };

  const handleRunCheck = async () => {
    setRunningCheck(true);
    setCheckResults(null);
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/sla-escalation-rules/check`, {
        method: 'POST',
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        setCheckResults(data);
      } else {
      }
    } catch (error) {
      console.error('Failed to run SLA check:', error);
    } finally {
      setRunningCheck(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      trigger_type: 'first_response_warning',
      trigger_threshold: 80,
      priority_filter: null,
      escalation_level_filter: null,
      actions: [{ type: 'set_priority', value: 'high' }],
      priority: 0,
      is_active: true
    });
  };

  const openEditModal = (rule) => {
    setEditingRule(rule);
    setFormData({
      name: rule.name,
      description: rule.description || '',
      trigger_type: rule.trigger_type,
      trigger_threshold: rule.trigger_threshold,
      priority_filter: rule.priority_filter,
      escalation_level_filter: rule.escalation_level_filter,
      actions: rule.actions || [{ type: 'set_priority', value: 'high' }],
      priority: rule.priority || 0,
      is_active: rule.is_active
    });
    setShowCreateModal(true);
  };

  const addAction = () => {
    setFormData(prev => ({
      ...prev,
      actions: [...prev.actions, { type: 'set_priority', value: '' }]
    }));
  };

  const removeAction = (index) => {
    setFormData(prev => ({
      ...prev,
      actions: prev.actions.filter((_, i) => i !== index)
    }));
  };

  const updateAction = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      actions: prev.actions.map((a, i) => 
        i === index ? { ...a, [field]: value } : a
      )
    }));
  };

  const renderActionValueInput = (action, index) => {
    const actionType = ACTION_TYPES.find(a => a.value === action.type);
    if (!actionType) return null;

    switch (actionType.needsValue) {
      case 'priority':
        return (
          <select
            value={action.value}
            onChange={(e) => updateAction(index, 'value', e.target.value)}
            className="flex-1 h-9 px-3 rounded-lg bg-background border border-border text-sm"
          >
            <option value="">Select priority...</option>
            {PRIORITIES.map(p => (
              <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
            ))}
          </select>
        );
      case 'escalation':
        return (
          <select
            value={action.value}
            onChange={(e) => updateAction(index, 'value', e.target.value)}
            className="flex-1 h-9 px-3 rounded-lg bg-background border border-border text-sm"
          >
            <option value="">Select level...</option>
            {ESCALATION_LEVELS.map(l => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        );
      case 'team':
        return (
          <select
            value={action.value}
            onChange={(e) => updateAction(index, 'value', e.target.value)}
            className="flex-1 h-9 px-3 rounded-lg bg-background border border-border text-sm"
          >
            <option value="">Select team...</option>
            {Array.isArray(teams) && teams.map(team => (
              <option key={team.team_id} value={team.team_id}>
                {team.name}
              </option>
            ))}
          </select>
        );
      case 'user':
        return (
          <select
            value={action.value}
            onChange={(e) => updateAction(index, 'value', e.target.value)}
            className="flex-1 h-9 px-3 rounded-lg bg-background border border-border text-sm"
          >
            <option value="">Select user...</option>
            {Array.isArray(users) && users.map(user => (
              <option key={user.user_id} value={user.user_id}>
                {user.name}
              </option>
            ))}
          </select>
        );
      default:
        return (
          <input
            type="text"
            value={action.value}
            onChange={(e) => updateAction(index, 'value', e.target.value)}
            className="flex-1 h-9 px-3 rounded-lg bg-background border border-border text-sm"
            placeholder="Enter value..."
          />
        );
    }
  };

  const getTriggerLabel = (type) => {
    const trigger = TRIGGER_TYPES.find(t => t.value === type);
    return trigger ? trigger.label : type;
  };

  const getThresholdLabel = (type, threshold) => {
    if (type === 'idle_ticket') {
      return `${threshold} minutes idle`;
    }
    return `${threshold}% of SLA`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 size={24} className="animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-medium">SLA Escalation Rules</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Automatically escalate tickets based on SLA status
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRunCheck}
            disabled={runningCheck}
            className="h-9 px-4 flex items-center gap-2 rounded-lg border border-border text-sm font-medium hover:bg-secondary transition-colors disabled:opacity-50"
          >
            {runningCheck ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Clock size={16} />
            )}
            Run Check Now
          </button>
          <button
            onClick={() => {
              resetForm();
              setEditingRule(null);
              setShowCreateModal(true);
            }}
            className="h-9 px-4 flex items-center gap-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
            data-testid="new-sla-rule-button"
          >
            <Plus size={16} />
            New Rule
          </button>
        </div>
      </div>

      {/* Check Results */}
      {checkResults && (
        <div className="mb-6 p-4 rounded-xl bg-secondary/30 border border-border/50">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium">SLA Check Results</h3>
            <button 
              onClick={() => setCheckResults(null)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X size={16} />
            </button>
          </div>
          <div className="text-sm text-muted-foreground">
            <p>Checked: {checkResults.checked} tickets</p>
            <p>Escalated: {checkResults.escalated} tickets</p>
          </div>
          {checkResults.details && checkResults.details.length > 0 && (
            <div className="mt-3 space-y-2">
              {checkResults.details.map((detail, idx) => (
                <div key={idx} className="text-xs p-2 rounded bg-background">
                  <span className="font-mono">{detail.ticket_id}</span>
                  <span className="text-muted-foreground"> - {detail.rule_name}</span>
                  <span className="text-primary"> ({detail.actions_applied.join(', ')})</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Rules List */}
      {rules.length === 0 ? (
        <div className="text-center py-12 bg-card rounded-xl border border-border/50">
          <Clock size={40} className="mx-auto text-muted-foreground/30 mb-3" />
          <p className="text-muted-foreground">No SLA escalation rules configured</p>
          <p className="text-sm text-muted-foreground/70 mt-1">
            Create rules to automatically escalate tickets when SLAs are at risk
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {rules.map((rule, idx) => (
            <div
              key={rule.rule_id}
              className={`bg-card rounded-xl border p-4 ${
                rule.is_active ? 'border-border/50' : 'border-border/30 opacity-60'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-muted-foreground/50 font-mono">
                      #{idx + 1}
                    </span>
                    <h3 className="font-medium">{rule.name}</h3>
                    {!rule.is_active && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                        Disabled
                      </span>
                    )}
                  </div>
                  {rule.description && (
                    <p className="text-sm text-muted-foreground mb-3">{rule.description}</p>
                  )}
                  
                  {/* Trigger */}
                  <div className="flex flex-wrap items-center gap-2 text-xs mb-2">
                    <span className="text-muted-foreground">Trigger:</span>
                    <span className="px-2 py-1 rounded bg-amber-500/20 text-amber-400">
                      {getTriggerLabel(rule.trigger_type)}
                    </span>
                    <span className="px-2 py-1 rounded bg-secondary/50 text-foreground/80">
                      {getThresholdLabel(rule.trigger_type, rule.trigger_threshold)}
                    </span>
                  </div>
                  
                  {/* Filters */}
                  {(rule.priority_filter || rule.escalation_level_filter) && (
                    <div className="flex flex-wrap items-center gap-2 text-xs mb-2">
                      <span className="text-muted-foreground">Applies to:</span>
                      {rule.priority_filter && (
                        <span className="px-2 py-1 rounded bg-secondary/50 text-foreground/80">
                          Priorities: {rule.priority_filter.join(', ')}
                        </span>
                      )}
                      {rule.escalation_level_filter && (
                        <span className="px-2 py-1 rounded bg-secondary/50 text-foreground/80">
                          Levels: {rule.escalation_level_filter.join(', ')}
                        </span>
                      )}
                    </div>
                  )}
                  
                  {/* Actions */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="text-muted-foreground">Actions:</span>
                    {rule.actions?.map((a, i) => (
                      <span key={i} className="px-2 py-1 rounded bg-primary/20 text-primary">
                        {ACTION_TYPES.find(at => at.value === a.type)?.label || a.type}: {a.value}
                      </span>
                    ))}
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggleActive(rule)}
                    className={`p-2 rounded-lg transition-colors ${
                      rule.is_active 
                        ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30' 
                        : 'bg-secondary/50 text-muted-foreground hover:bg-secondary'
                    }`}
                    title={rule.is_active ? 'Disable rule' : 'Enable rule'}
                  >
                    <Play size={14} />
                  </button>
                  <button
                    onClick={() => openEditModal(rule)}
                    className="p-2 rounded-lg bg-secondary/50 hover:bg-secondary transition-colors"
                  >
                    <Clock size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete(rule.rule_id)}
                    className="p-2 rounded-lg hover:bg-destructive/10 text-destructive transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showCreateModal && (
        <>
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={() => setShowCreateModal(false)}
          />
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 overflow-y-auto">
            <div className="bg-card rounded-2xl border border-border w-full max-w-2xl shadow-2xl my-8">
              <div className="flex items-center justify-between px-6 py-4 border-b border-border">
                <div>
                  <h3 className="font-semibold text-lg">
                    {editingRule ? 'Edit SLA Escalation Rule' : 'Create SLA Escalation Rule'}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Define when and how to escalate tickets based on SLA status
                  </p>
                </div>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-secondary transition-colors"
                >
                  <X size={18} />
                </button>
              </div>
              
              <div className="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
                {/* Basic Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Rule Name</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground"
                      placeholder="e.g., Escalate urgent before breach"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Priority (higher runs first)</label>
                    <input
                      type="number"
                      value={formData.priority}
                      onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
                      className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-2">Description</label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground"
                    placeholder="Optional description"
                  />
                </div>

                {/* Trigger Type */}
                <div>
                  <label className="block text-sm font-medium mb-3">Trigger Type</label>
                  <div className="grid grid-cols-1 gap-2">
                    {TRIGGER_TYPES.map(trigger => (
                      <button
                        key={trigger.value}
                        onClick={() => setFormData({ ...formData, trigger_type: trigger.value })}
                        className={`p-3 rounded-lg border text-left transition-colors ${
                          formData.trigger_type === trigger.value
                            ? 'border-primary bg-primary/10'
                            : 'border-border hover:border-primary/50'
                        }`}
                      >
                        <div className="font-medium text-sm">{trigger.label}</div>
                        <div className="text-xs text-muted-foreground">{trigger.description}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Threshold */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    {formData.trigger_type === 'idle_ticket' ? 'Idle Time (minutes)' : 'SLA Threshold (%)'}
                  </label>
                  <input
                    type="number"
                    value={formData.trigger_threshold}
                    onChange={(e) => setFormData({ ...formData, trigger_threshold: parseInt(e.target.value) || 0 })}
                    className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground"
                    placeholder={formData.trigger_type === 'idle_ticket' ? 'e.g., 60' : 'e.g., 80'}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {formData.trigger_type === 'idle_ticket' 
                      ? 'Trigger when ticket has no activity for this many minutes'
                      : 'Trigger when this percentage of SLA time has elapsed'}
                  </p>
                </div>

                {/* Filters */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Priority Filter (optional)</label>
                    <div className="space-y-1">
                      {PRIORITIES.map(p => (
                        <label key={p} className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={formData.priority_filter?.includes(p) || false}
                            onChange={(e) => {
                              const current = formData.priority_filter || [];
                              if (e.target.checked) {
                                setFormData({ ...formData, priority_filter: [...current, p] });
                              } else {
                                const filtered = current.filter(x => x !== p);
                                setFormData({ ...formData, priority_filter: filtered.length > 0 ? filtered : null });
                              }
                            }}
                            className="rounded"
                          />
                          {p.charAt(0).toUpperCase() + p.slice(1)}
                        </label>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">Leave empty to apply to all</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Escalation Level Filter (optional)</label>
                    <div className="space-y-1">
                      {ESCALATION_LEVELS.map(l => (
                        <label key={l} className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={formData.escalation_level_filter?.includes(l) || false}
                            onChange={(e) => {
                              const current = formData.escalation_level_filter || [];
                              if (e.target.checked) {
                                setFormData({ ...formData, escalation_level_filter: [...current, l] });
                              } else {
                                const filtered = current.filter(x => x !== l);
                                setFormData({ ...formData, escalation_level_filter: filtered.length > 0 ? filtered : null });
                              }
                            }}
                            className="rounded"
                          />
                          {l}
                        </label>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">Leave empty to apply to all</p>
                  </div>
                </div>

                {/* Actions */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <label className="text-sm font-medium">Actions</label>
                    <button
                      onClick={addAction}
                      className="text-xs text-primary hover:underline flex items-center gap-1"
                    >
                      <Plus size={12} /> Add action
                    </button>
                  </div>
                  <div className="space-y-2">
                    {formData.actions.map((action, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <select
                          value={action.type}
                          onChange={(e) => updateAction(idx, 'type', e.target.value)}
                          className="h-9 px-3 rounded-lg bg-background border border-border text-sm"
                        >
                          {ACTION_TYPES.map(a => (
                            <option key={a.value} value={a.value}>{a.label}</option>
                          ))}
                        </select>
                        {renderActionValueInput(action, idx)}
                        {formData.actions.length > 1 && (
                          <button
                            onClick={() => removeAction(idx)}
                            className="p-2 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                          >
                            <X size={14} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              
              <div className="flex gap-3 px-6 py-4 border-t border-border">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 h-11 rounded-lg border border-border font-medium hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving || !formData.name.trim()}
                  className="flex-1 h-11 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {saving ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Clock size={16} />
                  )}
                  {editingRule ? 'Update Rule' : 'Create Rule'}
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default SLAEscalationTab;
