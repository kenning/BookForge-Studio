import React from 'react';
import { useDraggable, useDroppable } from '@dnd-kit/core';
import { Step } from '../../types/readableBackendTypes';
import AvailableStep from './AvailableStep';

interface DraggableStepProps {
  step: Step;
}

const DraggableStep: React.FC<DraggableStepProps> = ({ step }) => {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `template-${step.name}`,
    data: {
      item: {
        id: `template-${step.name}`,
        type: 'template' as const,
        data: step,
      },
    },
  });

  const style: any = {
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes}>
      <AvailableStep step={step} isDragging={isDragging} />
    </div>
  );
};

interface AvailableStepsContainerProps {
  availableSteps: Step[];
}

const AvailableStepsContainer: React.FC<AvailableStepsContainerProps> = React.memo(
  ({ availableSteps }) => {
    const { setNodeRef } = useDroppable({ id: 'available' });

    return (
      <div className="drag-drop-container available-steps-container">
        <h3>Available Steps</h3>
        <div ref={setNodeRef} style={{ minHeight: '100px', overflowX: 'hidden' }}>
          {availableSteps.length === 0 ? (
            <div className="available-steps-placeholder">Available steps will appear here</div>
          ) : (
            availableSteps.map(step => <DraggableStep key={step.name} step={step} />)
          )}
        </div>
      </div>
    );
  }
);

AvailableStepsContainer.displayName = 'AvailableStepsContainer';

export default AvailableStepsContainer;
