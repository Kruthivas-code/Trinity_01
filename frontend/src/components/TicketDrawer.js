import React, { useState, useEffect } from 'react';
import { X, Trash2, Save, MessageSquare, Send, ChevronDown, ChevronUp, Loader2, StickyNote, Clock, User } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const STATUSES = [
  { value: 'todo', label: 'To Do' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'waiting', label: 'Waiting on Customer' },
  { value: 'review', label: 'Review' },
  { value: 'resolved', label: 'Resolved' }
];

const PRIORITIES = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' }
];

const TicketDrawer = ({ ticket, users, isOpen, onClose, onUpdate, onDelete }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'backlog',
    assignee_id: null,
    priority: 'medium'
  });
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    if (ticket) {
      setFormData({
        title: ticket.title || '',
        description: ticket.description || '',
        status: ticket.status || 'backlog',
        assignee_id: ticket.assignee_id || null,
        priority: ticket.priority || 'medium'
      });
      setShowDeleteConfirm(false); // Reset delete confirmation when opening drawer
    }
  }, [ticket]);

  const handleSubmit = (e) => {
    e.preventDefault();
    setShowDeleteConfirm(false); // Reset after save
    if (ticket) {
      onUpdate(ticket.id, formData);
    }
  };

  const handleDelete = () => {
    if (ticket) {
      onDelete(ticket.id);
    }
  };

  const handleDeleteClick = () => {
    console.log('Delete button clicked, current showDeleteConfirm:', showDeleteConfirm);
    setShowDeleteConfirm(prev => {
      console.log('Setting showDeleteConfirm from', prev, 'to true');
      return true;
    });
  };

  const handleCancelDelete = () => {
    console.log('Cancel delete clicked');
    setShowDeleteConfirm(false);
  };

  const handleConfirmDelete = () => {
    console.log('Confirm delete clicked');
    handleDelete();
  };

  if (!isOpen || !ticket) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 pointer-events-auto"
        onClick={onClose}
        data-testid="drawer-backdrop"
        style={{ pointerEvents: 'auto' }}
      />

      {/* Drawer */}
      <div
        className="fixed right-0 top-0 bottom-0 w-full max-w-md glass-elevated border-l border-border/60 z-[60] overflow-y-auto pointer-events-auto"
        data-testid="ticket-drawer"
        style={{ pointerEvents: 'auto' }}
      >
        <form onSubmit={handleSubmit} className="h-full flex flex-col">
          {/* Header */}
          <div className="px-6 py-4 border-b border-border/40 flex items-center justify-between sticky top-0 bg-transparent backdrop-blur">
            <h2 className="text-lg font-semibold" data-testid="drawer-title">
              Edit Ticket
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-white/5 transition-interactive"
              data-testid="drawer-close-button"
            >
              <X size={18} />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 px-6 py-6 space-y-5">
            {/* Title */}
            <div>
              <label className="block text-sm font-medium mb-2" htmlFor="drawer-title-input">
                Title
              </label>
              <input
                id="drawer-title-input"
                type="text"
                className="w-full h-10 px-4 rounded-lg bg-secondary/70 border border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                required
                data-testid="drawer-title-input"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium mb-2" htmlFor="drawer-description-input">
                Description
              </label>
              <textarea
                id="drawer-description-input"
                className="w-full min-h-[120px] px-4 py-3 rounded-lg bg-secondary/70 border border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive resize-none"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Add a description..."
                data-testid="drawer-description-input"
              />
            </div>

            {/* Status */}
            <div>
              <label className="block text-sm font-medium mb-2" htmlFor="drawer-status-select">
                Status
              </label>
              <select
                id="drawer-status-select"
                className="w-full h-10 px-4 rounded-lg bg-secondary/70 border border-white/10 text-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                data-testid="drawer-status-select"
              >
                {STATUSES.map(status => (
                  <option key={status.value} value={status.value}>
                    {status.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Priority */}
            <div>
              <label className="block text-sm font-medium mb-2" htmlFor="drawer-priority-select">
                Priority
              </label>
              <select
                id="drawer-priority-select"
                className="w-full h-10 px-4 rounded-lg bg-secondary/70 border border-white/10 text-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                data-testid="drawer-priority-select"
              >
                {PRIORITIES.map(priority => (
                  <option key={priority.value} value={priority.value}>
                    {priority.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Assignee */}
            <div>
              <label className="block text-sm font-medium mb-2" htmlFor="drawer-assignee-select">
                Assignee
              </label>
              <select
                id="drawer-assignee-select"
                className="w-full h-10 px-4 rounded-lg bg-secondary/70 border border-white/10 text-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                value={formData.assignee_id || ''}
                onChange={(e) => setFormData({ ...formData, assignee_id: e.target.value || null })}
                data-testid="drawer-assignee-select"
              >
                <option value="">Unassigned</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>
                    {user.name} ({user.email})
                  </option>
                ))}
              </select>
            </div>

            {/* Metadata */}
            <div className="pt-4 border-t border-border/40">
              <div className="space-y-2 text-xs text-muted-foreground">
                <div className="flex justify-between">
                  <span>Created:</span>
                  <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Updated:</span>
                  <span>{new Date(ticket.updated_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>ID:</span>
                  <span>#{ticket.id?.slice(-8) || 'N/A'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Footer - Save Button */}
          <div className="px-6 py-4 border-t border-border/40">
            <button
              type="submit"
              className="w-full h-10 px-4 flex items-center justify-center gap-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-cyan-400/90 transition-interactive"
              data-testid="drawer-save-button"
            >
              <Save size={16} />
              Save Changes
            </button>
          </div>
        </form>

        {/* Delete Section - Outside Form */}
        <div className="px-6 py-4 border-t border-border/40">
          {console.log('Rendering delete section, showDeleteConfirm:', showDeleteConfirm)}
          {!showDeleteConfirm ? (
            <button
              type="button"
              onClick={handleDeleteClick}
              className="w-full h-10 px-4 flex items-center justify-center gap-2 rounded-lg bg-destructive/20 text-destructive hover:bg-destructive/30 transition-interactive"
              data-testid="drawer-delete-button"
            >
              <Trash2 size={16} />
              <span className="ml-1">Delete Ticket</span>
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleCancelDelete}
                className="flex-1 h-10 px-4 flex items-center justify-center gap-2 rounded-lg bg-secondary/70 text-secondary-foreground border border-white/10 hover:bg-secondary/90 transition-interactive"
                data-testid="drawer-delete-cancel-button"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                className="flex-1 h-10 px-4 flex items-center justify-center gap-2 rounded-lg bg-destructive text-destructive-foreground font-medium transition-interactive"
                data-testid="drawer-delete-confirm-button"
              >
                Confirm Delete
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default TicketDrawer;
