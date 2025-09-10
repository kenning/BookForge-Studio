import React, { useState, useRef, useEffect } from 'react';
import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { ValidationError, WrappedStep } from '../types';
import WorkflowStep from './WorkflowStep';
import { useVoiceModesStore } from '../store/voiceModesStore';

interface SortableWorkflowStepProps {
  stepConfig: WrappedStep;
  validationErrors: ValidationError[];
  isDraggable: boolean;
}

const SortableWorkflowStep: React.FC<SortableWorkflowStepProps> = ({
  stepConfig,
  validationErrors,
  isDraggable,
}) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const { availableSteps } = useVoiceModesStore();

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: stepConfig.id,
    data: {
      item: {
        id: stepConfig.id,
        type: 'instance' as const,
        data: stepConfig,
      },
    },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const isTemporary = stepConfig.id.startsWith('temp-');

  const handleMouseEnter = () => {
    if (stepConfig.step.description) {
      hoverTimeoutRef.current = setTimeout(() => {
        setShowTooltip(true);
      }, 500);
    }
  };

  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    setShowTooltip(false);
  };

  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
    };
  }, []);

  const realStep = (
    <WorkflowStep
      stepConfig={stepConfig}
      validationErrors={validationErrors}
      isDragging={isDragging}
      isTemporary={isTemporary}
      removable={isDraggable}
    />
  );

  const tooltipMetadata = availableSteps.find(s => s.name === stepConfig.step.name);
  const realTooltip = tooltipMetadata ? (
    <div ref={tooltipRef} className="workflow-step-tooltip">
      {tooltipMetadata?.description}
      {tooltipMetadata?.parameters &&
        Object.entries(tooltipMetadata?.parameters || {}).length > 0 && (
          <ul>
            {Object.entries(tooltipMetadata?.parameters || {}).map(([paramName, paramDef]: any) => {
              return (
                <li key={paramName}>
                  <strong>{paramName}:</strong> {paramDef.description}
                </li>
              );
            })}
          </ul>
        )}
    </div>
  ) : null;

  const wrapperElement = (
    <div
      className="workflow-step-wrapper"
      ref={node => {
        setNodeRef(node);
        wrapperRef.current = node;
      }}
      style={style}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      {...(isDraggable ? listeners : {})}
      {...(isDraggable ? attributes : {})}
    >
      {realStep}
      {showTooltip && stepConfig.step.description && realTooltip}
    </div>
  );

  if (isDraggable) {
    return wrapperElement;
  } else {
    return (
      <div
        className="workflow-step-wrapper"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {realStep}
        {showTooltip && stepConfig.step.description && realTooltip}
      </div>
    );
  }
};

interface WorkflowContainerProps {
  currentWorkflow: WrappedStep[];
  validationErrors: ValidationError[];
}

const WorkflowContainer: React.FC<WorkflowContainerProps> = React.memo(
  ({ currentWorkflow, validationErrors }) => {
    const { setNodeRef } = useDroppable({ id: 'workflow' });

    return (
      <div className="drag-drop-container workflow-container">
        <div ref={setNodeRef} style={{ minHeight: '100px' }}>
          {currentWorkflow.length === 0 ? (
            <div className="empty-workflow">Drag steps here to build your workflow</div>
          ) : (
            <SortableContext
              items={currentWorkflow.map(config => config.id)}
              strategy={verticalListSortingStrategy}
            >
              {currentWorkflow.map((stepConfig, index) => (
                <SortableWorkflowStep
                  key={stepConfig.id}
                  isDraggable={index !== 0 && index !== currentWorkflow.length - 1}
                  stepConfig={stepConfig}
                  validationErrors={validationErrors}
                />
              ))}
            </SortableContext>
          )}
        </div>
      </div>
    );
  }
);

WorkflowContainer.displayName = 'WorkflowContainer';

export default WorkflowContainer;
