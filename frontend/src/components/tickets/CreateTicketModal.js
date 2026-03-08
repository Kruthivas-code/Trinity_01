import React, { useState } from 'react';
import { X, Mail, Send } from 'lucide-react';

const STATUSES = [
  { value: 'todo', label: 'Open' },
  { value: 'waiting', label: 'Waiting' },
  { value: 'closed', label: 'Closed' }
];

const CreateTicketModal = ({ isOpen, users = [], onClose, onCreate, onCreated }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'todo',
    assignee_id: null,
    customer_email: '',
    send_email: false,
    cc: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (onCreate) {
      onCreate(formData);
      resetForm();
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        title: formData.title,
        description: formData.description,
        status: formData.status,
        assignee_id: formData.assignee_id,
        customer_email: formData.customer_email || undefined,
        send_email: formData.send_email,
        cc: formData.cc ? formData.cc.split(',').map(e => e.trim()).filter(Boolean) : [],
      };

      const response = await fetch(`${BACKEND_URL}/api/tickets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) throw new Error('Failed to create ticket');
      
      resetForm();
      if (onCreated) onCreated();
    } catch (error) {
      console.error('Failed to create ticket:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setFormData({
      title: '', description: '', status: 'todo', assignee_id: null,
      customer_email: '', send_email: false, cc: '',
    });
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={handleClose}
        data-testid="modal-backdrop"
      >
        <div
          className="glass-elevated max-w-lg w-full rounded-2xl p-6 border border-border/60 relative"
          onClick={(e) => e.stopPropagation()}
          data-testid="create-ticket-modal"
        >
          <form onSubmit={handleSubmit}>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold" data-testid="modal-title">
                Create New Ticket
              </h2>
              <button
                type="button"
                onClick={handleClose}
                className="h-8 w-8 flex items-center justify-center rounded-lg hover:bg-foreground/10 transition-interactive"
                data-testid="modal-close-button"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-4">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="modal-title-input">
                  Subject *
                </label>
                <input
                  id="modal-title-input"
                  type="text"
                  className="w-full h-10 px-4 rounded-lg bg-secondary/70 border border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="Enter ticket subject"
                  required
                  data-testid="modal-title-input"
                />
              </div>

              {/* Customer Email */}
              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="modal-email-input">
                  Customer Email
                </label>
                <input
                  id="modal-email-input"
                  type="email"
                  className="w-full h-10 px-4 rounded-lg bg-secondary/70 border border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                  value={formData.customer_email}
                  onChange={(e) => setFormData({ ...formData, customer_email: e.target.value })}
                  placeholder="customer@example.com"
                  data-testid="modal-email-input"
                />
              </div>

              {/* Description / Message Body */}
              <div>
                <label className="block text-sm font-medium mb-2" htmlFor="modal-description-input">
                  {formData.send_email ? 'Email Body *' : 'Description'}
                </label>
                <textarea
                  id="modal-description-input"
                  className="w-full min-h-[100px] px-4 py-3 rounded-lg bg-secondary/70 border border-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-interactive resize-none"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder={formData.send_email ? "Write your email message..." : "Add a description..."}
                  required={formData.send_email}
                  data-testid="modal-description-input"
                />
              </div>

              {/* Send Email Toggle + CC */}
              {formData.customer_email && (
                <div className="space-y-3 p-3 rounded-lg bg-primary/5 border border-primary/20">
                  <label className="flex items-center gap-3 cursor-pointer" data-testid="send-email-toggle">
                    <div className="relative">
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        checked={formData.send_email}
                        onChange={(e) => setFormData({ ...formData, send_email: e.target.checked })}
                      />
                      <div className="w-9 h-5 bg-secondary rounded-full peer-checked:bg-primary transition-colors" />
                      <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-4" />
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Mail size={14} className="text-primary" />
                      <span className="text-sm font-medium">Send email to customer</span>
                    </div>
                  </label>
                  
                  {formData.send_email && (
                    <div>
                      <label className="block text-xs font-medium text-muted-foreground mb-1.5" htmlFor="modal-cc-input">
                        CC (optional)
                      </label>
                      <input
                        id="modal-cc-input"
                        type="text"
                        className="w-full h-9 px-3 rounded-md bg-secondary/70 border border-white/10 text-foreground text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-ring transition-interactive"
                        value={formData.cc}
                        onChange={(e) => setFormData({ ...formData, cc: e.target.value })}
                        placeholder="cc1@example.com, cc2@example.com"
                        data-testid="modal-cc-input"
                      />
                    </div>
                  )}
                </div>
              )}

              {/* Status & Assignee row */}
              <div className="grid grid-cols-2 gap-3">
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
                className={`flex-1 h-10 px-4 rounded-lg font-medium transition-interactive disabled:opacity-50 flex items-center justify-center gap-2 ${
                  formData.send_email
                    ? 'bg-primary text-primary-foreground hover:bg-cyan-400/90'
                    : 'bg-primary text-primary-foreground hover:bg-cyan-400/90'
                }`}
                data-testid="modal-create-button"
                disabled={isSubmitting || (formData.send_email && !formData.description.trim())}
              >
                {isSubmitting ? 'Creating...' : (
                  <>
                    {formData.send_email && <Send size={14} />}
                    {formData.send_email ? 'Create & Send Email' : 'Create Ticket'}
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
};

export default CreateTicketModal;
