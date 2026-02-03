import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import TicketCard from './TicketCard';

const SortableTicketCard = ({ ticket, users, isMentioned, onClick, isActive }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: ticket.id });

  // Direct transform without CSS utility for instant response
  const style = {
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    transition: isDragging ? 'none' : 'transform 120ms ease',
    opacity: isDragging ? 0.3 : 1,
    pointerEvents: isDragging ? 'none' : 'auto',
  };

  return (
    <div 
      ref={setNodeRef} 
      style={style} 
      {...attributes} 
      {...listeners}
      className="touch-none"
    >
      <TicketCard ticket={ticket} users={users} isMentioned={isMentioned} onClick={onClick} isDragging={isDragging} />
    </div>
  );
};

export default SortableTicketCard;
