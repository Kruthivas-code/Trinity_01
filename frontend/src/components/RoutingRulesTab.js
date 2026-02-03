import React, { useState, useEffect } from 'react';
import { 
  Plus, Trash2, X, ChevronDown, ChevronRight, 
  Loader2, Play, Zap, ArrowRight, Tag, AlertCircle, Users
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const CONDITION_FIELDS = [
  { value: 'priority', label: 'Priority', type: 'select', options: ['low', 'medium', 'high', 'urgent'] },
  { value: 'escalation_level', label: 'Escalation Level', type: 'select', options: ['L1', 'L2', 'L3'] },
  { value: 'tags', label: 'Tags', type: 'text' },
  { value: 'customer_email', label: 'Customer Email', type: 'text' },
  { value: 'domain', label: 'Email Domain', type: 'text' },
  { value: 'source', label: 'Source', type: 'select', options: ['manual', 'email', 'api'] },
  { value: 'status', label: 'Status', type: 'select', options: ['todo', 'in_progress', 'waiting', 'review', 'resolved'] },
  { value: 'customer_ltv', label: 'Customer Lifetime Value', type: 'number' }
];

const CONDITION_OPERATORS = [
  { value: 'equals', label: 'equals' },
  { value: 'not_equals', label: 'does not equal' },
  { value: 'contains', label: 'contains' },
  { value: 'not_contains', label: 'does not contain' },
  { value: 'starts_with', label: 'starts with' },
  { value: 'ends_with', label: 'ends with' },
  { value: 'tag_includes', label: 'has tag' },
  { value: 'tag_excludes', label: 'does not have tag' },
  { value: 'exists', label: 'exists' },
  { value: 'not_exists', label: 'does not exist' },
  { value: 'greater_than', label: 'greater than' },
  { value: 'less_than', label: 'less than' },
  { value: 'greater_or_equal', label: 'greater or equal' },
  { value: 'less_or_equal', label: 'less or equal' }
];

const ASSIGNMENT_METHODS = [
  { value: 'round_robin', label: 'Round Robin', description: 'Assign in rotation order' },
  { value: 'least_tickets', label: 'Least Tickets', description: 'Assign to agent with fewest open tickets' }
];

const ACTION_TYPES = [
  { value: 'assign_team', label: 'Assign to Team', needsValue: 'team' },
  { value: 'assign_user', label: 'Assign to User', needsValue: 'user' },
  { value: 'set_priority', label: 'Set Priority', needsValue: 'priority' },
  { value: 'set_escalation', label: 'Set Escalation Level', needsValue: 'escalation' },
  { value: 'add_tag', label: 'Add Tag', needsValue: 'text' },
  { value: 'set_status', label: 'Set Status', needsValue: 'status' }
];

const RoutingRulesTab = ({ teams, users }) => {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [saving, setSaving] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    priority: 0,
    is_active: true,
    condition_groups: [[{ field: 'priority', operator: 'equals', value: '' }]], // Array of groups (OR between groups, AND within group)
    actions: [{ type: 'assign_team', value: '' }],
    assignment_method: 'round_robin' // round_robin or least_tickets
  });

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/routing-rules`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setRules(data);
      }
    } catch (error) {
      console.error('Failed to fetch rules:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!formData.name.trim()) return;
    
    setSaving(true);
    try {
      const url = editingRule 
        ? `${BACKEND_URL}/api/admin/routing-rules/${editingRule.rule_id}`
        : `${BACKEND_URL}/api/admin/routing-rules`;
      
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
      const response = await fetch(`${BACKEND_URL}/api/admin/routing-rules/${ruleId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        await fetchRules();
      }
    } catch (error) {
      console.error('Failed to delete rule:', error);
    }
  };

  const handleToggleActive = async (rule) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/routing-rules/${rule.rule_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ is_active: !rule.is_active })
      });
      
      if (response.ok) {
        await fetchRules();
      }
    } catch (error) {
      console.error('Failed to toggle rule:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      priority: 0,
      is_active: true,
      condition_groups: [[{ field: 'priority', operator: 'equals', value: '' }]],
      actions: [{ type: 'assign_team', value: '' }],
      assignment_method: 'round_robin'
    });
  };

  const openEditModal = (rule) => {
    setEditingRule(rule);
    // Handle both old format (conditions) and new format (condition_groups)
    let conditionGroups = rule.condition_groups;
    if (!conditionGroups && rule.conditions) {
      // Migrate old format: single group with all conditions
      conditionGroups = [rule.conditions];
    }
    if (!conditionGroups || conditionGroups.length === 0) {
      conditionGroups = [[{ field: 'priority', operator: 'equals', value: '' }]];
    }
    
    setFormData({
      name: rule.name,
      description: rule.description || '',
      priority: rule.priority || 0,
      is_active: rule.is_active,
      condition_groups: conditionGroups,
      actions: rule.actions || [{ type: 'assign_team', value: '' }],
      assignment_method: rule.assignment_method || 'round_robin'
    });
    setShowCreateModal(true);
  };

  // Condition group management (OR between groups, AND within group)
  const addConditionGroup = () => {
    setFormData(prev => ({
      ...prev,
      condition_groups: [...prev.condition_groups, [{ field: 'priority', operator: 'equals', value: '' }]]
    }));
  };

  const removeConditionGroup = (groupIndex) => {
    setFormData(prev => ({
      ...prev,
      condition_groups: prev.condition_groups.filter((_, i) => i !== groupIndex)
    }));
  };

  const addConditionToGroup = (groupIndex) => {
    setFormData(prev => ({
      ...prev,
      condition_groups: prev.condition_groups.map((group, i) => 
        i === groupIndex ? [...group, { field: 'priority', operator: 'equals', value: '' }] : group
      )
    }));
  };

  const removeConditionFromGroup = (groupIndex, conditionIndex) => {
    setFormData(prev => ({
      ...prev,
      condition_groups: prev.condition_groups.map((group, i) => 
        i === groupIndex ? group.filter((_, ci) => ci !== conditionIndex) : group
      ).filter(group => group.length > 0) // Remove empty groups
    }));
  };

  const updateConditionInGroup = (groupIndex, conditionIndex, field, value) => {
    setFormData(prev => ({
      ...prev,
      condition_groups: prev.condition_groups.map((group, gi) => 
        gi === groupIndex 
          ? group.map((c, ci) => ci === conditionIndex ? { ...c, [field]: value } : c)
          : group
      )
    }));
  };

  const addAction = () => {
    setFormData(prev => ({
      ...prev,
      actions: [...prev.actions, { type: 'assign_team', value: '' }]
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
      case 'team':
        return (
          <select
            value={action.value}
            onChange={(e) => updateAction(index, 'value', e.target.value)}
            className="flex-1 h-9 px-3 rounded-lg bg-background border border-border text-sm"
          >
            <option value="">Select team...</option>
            {teams.map(team => (
              <option key={team.team_id} value={team.team_id}>
                {team.name} ({team.escalation_level || 'N/A'})
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
      case 'priority':
        return (
          <select
            value={action.value}
            onChange={(e) => updateAction(index, 'value', e.target.value)}
            className="flex-1 h-9 px-3 rounded-lg bg-background border border-border text-sm"
          >
            <option value="">Select priority...</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
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
            <option value="L1">L1</option>
            <option value="L2">L2</option>
            <option value="L3">L3</option>
          </select>
        );
      case 'status':
        return (
          <select
            value={action.value}
            onChange={(e) => updateAction(index, 'value', e.target.value)}
            className="flex-1 h-9 px-3 rounded-lg bg-background border border-border text-sm"
          >
            <option value="">Select status...</option>
            <option value="todo">To Do</option>
            <option value="in_progress">In Progress</option>
            <option value="waiting">Waiting</option>
            <option value="review">Review</option>
            <option value="resolved">Resolved</option>
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
          <h2 className="text-lg font-medium">Routing Rules</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Define rules to automatically route and assign tickets
          </p>
        </div>
        <button
          onClick={() => {
            resetForm();
            setEditingRule(null);
            setShowCreateModal(true);
          }}
          className="h-9 px-4 flex items-center gap-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
          data-testid="new-rule-button"
        >
          <Plus size={16} />
          New Rule
        </button>
      </div>

      {/* Rules List */}
      {rules.length === 0 ? (
        <div className="text-center py-12 bg-card rounded-xl border border-border/50">
          <Zap size={40} className="mx-auto text-muted-foreground/30 mb-3" />
          <p className="text-muted-foreground">No routing rules configured</p>
          <p className="text-sm text-muted-foreground/70 mt-1">
            Create rules to automatically route tickets based on conditions
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
                  
                  {/* Conditions */}
                  <div className="flex flex-wrap items-center gap-2 text-xs mb-2">
                    <span className="text-muted-foreground">When:</span>
                    {(rule.condition_groups || (rule.conditions ? [rule.conditions] : [])).map((group, gi) => (
                      <React.Fragment key={gi}>
                        {gi > 0 && <span className="text-amber-400 font-medium">OR</span>}
                        <span className="flex items-center gap-1">
                          {group.map((c, ci) => (
                            <React.Fragment key={ci}>
                              {ci > 0 && <span className="text-muted-foreground">+</span>}
                              <span className="px-2 py-1 rounded bg-secondary/50 text-foreground/80">
                                {c.field} {c.operator} "{c.value}"
                              </span>
                            </React.Fragment>
                          ))}
                        </span>
                      </React.Fragment>
                    ))}
                  </div>
                  
                  {/* Actions */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="text-muted-foreground">Then:</span>
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
                    <ChevronRight size={14} />
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
                    {editingRule ? 'Edit Routing Rule' : 'Create Routing Rule'}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Define conditions and actions for automatic ticket routing
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
                      placeholder="e.g., Route urgent to L2"
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

                {/* Condition Groups (OR between groups, AND within group) */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <label className="text-sm font-medium">Conditions</label>
                      <p className="text-xs text-muted-foreground">AND within groups, OR between groups</p>
                    </div>
                    <button
                      onClick={addConditionGroup}
                      className="text-xs text-primary hover:underline flex items-center gap-1"
                    >
                      <Plus size={12} /> Add OR group
                    </button>
                  </div>
                  <div className="space-y-4">
                    {formData.condition_groups.map((group, groupIdx) => (
                      <div key={groupIdx} className="relative">
                        {groupIdx > 0 && (
                          <div className="flex items-center justify-center -mt-2 mb-2">
                            <span className="px-3 py-1 text-xs font-medium bg-amber-500/20 text-amber-400 rounded-full">
                              OR
                            </span>
                          </div>
                        )}
                        <div className="p-3 rounded-lg border border-border/50 bg-secondary/20 space-y-2">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs text-muted-foreground font-medium">
                              Group {groupIdx + 1} {group.length > 1 && '(all must match)'}
                            </span>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => addConditionToGroup(groupIdx)}
                                className="text-xs text-primary hover:underline flex items-center gap-1"
                              >
                                <Plus size={10} /> AND
                              </button>
                              {formData.condition_groups.length > 1 && (
                                <button
                                  onClick={() => removeConditionGroup(groupIdx)}
                                  className="text-xs text-destructive hover:underline"
                                >
                                  Remove group
                                </button>
                              )}
                            </div>
                          </div>
                          {group.map((condition, condIdx) => (
                            <div key={condIdx} className="flex items-center gap-2">
                              {condIdx > 0 && (
                                <span className="text-xs text-muted-foreground w-8">AND</span>
                              )}
                              <select
                                value={condition.field}
                                onChange={(e) => updateConditionInGroup(groupIdx, condIdx, 'field', e.target.value)}
                                className="h-9 px-3 rounded-lg bg-background border border-border text-sm"
                              >
                                {CONDITION_FIELDS.map(f => (
                                  <option key={f.value} value={f.value}>{f.label}</option>
                                ))}
                              </select>
                              <select
                                value={condition.operator}
                                onChange={(e) => updateConditionInGroup(groupIdx, condIdx, 'operator', e.target.value)}
                                className="h-9 px-3 rounded-lg bg-background border border-border text-sm"
                              >
                                {CONDITION_OPERATORS.map(o => (
                                  <option key={o.value} value={o.value}>{o.label}</option>
                                ))}
                              </select>
                              <input
                                type={CONDITION_FIELDS.find(f => f.value === condition.field)?.type === 'number' ? 'number' : 'text'}
                                value={condition.value}
                                onChange={(e) => updateConditionInGroup(groupIdx, condIdx, 'value', e.target.value)}
                                className="flex-1 h-9 px-3 rounded-lg bg-background border border-border text-sm"
                                placeholder="Value..."
                              />
                              {group.length > 1 && (
                                <button
                                  onClick={() => removeConditionFromGroup(groupIdx, condIdx)}
                                  className="p-2 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                                >
                                  <X size={14} />
                                </button>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Assignment Method */}
                <div>
                  <label className="block text-sm font-medium mb-2">Assignment Method</label>
                  <div className="grid grid-cols-2 gap-3">
                    {ASSIGNMENT_METHODS.map(method => (
                      <button
                        key={method.value}
                        onClick={() => setFormData({ ...formData, assignment_method: method.value })}
                        className={`p-3 rounded-lg border text-left transition-colors ${
                          formData.assignment_method === method.value
                            ? 'border-primary bg-primary/10'
                            : 'border-border hover:border-primary/50'
                        }`}
                      >
                        <div className="font-medium text-sm">{method.label}</div>
                        <div className="text-xs text-muted-foreground">{method.description}</div>
                      </button>
                    ))}
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
                    <Zap size={16} />
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

export default RoutingRulesTab;
