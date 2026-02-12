import React, { useState } from 'react';
import { X } from 'lucide-react';

const STATUSES = [
  { value: 'todo', label: 'To Do' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'waiting', label: 'Waiting on Customer' },
  { value: 'review', label: 'Review' },
  { value: 'resolved', label: 'Resolved' }
];

const CreateTicketModal = ({ isOpen, users = [], onClose, onCreate, onCreated }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'todo',
    assignee_id: null
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // If onCreate is provided, use it (legacy behavior)
    if (onCreate) {
      onCreate(formData);
      setFormData({
        title: '',
        description: '',
        status: 'todo',
        assignee_id: null
      });
      return;
    }

    // Otherwise, handle the creation internally
    setIsSubmitting(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/tickets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) throw new Error('Failed to create ticket');
      
      setFormData({
        title: '',
        description: '',
        status: 'todo',
        assignee_id: null
      });
      
      if (onCreated) onCreated();
    } catch (error) {
      console.error('Failed to create ticket:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setFormData({
      title: '',
      description: '',
      status: 'todo',
      assignee_id: null
    });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={handleClose}
        data-testid="modal-backdrop"
      >
        {/* Modal */}
        <div
          className="glass-elevated max-w-lg w-full rounded-2xl p-6 border border-border/60 relative"
          onClick={(e) => e.stopPropagation()}
          data-testid="create-ticket-modal"
        >
          <form onSubmit={handleSubmit}>
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold" data-testid="modal-title">
                Create New Ticket
              </h2>
              <button
                type="button"
                onClick={handleClose}
                className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-white/5 transition-interactive"
                data-testid="modal-close-button"
              >
                <X size={18} />
              </button>
            </div>

            {/* Body */}
            <div className="space-y-4">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="modal-title-input">
                  Title *
                </label>
                <input
                  id="modal-title-input"
                  type="text"
                  className="w-full h-10 px-4 rounded-lg bg-secondary/70 border border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="Enter ticket title"
                  required
                  data-testid="modal-title-input"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="modal-description-input">
                  Description
                </label>
                <textarea
                  id="modal-description-input"
                  className="w-full min-h-[100px] px-4 py-3 rounded-lg bg-secondary/70 border border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive resize-none"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Add a description..."
                  data-testid="modal-description-input"
                />
              </div>

              {/* Status */}
              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="modal-status-select">
                  Status
                </label>
                <select
                  id="modal-status-select"
                  className="w-full h-10 px-4 rounded-lg bg-secondary/70 border border-white/10 text-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  data-testid="modal-status-select"
                >
                  {STATUSES.map(status => (
                    <option key={status.value} value={status.value}>
                      {status.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Assignee */}
              {users.length > 0 && (
                <div>
                  <label className="block text-sm font-medium mb-2" htmlFor="modal-assignee-select">
                    Assignee
                  </label>
                  <select
                    id="modal-assignee-select"
                    className="w-full h-10 px-4 rounded-lg bg-secondary/70 border border-white/10 text-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                    value={formData.assignee_id || ''}
                    onChange={(e) => setFormData({ ...formData, assignee_id: e.target.value || null })}
                    data-testid="modal-assignee-select"
                  >
                    <option value="">Unassigned</option>
                    {Array.isArray(users) && users.map(user => (
                      <option key={user.id} value={user.id}>
                        {user.name} ({user.email})
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="mt-6 flex items-center gap-3">
              <button
                type="button"
                onClick={handleClose}
                className="flex-1 h-10 px-4 rounded-lg bg-secondary/70 text-secondary-foreground border border-white/10 hover:bg-secondary/90 transition-interactive"
                data-testid="modal-cancel-button"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 h-10 px-4 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-cyan-400/90 transition-interactive disabled:opacity-50"
                data-testid="modal-create-button"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Creating...' : 'Create Ticket'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
};

export default CreateTicketModal;
