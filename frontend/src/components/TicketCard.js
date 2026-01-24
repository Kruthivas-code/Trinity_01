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

// Strip HTML tags and decode entities for display
const stripHtml = (html) => {
  if (!html) return '';
  // Remove HTML tags
  let text = html.replace(/<[^>]*>/g, ' ');
  // Decode common HTML entities
  text = text.replace(/&nbsp;/g, ' ')
             .replace(/&amp;/g, '&')
             .replace(/&lt;/g, '<')
             .replace(/&gt;/g, '>')
             .replace(/&quot;/g, '"')
             .replace(/&#39;/g, "'");
  // Collapse multiple spaces
  text = text.replace(/\s+/g, ' ').trim();
  return text;
};

const TicketCard = ({ ticket, users, onClick, isDragging }) => {
  if (!ticket || !ticket.id) {
    return null;
  }
  
  const assignee = users.find(u => u.id === ticket.assignee_id);
  const priorityColor = getPriorityColor(ticket.priority);
  const cleanDescription = stripHtml(ticket.description);

  return (
    <button
      onClick={onClick}
      className={`w-full text-left glass rounded-lg p-3 border hover:border-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--glass-ring)] transition-interactive ${
        isDragging ? 'shadow-2xl scale-105' : ''
      }`}
      data-testid="ticket-card"
    >
      {/* Title row with priority dot */}
      <div className="flex items-start gap-2 mb-1.5">
        <span
          className="shrink-0 w-2 h-2 rounded-full mt-1.5"
          style={{ background: priorityColor }}
          data-testid="ticket-priority-dot"
          title={ticket.priority || 'No priority'}
        />
        <h4 className="text-sm font-medium leading-tight line-clamp-2 break-words" data-testid="ticket-title">
          {ticket.title}
        </h4>
      </div>

      {/* Description - compact, 2 lines max */}
      {cleanDescription && (
        <p className="text-xs text-muted-foreground/70 line-clamp-2 mb-2 pl-4 leading-relaxed break-words">
          {cleanDescription}
        </p>
      )}

      {/* Footer: Assignee + ID */}
      <div className="flex items-center justify-between gap-2 pl-4">
        {assignee ? (
          <div className="flex items-center gap-1.5 min-w-0">
            <div className="w-4 h-4 rounded-full bg-primary/20 flex items-center justify-center text-[10px] text-primary font-medium shrink-0">
              {assignee.name.charAt(0).toUpperCase()}
            </div>
            <span className="text-[11px] text-muted-foreground truncate" data-testid="ticket-assignee">
              {assignee.name}
            </span>
          </div>
        ) : (
          <span className="text-[11px] text-muted-foreground/50" data-testid="ticket-assignee">
            Unassigned
          </span>
        )}
        
        <span className="text-[10px] text-muted-foreground/50 font-mono shrink-0">
          {ticket.ticket_id || `#${ticket.id?.slice(-6)}`}
        </span>
      </div>
    </button>
  );
};

export default TicketCard;
