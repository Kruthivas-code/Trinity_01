import React from 'react';
import { Tag, User } from 'lucide-react';

const getPriorityConfig = (priority) => {
  switch (priority) {
    case 'urgent': return { color: 'bg-red-500', text: 'text-red-400', label: 'Urgent' };
    case 'high': return { color: 'bg-orange-500', text: 'text-orange-400', label: 'High' };
    case 'medium': return { color: 'bg-amber-500', text: 'text-amber-400', label: 'Medium' };
    case 'low': return { color: 'bg-emerald-500', text: 'text-emerald-400', label: 'Low' };
    default: return { color: 'bg-slate-500', text: 'text-slate-400', label: 'None' };
  }
};

const getEscalationConfig = (level) => {
  switch (level) {
    case 'L1': return { color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', label: 'L1' };
    case 'L2': return { color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', label: 'L2' };
    case 'L3': return { color: 'bg-red-500/20 text-red-400 border-red-500/30', label: 'L3' };
    default: return { color: 'bg-slate-500/20 text-slate-400 border-slate-500/30', label: 'L1' };
  }
};

const TicketCard = ({ ticket, users = [], onClick, isDragging }) => {
  if (!ticket || !ticket.id) return null;
  
  const assignee = Array.isArray(users) ? users.find(u => u.id === ticket.assignee_id) : null;
  const priorityConfig = getPriorityConfig(ticket.priority);
  const escalationConfig = getEscalationConfig(ticket.escalation_level);
  const tags = ticket.tags || [];

  return (
    <div
      onClick={isDragging ? undefined : onClick}
      className={`w-full text-left glass rounded-lg p-3 border cursor-grab active:cursor-grabbing ${
        isDragging ? 'shadow-xl border-primary/50' : 'hover:border-white/20'
      }`}
      data-testid="ticket-card"
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-[10px] text-muted-foreground/70 font-mono">
          {ticket.ticket_id || `#${ticket.id?.slice(-6)}`}
        </span>
        <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded border ${escalationConfig.color}`}>
          {escalationConfig.label}
        </span>
      </div>

      <div className="flex items-center gap-2 mb-2">
        <div className="flex items-center gap-1">
          <span className={`w-2 h-2 rounded-full ${priorityConfig.color}`} />
          <span className={`text-[10px] font-medium ${priorityConfig.text}`}>{priorityConfig.label}</span>
        </div>
        <span className="text-muted-foreground/30">•</span>
        {assignee ? (
          <div className="flex items-center gap-1 min-w-0">
            <div className="w-4 h-4 rounded-full bg-primary/20 flex items-center justify-center text-[9px] text-primary font-medium shrink-0">
              {assignee.name.charAt(0).toUpperCase()}
            </div>
            <span className="text-[10px] text-muted-foreground truncate">{assignee.name.split(' ')[0]}</span>
          </div>
        ) : (
          <span className="text-[10px] text-muted-foreground/50 flex items-center gap-1">
            <User size={10} />Unassigned
          </span>
        )}
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {tags.slice(0, 3).map((tag, idx) => (
            <span key={idx} className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[9px] font-medium rounded bg-secondary/50 text-muted-foreground">
              <Tag size={8} />{tag}
            </span>
          ))}
          {tags.length > 3 && <span className="text-[9px] text-muted-foreground/50">+{tags.length - 3}</span>}
        </div>
      )}

      <h4 className="text-[11px] text-foreground/80 leading-tight truncate">{ticket.title}</h4>
      {ticket.customer_email && (
        <p className="text-[9px] text-muted-foreground/50 truncate mt-1">{ticket.customer_email}</p>
      )}
    </div>
  );
};

export default TicketCard;
