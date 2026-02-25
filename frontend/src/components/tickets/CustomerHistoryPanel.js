import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Loader2 } from 'lucide-react';
import { STATUSES, PRIORITIES } from '../../hooks/useTicketDrawer';

const CustomerHistoryPanel = ({ ticket, users, relatedTickets, loadingRelated, assignee, getStatusConfig, getPriorityConfig, onTicketSwitch }) => {
  const navigate = useNavigate();

  // Merge current ticket + related into a single list, sorted by created_at desc (most recent first).
  // The list order never changes when clicking a ticket — only the highlight moves.
  const allTickets = useMemo(() => {
    const currentId = ticket?.ticket_id || ticket?.id;
    const merged = [
      { ...ticket, _isCurrent: true, _sortKey: ticket?.created_at },
      ...relatedTickets.filter(r => (r.ticket_id || r.id) !== currentId).map(r => ({ ...r, _isCurrent: false, _sortKey: r.created_at }))
    ];
    return merged.sort((a, b) => new Date(b._sortKey || 0) - new Date(a._sortKey || 0));
  }, [ticket, relatedTickets]);

  const activeId = ticket?.ticket_id || ticket?.id;

  const renderTicketItem = (t) => {
    const id = t.ticket_id || t.id;
    const isActive = id === activeId;
    const status = STATUSES.find(s => s.value === t.status) || STATUSES[0];
    const priority = PRIORITIES.find(p => p.value === t.priority) || PRIORITIES[1];
    const itemAssignee = t._isCurrent ? assignee : (Array.isArray(users) ? users.find(u => (u.id || u.user_id) === t.assignee_id) : null);

    return (
      <div
        key={id}
        className={`px-2 py-1.5 rounded-lg cursor-pointer transition-colors duration-150 ${
          isActive
            ? 'bg-foreground/[0.07] border-2 border-foreground/15'
            : 'bg-secondary/30 border border-transparent hover:bg-secondary/50 hover:border-border'
        }`}
        onClick={() => {
          if (!isActive) {
            if (onTicketSwitch) onTicketSwitch(id);
            navigate(`/all-tickets?ticket=${id}`, { replace: true });
          }
        }}
        data-testid={isActive ? 'current-ticket-item' : `related-ticket-${id}`}
      >
        <div className="flex items-center gap-1.5 mb-0.5">
          <span className={`text-[11px] font-mono ${isActive ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
            {id || `#${t.id?.slice(-8)}`}
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${status.color} text-white`}>
            {status.label}
          </span>
          <span className={`text-[10px] font-semibold px-1 py-0.5 rounded ${
            t.escalation_level === 'L3' ? 'bg-rose-50 text-rose-700 border border-rose-200' :
            t.escalation_level === 'L2' ? 'bg-amber-50 text-amber-800 border border-amber-200' :
            'bg-emerald-50 text-emerald-700 border border-emerald-200'
          }`}>
            {t.escalation_level || 'L1'}
          </span>
        </div>
        <p className={`text-[12px] font-medium line-clamp-1 mb-0.5 ${isActive ? 'text-foreground' : 'text-foreground/80'}`}>
          {t.title}
        </p>
        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
          <div className="flex items-center gap-1">
            <span className={`w-1.5 h-1.5 rounded-full ${
              priority.value === 'urgent' ? 'bg-red-500' :
              priority.value === 'high' ? 'bg-orange-500' :
              priority.value === 'medium' ? 'bg-amber-500' : 'bg-emerald-500'
            }`} />
            <span>{priority.label}</span>
          </div>
          <span>
            {new Date(t.updated_at ? (t.updated_at?.endsWith?.('Z') ? t.updated_at : t.updated_at + 'Z') : (t.created_at?.endsWith?.('Z') ? t.created_at : t.created_at + 'Z')).toLocaleDateString('en-US', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric' })}
          </span>
          <span className="truncate max-w-[60px]">
            {itemAssignee?.name || 'Unassigned'}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="w-[240px] bg-background border-l border-border/40 flex flex-col shrink-0" data-testid="customer-history-panel">
      {/* Customer History Header */}
      <div className="h-12 px-3 flex items-center justify-between border-b border-border/30 shrink-0">
        <div className="flex items-center gap-2">
          <Users size={14} className="text-primary" />
          <span className="text-sm font-medium">Customer Tickets</span>
        </div>
        <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-foreground/10 text-foreground font-medium">
          {allTickets.length}
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
      
      {/* Ticket List — stable order, active ticket highlighted */}
      <div className="flex-1 overflow-y-auto">
        {loadingRelated ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={16} className="animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="p-1.5 space-y-0.5">
            {allTickets.map(renderTicketItem)}
            {allTickets.length === 1 && (
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
