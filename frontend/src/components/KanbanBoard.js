import React, { useState, useMemo } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
  MouseSensor,
  TouchSensor
} from '@dnd-kit/core';
import KanbanColumn from './KanbanColumn';
import TicketCard from './TicketCard';

const COLUMNS = [
  { id: 'todo', title: 'To Do' },
  { id: 'in_progress', title: 'In Progress' },
  { id: 'waiting', title: 'Waiting on Customer' },
  { id: 'review', title: 'Review' },
  { id: 'resolved', title: 'Resolved' }
];

const KanbanBoard = ({ tickets, users, onTicketClick, onDragEnd, onCreateTicket }) => {
  const [activeId, setActiveId] = useState(null);
  const [activeTicket, setActiveTicket] = useState(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(MouseSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(TouchSensor, {
      activationConstraint: {
        delay: 200,
        tolerance: 5,
      },
    })
  );

  // Group tickets by status
  const ticketsByStatus = useMemo(() => {
    const grouped = {
      todo: [],
      in_progress: [],
      waiting: [],
      review: [],
      resolved: []
    };

    tickets.forEach(ticket => {
      if (grouped[ticket.status]) {
        grouped[ticket.status].push(ticket);
      }
    });

    // Sort by order
    Object.keys(grouped).forEach(status => {
      grouped[status].sort((a, b) => (a.order || 0) - (b.order || 0));
    });

    return grouped;
  }, [tickets]);

  const findContainer = (id) => {
    // Check if id is a column
    if (COLUMNS.some(col => col.id === id)) {
      return id;
    }

    // Find which column contains this ticket
    for (const [status, ticketList] of Object.entries(ticketsByStatus)) {
      if (ticketList.some(ticket => ticket.id === id)) {
        return status;
      }
    }
    return null;
  };

  const handleDragStart = (event) => {
    const { active } = event;
    setActiveId(active.id);

    // Find the active ticket
    const ticket = tickets.find(t => t.id === active.id);
    setActiveTicket(ticket);
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    
    setActiveId(null);
    setActiveTicket(null);

    if (!over) return;

    const activeContainer = findContainer(active.id);
    const overContainer = findContainer(over.id);

    if (!activeContainer || !overContainer) return;

    // Get the ticket being moved
    const activeTicket = tickets.find(t => t.id === active.id);
    if (!activeTicket) return;

    // If dropped on a column or different ticket
    if (activeContainer !== overContainer || active.id !== over.id) {
      const overTickets = ticketsByStatus[overContainer];
      let newOrder = 0;

      if (over.id === overContainer) {
        // Dropped on column itself - add to end
        newOrder = overTickets.length;
      } else {
        // Dropped on a ticket - find its position
        const overIndex = overTickets.findIndex(t => t.id === over.id);
        newOrder = overIndex >= 0 ? overIndex : overTickets.length;
      }

      // Call the backend to update
      onDragEnd(active.id, overContainer, newOrder);
    }
  };

  const handleDragCancel = () => {
    setActiveId(null);
    setActiveTicket(null);
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <div className="relative h-[calc(100vh-64px)] overflow-x-auto overflow-y-hidden">
        <div className="flex h-full gap-4 px-4 pb-6 pt-4" data-testid="kanban-track">
          {COLUMNS.map((column, index) => (
            <KanbanColumn
              key={column.id}
              column={column}
              tickets={ticketsByStatus[column.id] || []}
              users={users}
              onTicketClick={onTicketClick}
              onCreateTicket={onCreateTicket}
              staggerIndex={index + 1}
            />
          ))}
        </div>
      </div>

      <DragOverlay>
        {activeTicket && (
          <div className="rotate-3 scale-105">
            <TicketCard ticket={activeTicket} users={users} onClick={() => {}} isDragging />
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
};

export default KanbanBoard;
