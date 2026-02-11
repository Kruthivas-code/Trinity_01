import React, { useState, useEffect, useCallback } from 'react';
import { X, Plus, Filter, ChevronDown, Save, Search } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const OPERATORS_BY_TYPE = {
  text: [
    { value: 'is', label: 'is' },
    { value: 'is_not', label: 'is not' },
    { value: 'contains', label: 'contains' },
    { value: 'not_contains', label: 'does not contain' },
    { value: 'is_empty', label: 'is empty' },
    { value: 'is_not_empty', label: 'is not empty' },
  ],
  select: [
    { value: 'is', label: 'is' },
    { value: 'is_not', label: 'is not' },
    { value: 'is_one_of', label: 'is one of' },
    { value: 'is_not_one_of', label: 'is not one of' },
  ],
  date: [
    { value: 'before', label: 'before' },
    { value: 'after', label: 'after' },
    { value: 'between', label: 'between' },
  ],
  number: [
    { value: 'eq', label: 'equals' },
    { value: 'gt', label: 'greater than' },
    { value: 'lt', label: 'less than' },
    { value: 'gte', label: 'at least' },
    { value: 'lte', label: 'at most' },
  ],
  user: [
    { value: 'is', label: 'is' },
    { value: 'is_not', label: 'is not' },
    { value: 'is_one_of', label: 'is one of' },
    { value: 'is_none', label: 'is unassigned' },
    { value: 'is_not_none', label: 'is assigned' },
  ],
  array: [
    { value: 'contains', label: 'contains' },
    { value: 'not_contains', label: 'does not contain' },
    { value: 'is_empty', label: 'is empty' },
    { value: 'is_not_empty', label: 'is not empty' },
  ],
};

const NO_VALUE_OPS = ['is_empty', 'is_not_empty', 'is_none', 'is_not_none'];

