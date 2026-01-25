import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy
} from '@dnd-kit/sortable';
import SortableTicketCard from './SortableTicketCard';
import { Plus, Inbox } from 'lucide-react';

const KanbanColumn = ({ 
  column, 
  tickets, 
  users, 
  onTicketClick, 
  onCreateTicket, 
  staggerIndex,
  isOver,
  activeId 
}) => {
  const { setNodeRef, isOver: isDirectlyOver } = useDroppable({
    id: column.id,
    data: {
      type: 'column',
      column
    }
  });

  const ticketIds = tickets.map(t => t.id);
  const showDropIndicator = isOver || isDirectlyOver;

  return (
    <div
      ref={setNodeRef}
      className={`
        w-72 min-w-[288px] max-w-[288px] rounded-xl border flex flex-col 
        animate-fade-in-up stagger-${staggerIndex}
        transition-all duration-200 ease-out
        ${showDropIndicator 
          ? 'border-primary/50 bg-primary/5 ring-2 ring-primary/20 scale-[1.01]' 
          : 'glass border-border/60'
        }
      `}
      data-testid={`kanban-column-${column.id}`}
    >
      {/* Column Header */}
      <div className="px-4 py-3 flex items-center justify-between sticky top-0 z-10 bg-transparent backdrop-blur border-b border-border/40">
        <h3 className="text-sm font-semibold" data-testid="column-title">
          {column.title}
        </h3>
        <div className="flex items-center gap-2">
          <span 
            className={`
              text-xs px-2 py-0.5 rounded-full font-medium transition-colors duration-200
              ${showDropIndicator 
                ? 'bg-primary/20 text-primary' 
                : 'bg-secondary/50 text-muted-foreground'
              }
            `} 
            data-testid="column-count"
          >
            {tickets.length}
          </span>
          <button
            onClick={onCreateTicket}
            className="h-7 w-7 flex items-center justify-center rounded-lg hover:bg-primary/10 hover:text-primary transition-interactive"
            data-testid="column-add-button"
            title="Add ticket"
          >
            <Plus size={16} />
          </button>
        </div>
      </div>

      {/* Column Body */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {tickets.length === 0 ? (
          <div 
            className={`
              flex flex-col items-center justify-center text-center py-10 px-4 
              transition-all duration-200 rounded-lg
              ${showDropIndicator ? 'bg-primary/10 border-2 border-dashed border-primary/30' : ''}
            `}
            data-testid="empty-state"
          >
            <div className={`
              w-14 h-14 rounded-xl flex items-center justify-center mb-3 transition-colors duration-200
              ${showDropIndicator ? 'bg-primary/20' : 'empty-state-icon'}
            `}>
              <Inbox size={24} className={`transition-colors duration-200 ${showDropIndicator ? 'text-primary' : 'text-muted-foreground/60'}`} />
            </div>
            <p className={`text-xs transition-colors duration-200 ${showDropIndicator ? 'text-primary font-medium' : 'text-muted-foreground'}`}>
              {showDropIndicator ? 'Drop here' : 'No tickets yet'}
            </p>
          </div>
        ) : (
          <SortableContext items={ticketIds} strategy={verticalListSortingStrategy}>
            {tickets.map((ticket) => (
              <SortableTicketCard
                key={ticket.id}
                ticket={ticket}
                users={users}
                onClick={() => onTicketClick(ticket)}
                isActive={activeId === ticket.id}
              />
            ))}
            
            {/* Drop zone indicator at end of list */}
            {showDropIndicator && (
              <div className="h-16 rounded-lg border-2 border-dashed border-primary/30 bg-primary/5 flex items-center justify-center">
                <span className="text-xs text-primary/70">Drop here</span>
              </div>
            )}
          </SortableContext>
        )}
      </div>
    </div>
  );
};

export default KanbanColumn;
