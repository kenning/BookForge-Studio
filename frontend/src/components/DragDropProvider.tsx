import React from 'react';
import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragStartEvent,
  MouseSensor,
  TouchSensor,
  useSensor,
  useSensors,
  DragOverlay,
} from '@dnd-kit/core';

interface DragDropProviderProps {
  children: React.ReactNode;
  onDragStart?: (event: DragStartEvent) => void;
  onDragOver?: (event: DragOverEvent) => void;
  onDragEnd?: (event: DragEndEvent) => void;
  renderDragOverlay?: (activeId: string | null, activeData: any) => React.ReactNode;
}

const DragDropProvider: React.FC<DragDropProviderProps> = ({
  children,
  onDragStart,
  onDragOver,
  onDragEnd,
  renderDragOverlay,
}) => {
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const [activeData, setActiveData] = React.useState<any>(null);

  const mouseSensor = useSensor(MouseSensor, {
    activationConstraint: {
      distance: 8,
    },
  });

  const touchSensor = useSensor(TouchSensor, {
    activationConstraint: {
      delay: 200,
      tolerance: 8,
    },
  });

  const sensors = useSensors(mouseSensor, touchSensor);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
    setActiveData(event.active.data.current);
    onDragStart?.(event);
  };

  const handleDragOver = (event: DragOverEvent) => {
    onDragOver?.(event);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveId(null);
    setActiveData(null);
    onDragEnd?.(event);
  };

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      {children}

      <DragOverlay>
        {renderDragOverlay ? (
          renderDragOverlay(activeId, activeData)
        ) : activeId ? (
          <div className="drag-overlay">
            <span>Dragging: {activeId}</span>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
};

export default DragDropProvider;
