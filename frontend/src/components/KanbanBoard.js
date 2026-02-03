import React, { useState, useMemo, useCallback, useRef } from 'react';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  MeasuringStrategy,
  pointerWithin,
  rectIntersection
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy
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

const KanbanBoard = ({ tickets, users, currentUserId, onTicketClick, onDragEnd, onCreateTicket }) => {
  const [activeId, setActiveId] = useState(null);
  const [activeTicket, setActiveTicket] = useState(null);
  const lastOverId = useRef(null);

  // Single optimized sensor - minimal activation distance
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 3,
      },
    })
  );

  // Check if ticket has a mention for current user (but not assigned to them)
  const isMentionedTicket = useCallback((ticket) => {
    if (!currentUserId) return false;
    const isMentioned = Array.isArray(ticket.mentioned_users) && 
                        ticket.mentioned_users.includes(currentUserId);
    const isAssigned = ticket.assignee_id === currentUserId;
    return isMentioned && !isAssigned;
  }, [currentUserId]);

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

    Object.keys(grouped).forEach(status => {
      grouped[status].sort((a, b) => (a.order || 0) - (b.order || 0));
    });

    return grouped;
  }, [tickets]);

  const findContainer = useCallback((id) => {
    if (!id) return null;
    if (COLUMNS.some(col => col.id === id)) return id;
    
    for (const [status, ticketList] of Object.entries(ticketsByStatus)) {
      if (ticketList.some(ticket => ticket.id === id)) {
        return status;
      }
    }
    return null;
  }, [ticketsByStatus]);

  // Simple collision detection
  const collisionDetection = useCallback((args) => {
    const pointerCollisions = pointerWithin(args);
    if (pointerCollisions.length > 0) return pointerCollisions;
    return rectIntersection(args);
  }, []);

  const handleDragStart = useCallback((event) => {
    const { active } = event;
    const ticket = tickets.find(t => t.id === active.id);
    setActiveId(active.id);
    setActiveTicket(ticket || null);
    lastOverId.current = null;
  }, [tickets]);

  const handleDragEnd = useCallback((event) => {
    const { active, over } = event;
    
    setActiveId(null);
    setActiveTicket(null);

    if (!over) return;

    const activeContainer = findContainer(active.id);
    let overContainer = COLUMNS.some(col => col.id === over.id) ? over.id : findContainer(over.id);

    if (!activeContainer || !overContainer) return;

    const overTickets = ticketsByStatus[overContainer] || [];
    let newOrder = overTickets.length;

    if (over.id !== overContainer) {
      const overIndex = overTickets.findIndex(t => t.id === over.id);
      if (overIndex >= 0) newOrder = overIndex;
    }

    if (activeContainer !== overContainer || active.id !== over.id) {
      onDragEnd(active.id, overContainer, newOrder);
    }
  }, [findContainer, ticketsByStatus, onDragEnd]);

  const handleDragCancel = useCallback(() => {
    setActiveId(null);
    setActiveTicket(null);
  }, []);

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={collisionDetection}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
      measuring={{ droppable: { strategy: MeasuringStrategy.Always } }}
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
              activeId={activeId}
            />
          ))}
        </div>
      </div>

      <DragOverlay dropAnimation={null}>
        {activeTicket && (
          <div style={{ transform: 'rotate(3deg)', opacity: 0.9 }}>
            <TicketCard 
              ticket={activeTicket} 
              users={users} 
              isMentioned={isMentionedTicket(activeTicket)}
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
