import React, { useState, useEffect } from 'react';
import { 
  Settings, Plus, Trash2, Save, X, ChevronDown, ChevronRight,
  Type, Hash, Calendar, ToggleLeft, List, Building, User, Ticket,
  Loader2, GripVertical
} from 'lucide-react';
import Sidebar from './Sidebar';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const FIELD_TYPES = [
  { value: 'text', label: 'Text', icon: Type, description: 'Single line text input' },
  { value: 'number', label: 'Number', icon: Hash, description: 'Numeric value' },
  { value: 'select', label: 'Dropdown', icon: List, description: 'Select from options' },
  { value: 'date', label: 'Date', icon: Calendar, description: 'Date picker' },
  { value: 'boolean', label: 'Yes/No', icon: ToggleLeft, description: 'Toggle switch' }
];

const AdminPage = ({ user }) => {
  const [activeTab, setActiveTab] = useState('custom-fields');
  const [customFields, setCustomFields] = useState([]);
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [entityFilter, setEntityFilter] = useState('all');
  const [savingSettings, setSavingSettings] = useState(false);
  
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
      <div className="min-h-screen flex bg-background">
        <Sidebar user={user} />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 size={32} className="animate-spin text-primary" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-background">
      <div className="gradient-overlay" />
      
      {/* Main Sidebar Navigation */}
      <Sidebar user={user} />
      
      {/* Admin Content */}
      <div className="flex-1 flex flex-col relative z-10">
        {/* Header */}
        <header className="h-14 px-6 flex items-center justify-between border-b border-border/40 shrink-0 bg-background/80 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <Settings size={20} className="text-primary" />
            <h1 className="text-lg font-semibold">Admin Settings</h1>
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
                    <div className="text-center py-12 text-muted-foreground border border-dashed border-border rounded-xl">
                      <List size={40} className="mx-auto mb-3 opacity-50" />
                      <p className="font-medium">No custom fields yet</p>
                      <p className="text-sm mt-1">Create your first custom field to get started</p>
                      <button
                        onClick={() => setShowCreateModal(true)}
                        className="mt-4 h-9 px-4 inline-flex items-center gap-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
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
                          className="flex items-center justify-between p-4 rounded-xl bg-card border border-border/50 hover:border-border transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                              <Icon size={18} className="text-primary" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-medium">{field.name}</span>
                                {field.required && (
                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-destructive/20 text-destructive font-medium">
                                    Required
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-xs text-muted-foreground capitalize">
                                  {FIELD_TYPES.find(t => t.value === field.field_type)?.label || field.field_type}
                                </span>
                                <span className="text-muted-foreground/40">•</span>
                                <span className={`text-xs font-medium ${
                                  field.entity_type === 'ticket' ? 'text-primary' : 'text-amber-500'
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
                                <p className="text-xs text-muted-foreground mt-1">{field.description}</p>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleDeleteField(field.field_id)}
                              className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
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
                    <label className="block text-sm font-medium mb-2">Support Email</label>
                    <input
                      type="email"
                      value={settings.support_email || ''}
                      onChange={(e) => setSettings({ ...settings, support_email: e.target.value })}
                      className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                      placeholder="support@company.com"
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
                    >
                      <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                        settings.auto_assignment ? 'translate-x-6' : 'translate-x-0.5'
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
          </main>
        </div>
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
    </div>
  );
};

export default AdminPage;
