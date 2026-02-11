import React, { useState, useEffect, useCallback } from 'react';
import { X, Plus, Filter, Save } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const OPERATORS = {
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
  ],
  user: [
    { value: 'is', label: 'is' },
    { value: 'is_not', label: 'is not' },
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

function ConditionRow({ condition, fields, users, onChange, onRemove }) {
  const fieldDef = fields.find(f => f.field === condition.field);
  const fieldType = fieldDef ? fieldDef.type : 'text';
  const ops = OPERATORS[fieldType] || OPERATORS.text;
  const needsValue = !NO_VALUE_OPS.includes(condition.op);
  const isMulti = condition.op === 'is_one_of';

  const sel = 'h-8 rounded-md border border-border bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring';

  function renderValue() {
    if (!needsValue) return null;

    if (fieldType === 'select' && fieldDef && fieldDef.options) {
      if (isMulti) {
        const selected = Array.isArray(condition.value) ? condition.value : [];
        return (
          <div className="flex flex-wrap gap-1">
            {fieldDef.options.map(opt => (
              <button key={opt} type="button" onClick={() => {
                const next = selected.includes(opt) ? selected.filter(v => v !== opt) : selected.concat(opt);
                onChange({ ...condition, value: next });
              }}
              className={'h-7 px-2 text-xs rounded-md border ' + (selected.includes(opt) ? 'bg-foreground text-background border-foreground' : 'bg-background text-foreground border-border hover:bg-muted')}>
                {opt}
              </button>
            ))}
          </div>
        );
      }
      return (
        <select value={condition.value || ''} onChange={e => onChange({ ...condition, value: e.target.value })} className={sel + ' min-w-[140px]'} data-testid="filter-value-select">
          <option value="">Select...</option>
          {fieldDef.options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
        </select>
      );
    }

    if (fieldType === 'user') {
      return (
        <select value={condition.value || ''} onChange={e => onChange({ ...condition, value: e.target.value })} className={sel + ' min-w-[140px]'} data-testid="filter-value-user">
          <option value="">Select user...</option>
          {users.map(u => <option key={u.user_id} value={u.user_id}>{u.name}</option>)}
        </select>
      );
    }

    if (fieldType === 'date') {
      if (condition.op === 'between') {
        const vals = Array.isArray(condition.value) ? condition.value : ['', ''];
        return (
          <div className="flex items-center gap-1">
            <input type="date" value={vals[0] || ''} onChange={e => onChange({ ...condition, value: [e.target.value, vals[1]] })} className={sel + ' min-w-[120px]'} />
            <span className="text-xs text-muted-foreground">to</span>
            <input type="date" value={vals[1] || ''} onChange={e => onChange({ ...condition, value: [vals[0], e.target.value] })} className={sel + ' min-w-[120px]'} />
          </div>
        );
      }
      return <input type="date" value={condition.value || ''} onChange={e => onChange({ ...condition, value: e.target.value })} className={sel + ' min-w-[140px]'} />;
    }

    return (
      <input type={fieldType === 'number' ? 'number' : 'text'} value={condition.value || ''} onChange={e => onChange({ ...condition, value: e.target.value })} placeholder="Enter value..." className={sel + ' min-w-[160px]'} data-testid="filter-value-text" />
    );
  }

  return (
    <div className="flex items-center gap-2 py-1.5" data-testid="filter-condition-row">
      <select value={condition.field} onChange={e => onChange({ ...condition, field: e.target.value, op: 'is', value: null })} className={sel + ' min-w-[140px]'} data-testid="filter-field-select">
        <option value="">Select field...</option>
        {fields.map(f => <option key={f.field} value={f.field}>{f.label}</option>)}
      </select>
      <select value={condition.op} onChange={e => onChange({ ...condition, op: e.target.value, value: NO_VALUE_OPS.includes(e.target.value) ? null : condition.value })} className={sel + ' min-w-[120px]'} data-testid="filter-operator-select">
        {ops.map(op => <option key={op.value} value={op.value}>{op.label}</option>)}
      </select>
      {renderValue()}
      <button onClick={onRemove} type="button" className="h-8 w-8 flex items-center justify-center rounded-md hover:bg-muted text-muted-foreground" data-testid="filter-remove-condition">
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

function GroupBlock({ group, fields, users, onChange, onRemove, depth }) {
  const borderColor = depth === 0 ? 'border-border' : (group.logic === 'and' ? 'border-blue-300' : 'border-orange-300');
  const bgColor = depth === 0 ? '' : (group.logic === 'and' ? 'bg-blue-50/50' : 'bg-orange-50/50');

  function updateCond(idx, cond) {
    const conditions = group.conditions.map(function(c, i) { return i === idx ? cond : c; });
    onChange({ ...group, conditions: conditions });
  }
  function removeCond(idx) {
    onChange({ ...group, conditions: group.conditions.filter(function(_, i) { return i !== idx; }) });
  }
  function addCond() {
    onChange({ ...group, conditions: group.conditions.concat({ field: '', op: 'is', value: null }) });
  }
  function updateSub(idx, sub) {
    const groups = group.groups.map(function(g, i) { return i === idx ? sub : g; });
    onChange({ ...group, groups: groups });
  }
  function removeSub(idx) {
    onChange({ ...group, groups: group.groups.filter(function(_, i) { return i !== idx; }) });
  }
  function addSub() {
    onChange({ ...group, groups: group.groups.concat({ logic: 'and', conditions: [{ field: '', op: 'is', value: null }], groups: [] }) });
  }

  return (
    <div className={'rounded-lg border p-3 ' + borderColor + ' ' + bgColor + (depth > 0 ? ' ml-4' : '')} data-testid="filter-group">
      <div className="flex items-center justify-between mb-2">
        <button type="button" onClick={() => onChange({ ...group, logic: group.logic === 'and' ? 'or' : 'and' })}
          data-testid="filter-logic-toggle"
          className={'text-xs font-semibold px-2 py-1 rounded-md border ' + (group.logic === 'and' ? 'bg-blue-100 text-blue-700 border-blue-200' : 'bg-orange-100 text-orange-700 border-orange-200')}>
          {group.logic.toUpperCase()}
        </button>
        {depth > 0 && <button type="button" onClick={onRemove} className="text-xs text-muted-foreground hover:text-foreground">Remove group</button>}
      </div>
      {group.conditions.map(function(cond, idx) {
        return <ConditionRow key={idx} condition={cond} fields={fields} users={users} onChange={function(c) { updateCond(idx, c); }} onRemove={function() { removeCond(idx); }} />;
      })}
      {group.groups.map(function(sub, idx) {
        return (
          <div key={idx} className="mt-2">
            <GroupBlock group={sub} fields={fields} users={users} onChange={function(g) { updateSub(idx, g); }} onRemove={function() { removeSub(idx); }} depth={depth + 1} />
          </div>
        );
      })}
      <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border/50">
        <button type="button" onClick={addCond} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted" data-testid="filter-add-condition">
          <Plus className="h-3 w-3" /> condition
        </button>
        <button type="button" onClick={addSub} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted" data-testid="filter-add-group">
          <Plus className="h-3 w-3" /> group
        </button>
      </div>
    </div>
  );
}

function FilterBuilder({ onFilter, onSaveInbox, initialFilters }) {
  const [fields, setFields] = useState([]);
  const [users, setUsers] = useState([]);
  const [isOpen, setIsOpen] = useState(Boolean(initialFilters));
  const [filterTree, setFilterTree] = useState(initialFilters || { logic: 'and', conditions: [], groups: [] });
  const [activeCount, setActiveCount] = useState(0);

  useEffect(function() {
    var aborted = false;
    async function load() {
      try {
        var fRes = await fetch(BACKEND_URL + '/api/filter/fields', { credentials: 'include' });
        var uRes = await fetch(BACKEND_URL + '/api/users', { credentials: 'include' });
        if (!aborted && fRes.ok) setFields(await fRes.json());
        if (!aborted && uRes.ok) {
          var uData = await uRes.json();
          setUsers(Array.isArray(uData) ? uData : (uData.items || []));
        }
      } catch (e) { /* ignore */ }
    }
    load();
    return function() { aborted = true; };
  }, []);

  useEffect(function() {
    if (initialFilters) { setFilterTree(initialFilters); setIsOpen(true); }
  }, [initialFilters]);

  useEffect(function() {
    function count(tree) {
      var n = (tree.conditions || []).filter(function(c) { return c.field; }).length;
      (tree.groups || []).forEach(function(g) { n += count(g); });
      return n;
    }
    setActiveCount(count(filterTree));
  }, [filterTree]);

  var handleApply = useCallback(function() {
    var has = filterTree.conditions.some(function(c) { return c.field; }) || filterTree.groups.length > 0;
    onFilter(has ? filterTree : null);
  }, [filterTree, onFilter]);

  function handleClear() {
    var empty = { logic: 'and', conditions: [], groups: [] };
    setFilterTree(empty);
    onFilter(null);
  }

  function handleToggle() {
    if (!isOpen && filterTree.conditions.length === 0) {
      setFilterTree({ logic: 'and', conditions: [{ field: '', op: 'is', value: null }], groups: [] });
    }
    setIsOpen(!isOpen);
  }

  return (
    <div data-testid="filter-builder">
      <div className="flex items-center gap-2">
        <button type="button" onClick={handleToggle} data-testid="filter-toggle-btn"
          className={'flex items-center gap-2 h-8 px-3 rounded-md border text-sm ' + (activeCount > 0 ? 'bg-foreground text-background border-foreground' : 'bg-background text-foreground border-border hover:bg-muted')}>
          <Filter className="h-3.5 w-3.5" />
          Filter
          {activeCount > 0 && <span className="bg-background text-foreground text-xs rounded-full h-5 w-5 flex items-center justify-center font-medium">{activeCount}</span>}
        </button>
        {activeCount > 0 && (
          <button type="button" onClick={handleClear} className="text-xs text-muted-foreground hover:text-foreground" data-testid="filter-clear-btn">
            Clear all
          </button>
        )}
        {activeCount > 0 && onSaveInbox && (
          <button type="button" onClick={onSaveInbox} data-testid="filter-save-inbox-btn"
            className="flex items-center gap-1.5 h-8 px-3 rounded-md border border-border bg-background text-sm hover:bg-muted">
            <Save className="h-3.5 w-3.5" /> Save as Inbox
          </button>
        )}
      </div>
      {isOpen && (
        <div className="mt-3">
          <GroupBlock group={filterTree} fields={fields} users={users} onChange={setFilterTree} onRemove={function(){}} depth={0} />
          <div className="flex justify-end mt-3">
            <button type="button" onClick={handleApply} data-testid="filter-apply-btn"
              className="h-8 px-4 rounded-md bg-foreground text-background text-sm font-medium hover:bg-foreground/90">
              Apply Filters
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default FilterBuilder;
