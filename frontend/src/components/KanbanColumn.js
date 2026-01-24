import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy
} from '@dnd-kit/sortable';
import SortableTicketCard from './SortableTicketCard';
import { Plus } from 'lucide-react';

const KanbanColumn = ({ column, tickets, users, onTicketClick, onCreateTicket, staggerIndex }) => {
  const { setNodeRef } = useDroppable({
    id: column.id
  });

  const ticketIds = tickets.map(t => t.id);

  return (
    <div
      ref={setNodeRef}
      className={`glass w-72 min-w-[288px] max-w-[288px] rounded-xl border border-border/60 flex flex-col animate-fade-in-up stagger-${staggerIndex}`}
      data-testid={`kanban-column-${column.id}`}
    >
      {/* Column Header */}
      <div className="px-4 py-3 flex items-center justify-between sticky top-0 z-10 bg-transparent backdrop-blur border-b border-border/40">
        <h3 className="text-sm font-medium" data-testid="column-title">
          {column.title}
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground" data-testid="column-count">
            {tickets.length}
          </span>
          <button
            onClick={onCreateTicket}
            className="h-6 w-6 flex items-center justify-center rounded hover:bg-white/5 transition-interactive"
            data-testid="column-add-button"
            title="Add ticket"
          >
            <Plus size={14} />
          </button>
        </div>
      </div>

      {/* Column Body */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {tickets.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-center p-6 text-muted-foreground" data-testid="empty-state">
            <div className="w-12 h-12 rounded-lg glass flex items-center justify-center mb-2 text-xl">
              📋
            </div>
            <p className="text-xs">No tickets yet</p>
          </div>
        ) : (
          <SortableContext items={ticketIds} strategy={verticalListSortingStrategy}>
            {tickets.map((ticket) => (
              <SortableTicketCard
                key={ticket.id}
                ticket={ticket}
                users={users}
                onClick={() => onTicketClick(ticket)}
              />
            ))}
          </SortableContext>
        )}
      </div>
    </div>
  );
};

export default KanbanColumn;
