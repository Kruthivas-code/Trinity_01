import React from 'react';

const getPriorityColor = (priority) => {
  switch (priority) {
    case 'urgent': return '#ef4444';
    case 'high': return '#f97316';
    case 'medium': return '#eab308';
    case 'low': return '#22c55e';
    default: return '#64748b';
  }
};

const TicketCard = ({ ticket, users, onClick, isDragging }) => {
  if (!ticket || !ticket.id) {
    return null; // Safety check for undefined tickets
  }
  
  const assignee = users.find(u => u.id === ticket.assignee_id);
  const priorityColor = getPriorityColor(ticket.priority);

  return (
    <button
      onClick={onClick}
      className={`w-full text-left glass rounded-xl p-3 border hover:border-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--glass-ring)] transition-interactive ${
        isDragging ? 'shadow-2xl' : ''
      }`}
      data-testid="ticket-card"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className="text-sm font-medium line-clamp-2 flex-1" data-testid="ticket-title">
          {ticket.title}
        </h4>
        <span
          className="shrink-0 w-2.5 h-2.5 rounded-full mt-1"
          style={{ background: priorityColor }}
          data-testid="ticket-priority-dot"
          title={ticket.priority || 'No priority'}
        />
      </div>

      {ticket.description && (
        <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
          {ticket.description}
        </p>
      )}

      <div className="flex items-center justify-between gap-2">
        {assignee ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <div className="w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center text-primary font-medium">
              {assignee.name.charAt(0).toUpperCase()}
            </div>
            <span data-testid="ticket-assignee">{assignee.name}</span>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground" data-testid="ticket-assignee">
            Unassigned
          </span>
        )}
        
        <span className="text-xs text-muted-foreground">
          #{ticket.id?.slice(-6) || 'N/A'}
        </span>
      </div>
    </button>
  );
};

export default TicketCard;
