import React from 'react';
import { Tag, User, AtSign } from 'lucide-react';

const getPriorityConfig = (priority) => {
  switch (priority) {
    case 'urgent': return { color: 'bg-rose-500', text: 'text-rose-600', label: 'Urgent' };
    case 'high': return { color: 'bg-orange-500', text: 'text-orange-600', label: 'High' };
    case 'medium': return { color: 'bg-amber-500', text: 'text-amber-700', label: 'Medium' };
    case 'low': return { color: 'bg-emerald-500', text: 'text-emerald-700', label: 'Low' };
    default: return { color: 'bg-slate-400', text: 'text-slate-500', label: 'None' };
  }
};

const getEscalationConfig = (level) => {
  switch (level) {
    case 'L1': return { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', label: 'L1' };
    case 'L2': return { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200', label: 'L2' };
    case 'L3': return { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', label: 'L3' };
    default: return { bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200', label: 'L1' };
  }
};

const TicketCard = ({ ticket, users = [], isMentioned = false, onClick, isDragging }) => {
  if (!ticket || !ticket.id) return null;
  
  const assignee = Array.isArray(users) ? users.find(u => u.id === ticket.assignee_id) : null;
  const priorityConfig = getPriorityConfig(ticket.priority);
  const escalationConfig = getEscalationConfig(ticket.escalation_level);
  const tags = ticket.tags || [];

  return (
    <div
      onClick={isDragging ? undefined : onClick}
      className={`w-full text-left bg-card rounded-md px-2.5 py-2 border cursor-grab active:cursor-grabbing relative transition-all duration-150 ${
        isDragging ? 'shadow-lg border-foreground/30 scale-[1.02]' : 'border-border hover:border-foreground/20 hover:shadow-md'
      } ${isMentioned ? 'border-l-2 border-l-amber-500 bg-amber-50/50' : ''}`}
      data-testid="ticket-card"
    >
      {isMentioned && (
        <div 
          className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-amber-500 flex items-center justify-center shadow-sm"
          title="You were mentioned in this ticket"
        >
          <AtSign size={10} className="text-white" />
        </div>
      )}

      {/* Row 1: Ticket ID · Priority · Assignee | Escalation */}
      <div className="flex items-center justify-between gap-1.5 mb-1">
        <div className="flex items-center gap-1.5 min-w-0 text-[11px]">
          <span className="text-muted-foreground font-mono shrink-0">{ticket.ticket_id || `#${ticket.id?.slice(-6)}`}</span>
          <span className="text-muted-foreground/30 shrink-0">·</span>
          <span className={`w-1.5 h-1.5 rounded-full ${priorityConfig.color} shrink-0`} />
          <span className={`font-medium ${priorityConfig.text} shrink-0`}>{priorityConfig.label}</span>
          <span className="text-muted-foreground/30 shrink-0">·</span>
          {assignee ? (
            <span className="text-muted-foreground truncate">{assignee.name.split(' ')[0]}</span>
          ) : (
            <span className="text-muted-foreground/60 flex items-center gap-0.5"><User size={10} />—</span>
          )}
        </div>
        <span className={`text-[9px] font-semibold px-1 py-px rounded border shrink-0 ${escalationConfig.bg} ${escalationConfig.text} ${escalationConfig.border}`}>
          {escalationConfig.label}
        </span>
      </div>

      {/* Row 2: Tags (inline, compact) */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-0.5 mb-1">
          {tags.slice(0, 2).map((tag, idx) => (
            <span key={idx} className="inline-flex items-center gap-0.5 px-1 py-px text-[9px] font-medium rounded bg-secondary text-muted-foreground">
              <Tag size={8} />{tag}
            </span>
          ))}
          {tags.length > 2 && <span className="text-[9px] text-muted-foreground/50">+{tags.length - 2}</span>}
        </div>
      )}

      {/* Row 3: Subject */}
      <h4 className="text-[12px] text-foreground leading-snug font-medium" data-testid="ticket-card-title">{ticket.title}</h4>

      {/* Row 4: Message preview */}
      {(ticket.description || ticket.last_message_text) && (
        <p className="text-[11px] text-muted-foreground/70 mt-0.5 line-clamp-2 leading-snug" data-testid="ticket-card-preview">
          {(ticket.description || ticket.last_message_text || '').slice(0, 120)}
        </p>
      )}

      {/* Row 5: Customer email */}
      {ticket.customer_email && (
        <p className="text-[10px] text-muted-foreground truncate mt-1">{ticket.customer_email}</p>
      )}
    </div>
  );
};

export default TicketCard;
