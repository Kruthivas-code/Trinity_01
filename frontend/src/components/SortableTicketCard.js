import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import TicketCard from './TicketCard';

const SortableTicketCard = ({ ticket, users, onClick, isActive }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
    isOver
  } = useSortable({ 
    id: ticket.id,
    data: {
      type: 'ticket',
      ticket
    }
  });

  // Use CSS.Translate for better performance (GPU accelerated)
  const style = {
    transform: CSS.Translate.toString(transform),
    transition: transition || 'transform 150ms cubic-bezier(0.25, 0.1, 0.25, 1)',
    opacity: isDragging ? 0.4 : 1,
    zIndex: isDragging ? 1000 : isOver ? 100 : 'auto',
  };

  return (
    <div 
      ref={setNodeRef} 
      style={style} 
      {...attributes} 
      {...listeners}
      className={`
        touch-none select-none
        ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}
        ${isOver ? 'relative' : ''}
      `}
    >
      {/* Drop indicator line when hovering over this card */}
      {isOver && !isDragging && (
        <div className="absolute -top-1 left-0 right-0 h-0.5 bg-primary rounded-full animate-pulse" />
      )}
      
      <TicketCard 
        ticket={ticket} 
        users={users} 
        onClick={onClick} 
        isDragging={isDragging}
      />
    </div>
  );
};

export default SortableTicketCard;
