import React, { useState, useMemo, useCallback } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  pointerWithin,
  rectIntersection,
  getFirstCollision,
  PointerSensor,
  useSensor,
  useSensors,
  MeasuringStrategy
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  horizontalListSortingStrategy
} from '@dnd-kit/sortable';
import KanbanColumn from './KanbanColumn';
import TicketCard from './TicketCard';

const COLUMNS = [
  { id: 'todo', title: 'To Do' },
  { id: 'in_progress', title: 'In Progress' },
  { id: 'waiting', title: 'Waiting on Customer' },
  { id: 'review', title: 'Review' },
  { id: 'resolved', title: 'Resolved' }
];

// Custom collision detection that works better for kanban boards
const customCollisionDetection = (args) => {
  // First, check if we're over a droppable column
  const pointerCollisions = pointerWithin(args);
  const intersectionCollisions = rectIntersection(args);
  
  // Combine and prioritize collisions
  const collisions = pointerCollisions.length > 0 ? pointerCollisions : intersectionCollisions;
  
  // Get first collision
  const firstCollision = getFirstCollision(collisions, 'id');
  
  if (firstCollision) {
    // If collision is with a column, return it
    if (COLUMNS.some(col => col.id === firstCollision)) {
      return [{ id: firstCollision }];
    }
    return collisions;
  }
  
  // Fall back to closest center
  return closestCenter(args);
};

const KanbanBoard = ({ tickets, users, onTicketClick, onDragEnd, onCreateTicket }) => {
  const [activeId, setActiveId] = useState(null);
  const [activeTicket, setActiveTicket] = useState(null);
  const [overId, setOverId] = useState(null);

  // Optimized sensor with lower activation distance for snappier feel
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5, // Lower distance for quicker activation
      },
    })
  );

  // Group tickets by status with memoization
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

  // Find which column contains a ticket or is the column itself
  const findContainer = useCallback((id) => {
    if (!id) return null;
    
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
  }, [ticketsByStatus]);

  const handleDragStart = useCallback((event) => {
    const { active } = event;
    setActiveId(active.id);
    setActiveTicket(tickets.find(t => t.id === active.id) || null);
  }, [tickets]);

  const handleDragOver = useCallback((event) => {
    const { over } = event;
    setOverId(over?.id || null);
  }, []);

  const handleDragEnd = useCallback((event) => {
    const { active, over } = event;
    
    setActiveId(null);
    setActiveTicket(null);
    setOverId(null);

    if (!over) return;

    const activeContainer = findContainer(active.id);
    let overContainer = findContainer(over.id);

    // If over.id is a column ID, use it directly
    if (COLUMNS.some(col => col.id === over.id)) {
      overContainer = over.id;
    }

    if (!activeContainer || !overContainer) return;

    // Get the ticket being moved
    const movedTicket = tickets.find(t => t.id === active.id);
    if (!movedTicket) return;

    // Calculate new order
    const overTickets = ticketsByStatus[overContainer] || [];
    let newOrder = 0;

    if (over.id === overContainer) {
      // Dropped on column itself - add to end
      newOrder = overTickets.length;
    } else {
      // Dropped on a ticket - find its position
      const overIndex = overTickets.findIndex(t => t.id === over.id);
      if (overIndex >= 0) {
        // Insert at the position of the target ticket
        newOrder = overIndex;
      } else {
        newOrder = overTickets.length;
      }
    }

    // Only trigger update if something changed
    if (activeContainer !== overContainer || active.id !== over.id) {
      onDragEnd(active.id, overContainer, newOrder);
    }
  }, [findContainer, tickets, ticketsByStatus, onDragEnd]);

  const handleDragCancel = useCallback(() => {
    setActiveId(null);
    setActiveTicket(null);
    setOverId(null);
  }, []);

  // Measuring configuration for better drop zone detection
  const measuringConfig = {
    droppable: {
      strategy: MeasuringStrategy.Always,
    },
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={customCollisionDetection}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
      measuring={measuringConfig}
    >
      <div className="relative h-[calc(100vh-64px)] overflow-x-auto overflow-y-hidden">
        <div className="flex h-full gap-4 px-6 pb-6 pt-4 min-w-max" data-testid="kanban-track">
          {COLUMNS.map((column, index) => (
            <KanbanColumn
              key={column.id}
              column={column}
              tickets={ticketsByStatus[column.id] || []}
              users={users}
              onTicketClick={onTicketClick}
              onCreateTicket={onCreateTicket}
              staggerIndex={index + 1}
              isOver={overId === column.id || findContainer(overId) === column.id}
              activeId={activeId}
            />
          ))}
        </div>
      </div>

      <DragOverlay
        dropAnimation={{
          duration: 200,
          easing: 'cubic-bezier(0.18, 0.67, 0.6, 1.22)',
        }}
      >
        {activeTicket && (
          <div className="transform rotate-2 scale-105 opacity-95">
            <TicketCard 
              ticket={activeTicket} 
              users={users} 
              onClick={() => {}} 
              isDragging 
            />
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
};

export default KanbanBoard;
