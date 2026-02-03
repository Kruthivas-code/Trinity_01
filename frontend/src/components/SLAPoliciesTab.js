import React, { useState, useEffect } from 'react';
import { 
  Clock, Save, Loader2, AlertCircle, CheckCircle2, 
  Timer, Zap, AlertTriangle, Flame, Calendar,
  Sun, RefreshCw, Info
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const PRIORITIES = [
  { 
    value: 'low', 
    label: 'Low', 
    icon: Clock, 
    color: 'text-slate-400',
    bgColor: 'bg-slate-400/10',
    borderColor: 'border-slate-400/30',
    description: 'Non-urgent issues, general questions'
  },
  { 
    value: 'medium', 
    label: 'Medium', 
    icon: Timer, 
    color: 'text-blue-400',
    bgColor: 'bg-blue-400/10',
    borderColor: 'border-blue-400/30',
    description: 'Standard support requests'
  },
  { 
    value: 'high', 
    label: 'High', 
    icon: AlertTriangle, 
    color: 'text-amber-400',
    bgColor: 'bg-amber-400/10',
    borderColor: 'border-amber-400/30',
    description: 'Important issues affecting work'
  },
  { 
    value: 'urgent', 
    label: 'Urgent', 
    icon: Flame, 
    color: 'text-red-400',
    bgColor: 'bg-red-400/10',
    borderColor: 'border-red-400/30',
    description: 'Critical issues, system down'
  }
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

// Helper to format minutes to human readable
const formatDuration = (minutes) => {
  if (minutes < 60) return `${minutes}m`;
  if (minutes < 1440) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  }
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  return hours > 0 ? `${days}d ${hours}h` : `${days}d`;
};

// Helper to parse duration input
const parseDuration = (value, unit) => {
  const num = parseInt(value) || 0;
  switch (unit) {
    case 'minutes': return num;
    case 'hours': return num * 60;
    case 'days': return num * 1440;
    default: return num;
  }
};

// Duration input component
const DurationInput = ({ value, onChange, label, min = 1 }) => {
  const [inputValue, setInputValue] = useState('');
  const [unit, setUnit] = useState('hours');

  useEffect(() => {
    // Convert minutes to best unit for display
    if (value >= 1440 && value % 1440 === 0) {
      setInputValue(String(value / 1440));
      setUnit('days');
    } else if (value >= 60) {
      setInputValue(String(Math.floor(value / 60)));
      setUnit('hours');
    } else {
      setInputValue(String(value));
      setUnit('minutes');
    }
  }, [value]);

  const handleChange = (newValue, newUnit) => {
    const minutes = parseDuration(newValue, newUnit);
    if (minutes >= min) {
      onChange(minutes);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <input
        type="number"
        value={inputValue}
        onChange={(e) => {
          setInputValue(e.target.value);
          handleChange(e.target.value, unit);
        }}
        min={1}
        className="w-20 h-9 px-2 rounded-lg bg-secondary/50 border border-border text-sm text-center focus:outline-none focus:ring-2 focus:ring-primary/50"
      />
      <select
        value={unit}
        onChange={(e) => {
          setUnit(e.target.value);
          handleChange(inputValue, e.target.value);
        }}
        className="h-9 px-2 rounded-lg bg-secondary/50 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
      >
        <option value="minutes">minutes</option>
        <option value="hours">hours</option>
        <option value="days">days</option>
      </select>
    </div>
  );
};

const SLAPoliciesTab = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  
  const [policies, setPolicies] = useState({
    default_first_response_hours: 4,
    default_resolution_hours: 24,
    priority_slas: {
      low: { first_response_minutes: 480, resolution_minutes: 2880 },
      medium: { first_response_minutes: 240, resolution_minutes: 1440 },
      high: { first_response_minutes: 60, resolution_minutes: 480 },
      urgent: { first_response_minutes: 15, resolution_minutes: 120 }
    },
    business_hours_only: false,
    business_hours: {
      start: '09:00',
      end: '18:00',
      days: [1, 2, 3, 4, 5]
    },
    holidays: []
  });

  const [newHoliday, setNewHoliday] = useState('');

  useEffect(() => {
    fetchPolicies();
  }, []);

  const fetchPolicies = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BACKEND_URL}/api/admin/sla-policies`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setPolicies(data);
      }
    } catch (error) {
      console.error('Failed to fetch SLA policies:', error);
      toast.error('Failed to load SLA policies');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/admin/sla-policies`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(policies)
      });

      if (response.ok) {
        toast.success('SLA policies saved successfully');
        setHasChanges(false);
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to save SLA policies');
      }
    } catch (error) {
      console.error('Failed to save SLA policies:', error);
      toast.error('Failed to save SLA policies');
    } finally {
      setSaving(false);
    }
  };

  const updatePriorityPolicy = (priority, field, value) => {
    setPolicies(prev => ({
      ...prev,
      priority_slas: {
        ...prev.priority_slas,
        [priority]: {
          ...prev.priority_slas[priority],
          [field]: value
        }
      }
    }));
    setHasChanges(true);
  };

  const toggleBusinessDay = (day) => {
    setPolicies(prev => {
      const currentDays = prev.business_hours?.days || [];
      const newDays = currentDays.includes(day)
        ? currentDays.filter(d => d !== day)
        : [...currentDays, day].sort((a, b) => a - b);
      
      return {
        ...prev,
        business_hours: {
          ...prev.business_hours,
          days: newDays
        }
      };
    });
    setHasChanges(true);
  };

  const addHoliday = () => {
    if (newHoliday && !policies.holidays.includes(newHoliday)) {
      setPolicies(prev => ({
        ...prev,
        holidays: [...prev.holidays, newHoliday].sort()
      }));
      setNewHoliday('');
      setHasChanges(true);
    }
  };

  const removeHoliday = (date) => {
    setPolicies(prev => ({
      ...prev,
      holidays: prev.holidays.filter(h => h !== date)
    }));
    setHasChanges(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex items-center gap-3 text-muted-foreground">
          <Loader2 size={20} className="animate-spin" />
          <span>Loading SLA policies...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8" data-testid="sla-policies-tab">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium flex items-center gap-2">
            <Clock size={20} className="text-primary" />
            SLA Policies
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Define response and resolution time targets for each priority level
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchPolicies}
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg hover:bg-secondary transition-colors"
            title="Refresh"
          >
            <RefreshCw size={16} />
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="save-sla-policies"
          >
            {saving ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save size={16} />
                Save Changes
              </>
            )}
          </button>
        </div>
      </div>

      {/* Info Banner */}
      <div className="p-4 rounded-xl bg-primary/5 border border-primary/20">
        <div className="flex items-start gap-3">
          <Info size={18} className="text-primary shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium text-primary">How SLAs Work</p>
            <p className="text-muted-foreground mt-1">
              <strong>First Response Time:</strong> Maximum time before first agent reply. 
              <strong className="ml-2">Resolution Time:</strong> Maximum time to resolve and close the ticket.
              SLA breaches trigger escalation rules you define in the "SLA Escalation" tab.
            </p>
          </div>
        </div>
      </div>

      {/* Priority-based SLAs */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
          SLA Targets by Priority
        </h3>
        
        <div className="grid gap-4">
          {PRIORITIES.map((priority) => {
            const Icon = priority.icon;
            const sla = policies.priority_slas?.[priority.value] || {};
            
            return (
              <div
                key={priority.value}
                className={`p-4 rounded-xl border ${priority.borderColor} ${priority.bgColor}`}
                data-testid={`sla-priority-${priority.value}`}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className={`w-10 h-10 rounded-lg ${priority.bgColor} flex items-center justify-center`}>
                    <Icon size={20} className={priority.color} />
                  </div>
                  <div>
                    <h4 className={`font-medium ${priority.color}`}>{priority.label} Priority</h4>
                    <p className="text-xs text-muted-foreground">{priority.description}</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-2">
                      First Response Time
                    </label>
                    <DurationInput
                      value={sla.first_response_minutes || 60}
                      onChange={(value) => updatePriorityPolicy(priority.value, 'first_response_minutes', value)}
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Current: {formatDuration(sla.first_response_minutes || 60)}
                    </p>
                  </div>
                  
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-2">
                      Resolution Time
                    </label>
                    <DurationInput
                      value={sla.resolution_minutes || 480}
                      onChange={(value) => updatePriorityPolicy(priority.value, 'resolution_minutes', value)}
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Current: {formatDuration(sla.resolution_minutes || 480)}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Business Hours */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
          <Sun size={14} />
          Business Hours
        </h3>
        
        <div className="p-4 rounded-xl bg-secondary/20 border border-border/30">
          <label className="flex items-center gap-3 cursor-pointer mb-4">
            <input
              type="checkbox"
              checked={policies.business_hours_only}
              onChange={(e) => {
                setPolicies(prev => ({ ...prev, business_hours_only: e.target.checked }));
                setHasChanges(true);
              }}
              className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
            />
            <div>
              <span className="text-sm font-medium">Calculate SLA only during business hours</span>
              <p className="text-xs text-muted-foreground">
                Pause SLA timer outside working hours and on holidays
              </p>
            </div>
          </label>
          
          {policies.business_hours_only && (
            <div className="space-y-4 pt-4 border-t border-border/30">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                    Start Time
                  </label>
                  <input
                    type="time"
                    value={policies.business_hours?.start || '09:00'}
                    onChange={(e) => {
                      setPolicies(prev => ({
                        ...prev,
                        business_hours: { ...prev.business_hours, start: e.target.value }
                      }));
                      setHasChanges(true);
                    }}
                    className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                    End Time
                  </label>
                  <input
                    type="time"
                    value={policies.business_hours?.end || '18:00'}
                    onChange={(e) => {
                      setPolicies(prev => ({
                        ...prev,
                        business_hours: { ...prev.business_hours, end: e.target.value }
                      }));
                      setHasChanges(true);
                    }}
                    className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-2">
                  Working Days
                </label>
                <div className="flex gap-2">
                  {DAYS_OF_WEEK.map((day) => (
                    <button
                      key={day.value}
                      onClick={() => toggleBusinessDay(day.value)}
                      className={`w-10 h-10 rounded-lg text-xs font-medium transition-colors ${
                        (policies.business_hours?.days || []).includes(day.value)
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-secondary/50 text-muted-foreground hover:bg-secondary'
                      }`}
                    >
                      {day.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Holidays */}
      {policies.business_hours_only && (
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
            <Calendar size={14} />
            Holidays (SLA Paused)
          </h3>
          
          <div className="p-4 rounded-xl bg-secondary/20 border border-border/30">
            <div className="flex gap-2 mb-4">
              <input
                type="date"
                value={newHoliday}
                onChange={(e) => setNewHoliday(e.target.value)}
                className="flex-1 h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50"
                min={new Date().toISOString().split('T')[0]}
              />
              <button
                onClick={addHoliday}
                disabled={!newHoliday}
                className="px-4 h-10 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add Holiday
              </button>
            </div>
            
            {policies.holidays.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {policies.holidays.map((date) => (
                  <div
                    key={date}
                    className="flex items-center gap-2 px-3 py-1.5 bg-secondary rounded-lg text-sm"
                  >
                    <span>{new Date(date + 'T00:00:00').toLocaleDateString('en-US', { 
                      month: 'short', 
                      day: 'numeric',
                      year: 'numeric'
                    })}</span>
                    <button
                      onClick={() => removeHoliday(date)}
                      className="text-muted-foreground hover:text-red-400 transition-colors"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No holidays configured. Add dates when SLA timers should be paused.
              </p>
            )}
          </div>
        </div>
      )}

      {/* SLA Summary Table */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
          SLA Summary
        </h3>
        
        <div className="rounded-xl border border-border/30 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-secondary/30">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Priority</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">First Response</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">Resolution</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/30">
              {PRIORITIES.map((priority) => {
                const sla = policies.priority_slas?.[priority.value] || {};
                const Icon = priority.icon;
                
                return (
                  <tr key={priority.value} className="hover:bg-secondary/10">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Icon size={14} className={priority.color} />
                        <span className={priority.color}>{priority.label}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {formatDuration(sla.first_response_minutes || 60)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {formatDuration(sla.resolution_minutes || 480)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Unsaved Changes Warning */}
      {hasChanges && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-3 px-4 py-3 bg-amber-500/10 border border-amber-500/30 rounded-xl shadow-lg">
          <AlertCircle size={18} className="text-amber-400" />
          <span className="text-sm text-amber-400">You have unsaved changes</span>
          <button
            onClick={handleSave}
            disabled={saving}
            className="ml-2 px-3 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Now'}
          </button>
        </div>
      )}
    </div>
  );
};

export default SLAPoliciesTab;
