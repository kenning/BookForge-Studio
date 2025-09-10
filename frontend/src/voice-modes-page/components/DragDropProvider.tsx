import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { v4 as uuidv4 } from 'uuid';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  DragOverEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
} from '@dnd-kit/core';
import { Step } from '../../types/readableBackendTypes';
import { ValidationError, WrappedStep } from '../types';
import { getCategoryIcon } from '../utils/categoryUtils';

interface DragDropState {
  activeId: string | null;
  activeItem: any;
  tempWorkflowItemId: string | null;
}

interface DragDropContextValue {
  state: DragDropState;
}

const DragDropContext = createContext<DragDropContextValue | null>(null);

export const useDragDropContext = () => {
  const context = useContext(DragDropContext);
  if (!context) {
    throw new Error('useDragDropContext must be used within a DragDropProvider');
  }
  return context;
};

interface DragDropProviderProps {
  children: React.ReactNode;
  availableSteps: Step[];
  currentWorkflow: WrappedStep[];
  validationErrors: ValidationError[];
  onSetCurrentWorkflow: (workflow: WrappedStep[]) => void;
  onReorderWorkflow: (oldIndex: number, newIndex: number) => void;
}

export const DragDropProvider: React.FC<DragDropProviderProps> = ({
  children,
  availableSteps,
  currentWorkflow,
  validationErrors,
  onSetCurrentWorkflow,
  onReorderWorkflow,
}) => {
  const [state, setState] = useState<DragDropState>({
    activeId: null,
    activeItem: null,
    tempWorkflowItemId: null,
  });

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  // Helper to find which container an item belongs to
  const findContainer = useCallback(
    (itemId: string): string | null => {
      // Check available steps
      if (availableSteps.some(step => `template-${step.name}` === itemId)) {
        return 'available';
      }

      // Check current workflow
      if (currentWorkflow.some(config => config.id === itemId)) {
        return 'workflow';
      }

      // Check if it's a container ID itself
      if (itemId === 'available' || itemId === 'workflow') {
        return itemId;
      }

      return null;
    },
    [availableSteps, currentWorkflow]
  );

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const { active } = event;
      const { id } = active;
      const data = active.data.current;

      setState(prev => ({
        ...prev,
        activeId: id.toString(),
        activeItem: data?.item || null,
      }));

      // If dragging a template item, create a temporary instance
      if (data?.item?.type === 'template') {
        const tempId = `temp-${uuidv4()}`;
        setState(prev => ({
          ...prev,
          tempWorkflowItemId: tempId,
        }));

        const step = data.item.data as Step;
        const parameterValues: Record<string, any> = {};
        if (step.parameters) {
          Object.entries(step.parameters).forEach(([key, paramDef]) => {
            parameterValues[key] = (paramDef as any).default;
          });
        }

        const newStepConfig: WrappedStep = {
          id: tempId,
          step: {
            ...step,
            parameters: parameterValues,
          },
        };

        const newWorkflow = [...currentWorkflow, newStepConfig];
        onSetCurrentWorkflow(newWorkflow);
      }
    },
    [currentWorkflow, onSetCurrentWorkflow]
  );

  const handleDragOver = useCallback(
    (event: DragOverEvent) => {
      const { active, over } = event;
      const activeId = active.id.toString();

      if (state.tempWorkflowItemId && activeId.startsWith('template-')) {
        if (!over) {
          // Remove temp item when not hovering over anything
          const newWorkflow = currentWorkflow.filter(s => s.id !== state.tempWorkflowItemId);
          onSetCurrentWorkflow(newWorkflow);
          return;
        }

        const overId = over.id.toString();
        const overContainer = findContainer(overId);

        if (overContainer !== 'workflow') {
          // Remove temp item when hovering over invalid container
          const newWorkflow = currentWorkflow.filter(s => s.id !== state.tempWorkflowItemId);
          onSetCurrentWorkflow(newWorkflow);
          return;
        }

        // Handle repositioning temp instances
        const currentTempIndex = currentWorkflow.findIndex(
          config => config.id === state.tempWorkflowItemId
        );

        if (currentTempIndex === -1) {
          // Temp item was removed, recreate it
          const data = active.data.current;
          if (data?.item) {
            const step = data.item.data as Step;
            const parameterValues: Record<string, any> = {};
            if (step.parameters) {
              Object.entries(step.parameters).forEach(([key, paramDef]) => {
                parameterValues[key] = (paramDef as any).default;
              });
            }

            const newStepConfig: WrappedStep = {
              id: state.tempWorkflowItemId,
              step: {
                ...step,
                parameters: parameterValues,
              },
            };

            const newWorkflow = [
              ...currentWorkflow.slice(0, currentWorkflow.length - 1),
              newStepConfig,
              currentWorkflow[currentWorkflow.length - 1],
            ];
            onSetCurrentWorkflow(newWorkflow);
          }
          return;
        }

        // Find target position
        let targetIndex;
        if (overId === 'workflow') {
          targetIndex = currentWorkflow.length - 1;
        } else {
          const overIndex = currentWorkflow.findIndex(config => config.id === overId);
          if (overIndex === -1) return;
          if (overId === state.tempWorkflowItemId) return;
          targetIndex = overIndex;
        }

        // Only move if position changed
        if (currentTempIndex !== targetIndex) {
          onReorderWorkflow(currentTempIndex, targetIndex);
        }
      }
    },
    [
      state.tempWorkflowItemId,
      currentWorkflow,
      onSetCurrentWorkflow,
      findContainer,
      onReorderWorkflow,
    ]
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      const activeId = active.id.toString();
      const data = active.data.current;

      // Reset state
      setState({
        activeId: null,
        activeItem: null,
        tempWorkflowItemId: null,
      });

      if (!over) {
        // Drag cancelled - clean up temp instances
        if (state.tempWorkflowItemId) {
          const newWorkflow = currentWorkflow.filter(s => s.id !== state.tempWorkflowItemId);
          onSetCurrentWorkflow(newWorkflow);
        }
        return;
      }

      const overId = over.id.toString();
      const activeContainer = findContainer(activeId);
      const overContainer = findContainer(overId);

      // Handle template instantiation completion
      if (data?.item?.type === 'template' && state.tempWorkflowItemId) {
        if (overContainer === 'workflow') {
          // Convert temp to permanent (assign real UUID)
          const tempIndex = currentWorkflow.findIndex(
            config => config.id === state.tempWorkflowItemId
          );
          if (tempIndex !== -1) {
            const newWorkflow = [...currentWorkflow];
            newWorkflow[tempIndex] = {
              ...newWorkflow[tempIndex],
              id: uuidv4(),
            };
            onSetCurrentWorkflow(newWorkflow);
          }
        } else {
          // Remove temp item if dropped somewhere invalid
          const newWorkflow = currentWorkflow.filter(s => s.id !== state.tempWorkflowItemId);
          onSetCurrentWorkflow(newWorkflow);
        }
        return;
      }

      // Handle instance movement/reordering
      if (data?.item?.type === 'instance' && activeContainer && overContainer) {
        if (activeContainer === overContainer && overContainer === 'workflow') {
          // Same container reordering
          const activeIndex = currentWorkflow.findIndex(config => config.id === activeId);
          const overIndex = currentWorkflow.findIndex(config => config.id === overId);

          if (activeIndex !== -1 && overIndex !== -1 && activeIndex !== overIndex) {
            onReorderWorkflow(activeIndex, overIndex);
          }
        } else if (activeContainer === 'workflow' && overContainer === 'available') {
          // Remove from workflow
          const newWorkflow = currentWorkflow.filter(s => s.id !== activeId);
          onSetCurrentWorkflow(newWorkflow);
        }
      }
    },
    [
      state.tempWorkflowItemId,
      currentWorkflow,
      onSetCurrentWorkflow,
      findContainer,
      onReorderWorkflow,
    ]
  );

  const renderDragOverlay = useCallback(() => {
    if (!state.activeItem) return null;

    const step =
      state.activeItem.type === 'template' ? state.activeItem.data : state.activeItem.data.step;
    return (
      <div className="drag-overlay">
        <span className="step-icon">{getCategoryIcon(step.category)}</span>
        <span className="step-title">{step.display_name}</span>
      </div>
    );
  }, [state.activeItem]);

  const contextValue = useMemo(
    () => ({
      state,
    }),
    [state]
  );

  return (
    <DragDropContext.Provider value={contextValue}>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        {children}
        <DragOverlay>{renderDragOverlay()}</DragOverlay>
      </DndContext>
    </DragDropContext.Provider>
  );
};
