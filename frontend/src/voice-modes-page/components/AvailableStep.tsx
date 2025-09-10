import React from 'react';
import { Step } from '../../types/readableBackendTypes';
import { getCategoryColor, getCategoryIcon } from '../utils/categoryUtils';

interface AvailableStepProps {
  step: Step;
  isDragging?: boolean;
}

const AvailableStep: React.FC<AvailableStepProps> = ({ step, isDragging }) => {
  return (
    <div className="available-step">
      <div
        className="step-header-minimal"
        style={{ backgroundColor: getCategoryColor(step.category) }}
      >
        <span className="step-icon">{getCategoryIcon(step.category)}</span>
        <span className="step-title">{step.display_name}</span>
      </div>
    </div>
  );
};

export default AvailableStep;
