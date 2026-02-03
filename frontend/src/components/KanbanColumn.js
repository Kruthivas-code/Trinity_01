import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import SortableTicketCard from './SortableTicketCard';
import { Plus, Inbox } from 'lucide-react';

const KanbanColumn = ({ column, tickets, users, onTicketClick, onCreateTicket, staggerIndex, activeId, isMentionedTicket }) => {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });
  const ticketIds = tickets.map(t => t.id);

  return (
    <div
      ref={setNodeRef}
      className={`w-72 min-w-[288px] max-w-[288px] rounded-xl border flex flex-col animate-fade-in-up stagger-${staggerIndex} ${
        isOver ? 'border-primary/60 bg-primary/5' : 'glass border-border/60'
      }`}
      style={{ transition: 'border-color 100ms, background-color 100ms' }}
      data-testid={`kanban-column-${column.id}`}
    >
      <div className="px-4 py-3 flex items-center justify-between sticky top-0 z-10 bg-transparent backdrop-blur border-b border-border/40">
        <h3 className="text-sm font-semibold">{column.title}</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground bg-secondary/50 px-2 py-0.5 rounded-full font-medium">
            {tickets.length}
          </span>
          <button
            onClick={onCreateTicket}
            className="h-7 w-7 flex items-center justify-center rounded-lg hover:bg-primary/10 hover:text-primary transition-colors"
            title="Add ticket"
          >
            <Plus size={16} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {tickets.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-center py-10 px-4">
            <div className="w-14 h-14 rounded-xl empty-state-icon flex items-center justify-center mb-3">
              <Inbox size={24} className="text-muted-foreground/60" />
            </div>
            <p className="text-xs text-muted-foreground">No tickets yet</p>
          </div>
        ) : (
          <SortableContext items={ticketIds} strategy={verticalListSortingStrategy}>
            {tickets.map((ticket) => (
              <SortableTicketCard
                key={ticket.id}
                ticket={ticket}
                users={users}
                isMentioned={isMentionedTicket ? isMentionedTicket(ticket) : false}
                onClick={() => onTicketClick(ticket)}
                isActive={activeId === ticket.id}
              />
            ))}
          </SortableContext>
        )}
      </div>
    </div>
  );
};

export default KanbanColumn;
