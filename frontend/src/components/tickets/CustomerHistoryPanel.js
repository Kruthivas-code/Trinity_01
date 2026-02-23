import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Loader2 } from 'lucide-react';
import { STATUSES, PRIORITIES } from '../../hooks/useTicketDrawer';

const CustomerHistoryPanel = ({ ticket, users, relatedTickets, loadingRelated, assignee, getStatusConfig, getPriorityConfig, onTicketSwitch }) => {
  const navigate = useNavigate();
  return (
    <div className="w-[240px] bg-background border-l border-border/40 flex flex-col shrink-0" data-testid="customer-history-panel">
      {/* Customer History Header */}
      <div className="h-12 px-3 flex items-center justify-between border-b border-border/30 shrink-0">
        <div className="flex items-center gap-2">
          <Users size={14} className="text-primary" />
          <span className="text-sm font-medium">Customer Tickets</span>
        </div>
        <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-foreground/10 text-foreground font-medium">
          {relatedTickets.length + 1}
        </span>
      </div>
      
      {/* Customer Info */}
      {(ticket.customer_email || ticket.email_sender || ticket.customer_name) && (
        <div className="px-3 py-2 border-b border-border/30">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-foreground/10 flex items-center justify-center text-xs font-medium text-foreground shrink-0">
              {(ticket.customer_name || ticket.email_sender_name || ticket.customer_email || 'C').charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">
                {ticket.customer_name || ticket.email_sender_name || 'Customer'}
              </p>
              <button
                onClick={() => { navigator.clipboard.writeText(ticket.customer_email || ticket.email_sender || ''); }}
                className="text-[11px] text-muted-foreground hover:text-primary truncate block max-w-full transition-colors cursor-pointer"
                title={`${ticket.customer_email || ticket.email_sender || 'No email'} — Click to copy`}
                data-testid="customer-email-copy-panel"
              >
                {ticket.customer_email || ticket.email_sender || 'No email'}
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Ticket List */}
      <div className="flex-1 overflow-y-auto">
        {loadingRelated ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={16} className="animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="p-1.5 space-y-0.5">
            {/* Current Ticket - highlighted */}
            <div
              className="px-2 py-1.5 rounded-lg bg-foreground/[0.07] border-2 border-foreground/15 cursor-default"
              data-testid="current-ticket-item"
            >
              <div className="flex items-center gap-1.5 mb-0.5">
                <span className="text-[11px] font-mono text-foreground font-medium">
                  {ticket.ticket_id || `#${ticket.id?.slice(-8)}`}
                </span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${getStatusConfig(ticket.status).color} text-white`}>
                  {getStatusConfig(ticket.status).label}
                </span>
                <span className={`text-[10px] font-semibold px-1 py-0.5 rounded ${
                  ticket.escalation_level === 'L3' ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                  ticket.escalation_level === 'L2' ? 'bg-amber-50 text-amber-800 border border-amber-200' :
                  'bg-emerald-50 text-emerald-700 border border-emerald-200'
                }`}>
                  {ticket.escalation_level || 'L1'}
                </span>
              </div>
              <p className="text-[12px] font-medium text-foreground line-clamp-1 mb-0.5">
                {ticket.title}
              </p>
              <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                <div className="flex items-center gap-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${getPriorityConfig(ticket.priority).value === 'urgent' ? 'bg-red-500' : getPriorityConfig(ticket.priority).value === 'high' ? 'bg-orange-500' : getPriorityConfig(ticket.priority).value === 'medium' ? 'bg-amber-500' : 'bg-emerald-500'}`} />
                  <span>{getPriorityConfig(ticket.priority).label}</span>
                </div>
                <span>
                  {new Date(ticket.updated_at ? (ticket.updated_at?.endsWith?.('Z') ? ticket.updated_at : ticket.updated_at + 'Z') : (ticket.created_at?.endsWith?.('Z') ? ticket.created_at : ticket.created_at + 'Z')).toLocaleDateString('en-US', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric' })}
                </span>
                <span className="truncate max-w-[60px]">
                  {assignee?.name || 'Unassigned'}
                </span>
              </div>
            </div>
            
            {/* Other tickets from same customer */}
            {relatedTickets.map(related => {
              const relatedStatus = STATUSES.find(s => s.value === related.status) || STATUSES[0];
              const relatedAssignee = Array.isArray(users) ? users.find(u => (u.id || u.user_id) === related.assignee_id) : null;
              const relatedPriority = PRIORITIES.find(p => p.value === related.priority) || PRIORITIES[1];
              
              return (
                <div
                  key={related.id || related.ticket_id}
                  className="px-2 py-1.5 rounded-lg bg-secondary/30 border border-transparent hover:bg-secondary/50 hover:border-border cursor-pointer transition-colors duration-150"
                  onClick={() => {
                    const ticketId = related.ticket_id || related.id;
                    if (onTicketSwitch) {
                      onTicketSwitch(ticketId);
                    }
                    navigate(`/all-tickets?ticket=${ticketId}`, { replace: true });
                  }}
                  data-testid={`related-ticket-${related.ticket_id || related.id}`}
                >
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="text-[11px] font-mono text-muted-foreground">
                      {related.ticket_id || `#${related.id?.slice(-8)}`}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${relatedStatus.color} text-white`}>
                      {relatedStatus.label}
                    </span>
                    <span className={`text-[10px] font-semibold px-1 py-0.5 rounded ${
                      related.escalation_level === 'L3' ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                      related.escalation_level === 'L2' ? 'bg-amber-50 text-amber-800 border border-amber-200' :
                      'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    }`}>
                      {related.escalation_level || 'L1'}
                    </span>
                  </div>
                  <p className="text-[12px] font-medium text-foreground/80 line-clamp-1 mb-0.5">
                    {related.title}
                  </p>
                  <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <span className={`w-1.5 h-1.5 rounded-full ${
                        related.priority === 'urgent' ? 'bg-red-500' : 
                        related.priority === 'high' ? 'bg-orange-500' : 
                        related.priority === 'medium' ? 'bg-amber-500' : 'bg-emerald-500'
                      }`} />
                      <span>{relatedPriority.label}</span>
                    </div>
                    <span>
                      {new Date(related.updated_at || related.created_at).toLocaleDateString('en-US', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric' })}
                    </span>
                    <span className="truncate max-w-[60px]">
                      {relatedAssignee?.name || 'Unassigned'}
                    </span>
                  </div>
                </div>
              );
            })}
            
            {/* Empty state when no other tickets */}
            {relatedTickets.length === 0 && (
              <div className="text-center py-6 text-muted-foreground/50">
                <p className="text-[12px]">No other tickets</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CustomerHistoryPanel;
