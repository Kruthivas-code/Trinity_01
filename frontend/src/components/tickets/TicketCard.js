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
      className={`w-full text-left bg-card rounded-lg p-3 border cursor-grab active:cursor-grabbing relative transition-all duration-150 ${
        isDragging ? 'shadow-lg border-foreground/30 scale-[1.02]' : 'border-border hover:border-foreground/20 hover:shadow-md'
      } ${isMentioned ? 'border-l-2 border-l-amber-500 bg-amber-50/50' : ''}`}
      data-testid="ticket-card"
    >
      {/* Mention Indicator Badge */}
      {isMentioned && (
        <div 
          className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-amber-500 flex items-center justify-center shadow-sm"
          title="You were mentioned in this ticket"
        >
          <AtSign size={10} className="text-white" />
        </div>
      )}
      
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-[11px] text-muted-foreground font-mono">
          {ticket.ticket_id || `#${ticket.id?.slice(-6)}`}
        </span>
        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${escalationConfig.bg} ${escalationConfig.text} ${escalationConfig.border}`}>
          {escalationConfig.label}
        </span>
      </div>

      <div className="flex items-center gap-2 mb-2">
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${priorityConfig.color}`} />
          <span className={`text-[11px] font-medium ${priorityConfig.text}`}>{priorityConfig.label}</span>
        </div>
        <span className="text-muted-foreground/30">·</span>
        {assignee ? (
          <div className="flex items-center gap-1.5 min-w-0">
            <div className="w-4 h-4 rounded-full bg-foreground/10 flex items-center justify-center text-[9px] text-foreground font-medium shrink-0">
              {assignee.name.charAt(0).toUpperCase()}
            </div>
            <span className="text-[11px] text-muted-foreground truncate">{assignee.name.split(' ')[0]}</span>
          </div>
        ) : (
          <span className="text-[11px] text-muted-foreground/60 flex items-center gap-1">
            <User size={11} />Unassigned
          </span>
        )}
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {tags.slice(0, 3).map((tag, idx) => (
            <span key={idx} className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded bg-secondary text-muted-foreground">
              <Tag size={9} />{tag}
            </span>
          ))}
          {tags.length > 3 && <span className="text-[10px] text-muted-foreground/50">+{tags.length - 3}</span>}
        </div>
      )}

      <h4 className="text-[13px] text-foreground leading-snug font-medium" data-testid="ticket-card-title">{ticket.title}</h4>
      {(ticket.description || ticket.last_message_text) && (
        <p className="text-[11px] text-muted-foreground/80 mt-1 line-clamp-2 leading-relaxed" data-testid="ticket-card-preview">
          {(ticket.description || ticket.last_message_text || '').slice(0, 150)}
        </p>
      )}
      {ticket.customer_email && (
        <p className="text-[10px] text-muted-foreground truncate mt-1.5">{ticket.customer_email}</p>
      )}
    </div>
  );
};

export default TicketCard;
