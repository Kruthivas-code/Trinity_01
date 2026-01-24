import React, { useState, useEffect } from 'react';
import { 
  Settings, Plus, Trash2, Edit2, Save, X, ChevronDown, ChevronRight,
  Type, Hash, Calendar, ToggleLeft, List, Building, User, Ticket,
  Loader2
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const FIELD_TYPES = [
  { value: 'text', label: 'Text', icon: Type },
  { value: 'number', label: 'Number', icon: Hash },
  { value: 'select', label: 'Dropdown', icon: List },
  { value: 'date', label: 'Date', icon: Calendar },
  { value: 'boolean', label: 'Yes/No', icon: ToggleLeft }
];

const AdminPage = ({ user }) => {
  const [activeTab, setActiveTab] = useState('custom-fields');
  const [customFields, setCustomFields] = useState([]);
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingField, setEditingField] = useState(null);
  const [entityFilter, setEntityFilter] = useState('all');
  
  // Form state for new field
  const [newField, setNewField] = useState({
    name: '',
    field_type: 'text',
    entity_type: 'ticket',
    options: '',
    required: false,
    description: ''
  });

  useEffect(() => {
    fetchCustomFields();
    fetchSettings();
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
      <div className="flex items-center justify-center h-full">
        <Loader2 size={32} className="animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <header className="h-14 px-6 flex items-center justify-between border-b border-border/40 shrink-0">
        <div className="flex items-center gap-3">
          <Settings size={20} className="text-primary" />
          <h1 className="text-lg font-semibold">Admin Settings</h1>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside className="w-56 border-r border-border/40 p-4 shrink-0">
          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab('custom-fields')}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                activeTab === 'custom-fields'
                  ? 'bg-primary/20 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
              }`}
            >
              <List size={16} />
              Custom Fields
            </button>
            <button
              onClick={() => setActiveTab('general')}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                activeTab === 'general'
                  ? 'bg-primary/20 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
              }`}
            >
              <Building size={16} />
              General Settings
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
              <div className="space-y-2">
                {filteredFields.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
                    <List size={40} className="mx-auto mb-3 opacity-50" />
                    <p>No custom fields yet</p>
                    <p className="text-sm">Create your first custom field to get started</p>
                  </div>
                ) : (
                  filteredFields.map(field => {
                    const Icon = getFieldTypeIcon(field.field_type);
                    return (
                      <div
                        key={field.field_id}
                        className="flex items-center justify-between p-4 rounded-lg bg-secondary/20 border border-border/30"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Icon size={16} className="text-primary" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm">{field.name}</span>
                              {field.required && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-400/20 text-red-400">
                                  Required
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className="text-xs text-muted-foreground capitalize">
                                {field.field_type}
                              </span>
                              <span className="text-muted-foreground/40">•</span>
                              <span className={`text-xs ${
                                field.entity_type === 'ticket' ? 'text-primary' : 'text-amber-400'
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
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleDeleteField(field.field_id)}
                            className="h-7 w-7 flex items-center justify-center rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {activeTab === 'general' && (
            <div className="max-w-2xl">
              <h2 className="text-lg font-medium mb-6">General Settings</h2>
              
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium mb-2">Company Name</label>
                  <input
                    type="text"
                    value={settings.company_name || ''}
                    onChange={(e) => setSettings({ ...settings, company_name: e.target.value })}
                    className="w-full h-10 px-3 rounded-lg bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Support Email</label>
                  <input
                    type="email"
                    value={settings.support_email || ''}
                    onChange={(e) => setSettings({ ...settings, support_email: e.target.value })}
                    className="w-full h-10 px-3 rounded-lg bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Default Priority</label>
                  <select
                    value={settings.default_priority || 'medium'}
                    onChange={(e) => setSettings({ ...settings, default_priority: e.target.value })}
                    className="w-full h-10 px-3 rounded-lg bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <label className="block text-sm font-medium">Auto Assignment</label>
                    <p className="text-xs text-muted-foreground">
                      Automatically assign new tickets using round-robin
                    </p>
                  </div>
                  <button
                    onClick={() => setSettings({ ...settings, auto_assignment: !settings.auto_assignment })}
                    className={`w-12 h-6 rounded-full transition-colors ${
                      settings.auto_assignment ? 'bg-primary' : 'bg-secondary'
                    }`}
                  >
                    <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
                      settings.auto_assignment ? 'translate-x-6' : 'translate-x-0.5'
                    }`} />
                  </button>
                </div>

                <button
                  onClick={handleSaveSettings}
                  className="h-10 px-6 flex items-center gap-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
                >
                  <Save size={16} />
                  Save Settings
                </button>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Create Field Modal */}
      {showCreateModal && (
        <>
          <div 
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50"
            onClick={() => setShowCreateModal(false)}
          />
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            <div className="bg-[hsl(222,28%,10%)] rounded-xl border border-border/40 w-full max-w-md shadow-2xl">
              <div className="flex items-center justify-between px-5 py-4 border-b border-border/30">
                <h3 className="font-medium">Create Custom Field</h3>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="h-7 w-7 flex items-center justify-center rounded hover:bg-white/5"
                >
                  <X size={16} />
                </button>
              </div>
              
              <form onSubmit={handleCreateField} className="p-5 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1.5">Field Name</label>
                  <input
                    type="text"
                    value={newField.name}
                    onChange={(e) => setNewField({ ...newField, name: e.target.value })}
                    className="w-full h-9 px-3 rounded-lg bg-secondary/30 border border-border/30 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50"
                    placeholder="e.g., Customer Type"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1.5">Apply To</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setNewField({ ...newField, entity_type: 'ticket' })}
                      className={`flex-1 h-9 flex items-center justify-center gap-2 rounded-lg text-sm transition-colors ${
                        newField.entity_type === 'ticket'
                          ? 'bg-primary/20 text-primary border border-primary/30'
                          : 'bg-secondary/30 border border-border/30 text-muted-foreground'
                      }`}
                    >
                      <Ticket size={14} />
                      Ticket
                    </button>
                    <button
                      type="button"
                      onClick={() => setNewField({ ...newField, entity_type: 'user' })}
                      className={`flex-1 h-9 flex items-center justify-center gap-2 rounded-lg text-sm transition-colors ${
                        newField.entity_type === 'user'
                          ? 'bg-amber-400/20 text-amber-400 border border-amber-400/30'
                          : 'bg-secondary/30 border border-border/30 text-muted-foreground'
                      }`}
                    >
                      <User size={14} />
                      User
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1.5">Field Type</label>
                  <select
                    value={newField.field_type}
                    onChange={(e) => setNewField({ ...newField, field_type: e.target.value })}
                    className="w-full h-9 px-3 rounded-lg bg-secondary/30 border border-border/30 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50"
                  >
                    {FIELD_TYPES.map(type => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
                </div>

                {newField.field_type === 'select' && (
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Options (comma separated)</label>
                    <input
                      type="text"
                      value={newField.options}
                      onChange={(e) => setNewField({ ...newField, options: e.target.value })}
                      className="w-full h-9 px-3 rounded-lg bg-secondary/30 border border-border/30 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50"
                      placeholder="Option 1, Option 2, Option 3"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-1.5">Description (optional)</label>
                  <input
                    type="text"
                    value={newField.description}
                    onChange={(e) => setNewField({ ...newField, description: e.target.value })}
                    className="w-full h-9 px-3 rounded-lg bg-secondary/30 border border-border/30 text-sm focus:outline-none focus:ring-1 focus:ring-primary/50"
                    placeholder="What is this field for?"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="required"
                    checked={newField.required}
                    onChange={(e) => setNewField({ ...newField, required: e.target.checked })}
                    className="w-4 h-4 rounded border-border/30"
                  />
                  <label htmlFor="required" className="text-sm">Required field</label>
                </div>

                <div className="flex gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="flex-1 h-9 rounded-lg border border-border/40 text-sm hover:bg-white/5 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 h-9 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
                  >
                    Create Field
                  </button>
                </div>
              </form>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default AdminPage;