// Single condition row
const ConditionRow = ({ condition, fields, users, onChange, onRemove, isFirst }) => {
  const fieldDef = fields.find(f => f.field === condition.field);
  const fieldType = fieldDef?.type || 'text';
  const operators = OPERATORS_BY_TYPE[fieldType] || OPERATORS_BY_TYPE.text;
  const needsValue = !NO_VALUE_OPS.includes(condition.op);
  const isMultiSelect = ['is_one_of', 'is_not_one_of'].includes(condition.op);

  return (
    <div className="flex items-center gap-2 py-1.5" data-testid="filter-condition-row">
      {/* Field picker */}
      <select
        data-testid="filter-field-select"
        value={condition.field}
        onChange={e => onChange({ ...condition, field: e.target.value, op: 'is', value: null })}
        className="h-8 rounded-md border border-border bg-background px-2 text-sm min-w-[140px] focus:outline-none focus:ring-1 focus:ring-ring"
      >
        <option value="">Select field...</option>
        {fields.map(f => (
          <option key={f.field} value={f.field}>{f.label}</option>
        ))}
      </select>

      {/* Operator picker */}
      <select
        data-testid="filter-operator-select"
        value={condition.op}
        onChange={e => onChange({ ...condition, op: e.target.value, value: NO_VALUE_OPS.includes(e.target.value) ? null : condition.value })}
        className="h-8 rounded-md border border-border bg-background px-2 text-sm min-w-[120px] focus:outline-none focus:ring-1 focus:ring-ring"
      >
        {operators.map(op => (
          <option key={op.value} value={op.value}>{op.label}</option>
        ))}
      </select>

      {/* Value input */}
      {needsValue && (
        <ValueInput
          fieldDef={fieldDef}
          fieldType={fieldType}
          op={condition.op}
          value={condition.value}
          users={users}
          isMultiSelect={isMultiSelect}
          onChange={val => onChange({ ...condition, value: val })}
        />
      )}

      <button
        onClick={onRemove}
        className="h-8 w-8 flex items-center justify-center rounded-md hover:bg-muted text-muted-foreground"
        data-testid="filter-remove-condition"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
};

// Value input - renders differently based on field type
const ValueInput = ({ fieldDef, fieldType, op, value, users, isMultiSelect, onChange }) => {
  const inputClass = "h-8 rounded-md border border-border bg-background px-2 text-sm min-w-[160px] focus:outline-none focus:ring-1 focus:ring-ring";

  if (fieldType === 'select' && fieldDef?.options) {
    if (isMultiSelect) {
      const selected = Array.isArray(value) ? value : [];
      return (
        <div className="flex flex-wrap gap-1 items-center min-w-[160px]">
          {fieldDef.options.map(opt => (
            <button
              key={opt}
              onClick={() => {
                const next = selected.includes(opt) ? selected.filter(v => v !== opt) : [...selected, opt];
                onChange(next);
              }}
              className={`h-7 px-2 text-xs rounded-md border ${
                selected.includes(opt)
                  ? 'bg-foreground text-background border-foreground'
                  : 'bg-background text-foreground border-border hover:bg-muted'
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      );
    }
    return (
      <select value={value || ''} onChange={e => onChange(e.target.value)} className={inputClass} data-testid="filter-value-select">
        <option value="">Select...</option>
        {fieldDef.options.map(opt => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    );
  }

  if (fieldType === 'user') {
    if (isMultiSelect) {
      const selected = Array.isArray(value) ? value : [];
      return (
        <div className="flex flex-wrap gap-1 items-center min-w-[160px]">
          {users.map(u => (
            <button
              key={u.user_id}
              onClick={() => {
                const next = selected.includes(u.user_id) ? selected.filter(v => v !== u.user_id) : [...selected, u.user_id];
                onChange(next);
              }}
              className={`h-7 px-2 text-xs rounded-md border ${
                selected.includes(u.user_id)
                  ? 'bg-foreground text-background border-foreground'
                  : 'bg-background text-foreground border-border hover:bg-muted'
              }`}
            >
              {u.name}
            </button>
          ))}
        </div>
      );
    }
    return (
      <select value={value || ''} onChange={e => onChange(e.target.value)} className={inputClass} data-testid="filter-value-user">
        <option value="">Select user...</option>
        {users.map(u => (
          <option key={u.user_id} value={u.user_id}>{u.name}</option>
        ))}
      </select>
    );
  }

  if (fieldType === 'date') {
    if (op === 'between') {
      const vals = Array.isArray(value) ? value : ['', ''];
      return (
        <div className="flex items-center gap-1">
          <input type="date" value={vals[0] || ''} onChange={e => onChange([e.target.value, vals[1]])}
            className={inputClass + ' min-w-[130px]'} data-testid="filter-date-from" />
          <span className="text-xs text-muted-foreground">to</span>
          <input type="date" value={vals[1] || ''} onChange={e => onChange([vals[0], e.target.value])}
            className={inputClass + ' min-w-[130px]'} data-testid="filter-date-to" />
        </div>
      );
    }
    return <input type="date" value={value || ''} onChange={e => onChange(e.target.value)} className={inputClass} data-testid="filter-date-value" />;
  }

  return (
    <input
      type={fieldType === 'number' ? 'number' : 'text'}
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      placeholder="Enter value..."
      className={inputClass}
      data-testid="filter-value-text"
    />
  );
};

// A filter group (bracket) with AND/OR logic
const FilterGroupUI = ({ group, fields, users, onChange, onRemove, depth = 0 }) => {
  const updateCondition = (idx, cond) => {
    const next = { ...group, conditions: group.conditions.map((c, i) => i === idx ? cond : c) };
    onChange(next);
  };
  const removeCondition = (idx) => {
    const next = { ...group, conditions: group.conditions.filter((_, i) => i !== idx) };
    onChange(next);
  };
  const addCondition = () => {
    onChange({ ...group, conditions: [...group.conditions, { field: '', op: 'is', value: null }] });
  };
  const updateSubgroup = (idx, subgroup) => {
    const next = { ...group, groups: group.groups.map((g, i) => i === idx ? subgroup : g) };
    onChange(next);
  };
  const removeSubgroup = (idx) => {
    onChange({ ...group, groups: group.groups.filter((_, i) => i !== idx) });
  };
  const addSubgroup = () => {
    onChange({ ...group, groups: [...group.groups, { logic: 'and', conditions: [{ field: '', op: 'is', value: null }], groups: [] }] });
  };
  const toggleLogic = () => {
    onChange({ ...group, logic: group.logic === 'and' ? 'or' : 'and' });
  };

  const borderColor = depth === 0 ? 'border-border' : group.logic === 'and' ? 'border-blue-300' : 'border-orange-300';
  const bgColor = depth === 0 ? '' : group.logic === 'and' ? 'bg-blue-50/50' : 'bg-orange-50/50';

  return (
    <div className={`rounded-lg border ${borderColor} ${bgColor} p-3 ${depth > 0 ? 'ml-4' : ''}`} data-testid="filter-group">
      {/* Logic toggle + remove */}
      <div className="flex items-center justify-between mb-2">
        <button
          onClick={toggleLogic}
          data-testid="filter-logic-toggle"
          className={`text-xs font-semibold px-2 py-1 rounded-md border ${
            group.logic === 'and'
              ? 'bg-blue-100 text-blue-700 border-blue-200'
              : 'bg-orange-100 text-orange-700 border-orange-200'
          }`}
        >
          {group.logic.toUpperCase()}
        </button>
        {depth > 0 && (
          <button onClick={onRemove} className="text-xs text-muted-foreground hover:text-foreground" data-testid="filter-remove-group">
            Remove group
          </button>
        )}
      </div>

      {/* Conditions */}
      {group.conditions.map((cond, idx) => (
        <ConditionRow
          key={idx}
          condition={cond}
          fields={fields}
          users={users}
          isFirst={idx === 0}
          onChange={c => updateCondition(idx, c)}
          onRemove={() => removeCondition(idx)}
        />
      ))}

      {/* Nested groups */}
      {group.groups.map((subgroup, idx) => (
        <div key={idx} className="mt-2">
          <FilterGroupUI
            group={subgroup}
            fields={fields}
            users={users}
            onChange={g => updateSubgroup(idx, g)}
            onRemove={() => removeSubgroup(idx)}
            depth={depth + 1}
          />
        </div>
      ))}

      {/* Add buttons */}
      <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border/50">
        <button
          onClick={addCondition}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted"
          data-testid="filter-add-condition"
        >
          <Plus className="h-3 w-3" /> condition
        </button>
        <button
          onClick={addSubgroup}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted"
          data-testid="filter-add-group"
        >
          <Plus className="h-3 w-3" /> group
        </button>
      </div>
    </div>
  );
};

// Main FilterBuilder component
const FilterBuilder = ({ onFilter, onSaveInbox, initialFilters = null }) => {
  const [fields, setFields] = useState([]);
  const [users, setUsers] = useState([]);
  const [isOpen, setIsOpen] = useState(!!initialFilters);
  const [filterTree, setFilterTree] = useState(
    initialFilters || { logic: 'and', conditions: [], groups: [] }
  );
  const [activeFilterCount, setActiveFilterCount] = useState(0);

  // Load filter fields and users
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [fieldsRes, usersRes] = await Promise.all([
          fetch(`${BACKEND_URL}/api/filter/fields`, { credentials: 'include' }),
          fetch(`${BACKEND_URL}/api/users`, { credentials: 'include' }),
        ]);
        if (fieldsRes.ok) setFields(await fieldsRes.json());
        if (usersRes.ok) setUsers(await usersRes.json());
      } catch (e) {
        console.error('Failed to load filter fields:', e);
      }
    };
    fetchData();
  }, []);

  // Update initialFilters when prop changes (e.g., navigating to a saved inbox)
  useEffect(() => {
    if (initialFilters) {
      setFilterTree(initialFilters);
      setIsOpen(true);
    }
  }, [initialFilters]);

  // Count active filters
  useEffect(() => {
    const countConditions = (tree) => {
      let count = (tree.conditions || []).filter(c => c.field).length;
      for (const g of (tree.groups || [])) {
        count += countConditions(g);
      }
      return count;
    };
    setActiveFilterCount(countConditions(filterTree));
  }, [filterTree]);

  const handleApply = useCallback(() => {
    const hasConditions = filterTree.conditions.some(c => c.field) || filterTree.groups.length > 0;
    onFilter(hasConditions ? filterTree : null);
  }, [filterTree, onFilter]);

  const handleClear = () => {
    const empty = { logic: 'and', conditions: [], groups: [] };
    setFilterTree(empty);
    onFilter(null);
  };

  const handleSaveInbox = () => {
    if (activeFilterCount > 0 && onSaveInbox) {
      onSaveInbox(filterTree);
    }
  };

  return (
    <div data-testid="filter-builder">
      {/* Trigger bar */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => { setIsOpen(!isOpen); if (!isOpen && filterTree.conditions.length === 0) setFilterTree({ ...filterTree, conditions: [{ field: '', op: 'is', value: null }] }); }}
          data-testid="filter-toggle-btn"
          className={`flex items-center gap-2 h-8 px-3 rounded-md border text-sm ${
            activeFilterCount > 0
              ? 'bg-foreground text-background border-foreground'
              : 'bg-background text-foreground border-border hover:bg-muted'
          }`}
        >
          <Filter className="h-3.5 w-3.5" />
          Filter
          {activeFilterCount > 0 && (
            <span className="bg-background text-foreground text-xs rounded-full h-5 w-5 flex items-center justify-center font-medium">
              {activeFilterCount}
            </span>
          )}
        </button>

        {activeFilterCount > 0 && (
          <>
            <button onClick={handleClear} className="text-xs text-muted-foreground hover:text-foreground" data-testid="filter-clear-btn">
              Clear all
            </button>
            {onSaveInbox && (
              <button
                onClick={handleSaveInbox}
                data-testid="filter-save-inbox-btn"
                className="flex items-center gap-1.5 h-8 px-3 rounded-md border border-border bg-background text-sm hover:bg-muted"
              >
                <Save className="h-3.5 w-3.5" /> Save as Inbox
              </button>
            )}
          </>
        )}
      </div>

      {/* Filter builder panel */}
      {isOpen && (
        <div className="mt-3 animate-in fade-in slide-in-from-top-2 duration-200">
          <FilterGroupUI
            group={filterTree}
            fields={fields}
            users={users}
            onChange={setFilterTree}
            onRemove={() => {}}
            depth={0}
          />
          <div className="flex justify-end mt-3">
            <button
              onClick={handleApply}
              data-testid="filter-apply-btn"
              className="h-8 px-4 rounded-md bg-foreground text-background text-sm font-medium hover:bg-foreground/90"
            >
              Apply Filters
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FilterBuilder;
