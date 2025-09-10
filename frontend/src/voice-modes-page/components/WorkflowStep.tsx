import React from 'react';
import { ValidationError, WrappedStep } from '../types';
import { getCategoryColor, getCategoryIcon } from '../utils/categoryUtils';
import { useVoiceModesStore } from '../store/voiceModesStore';

interface WorkflowStepProps {
  stepConfig: WrappedStep;
  validationErrors: ValidationError[];
  isDragging?: boolean;
  isTemporary?: boolean;
  removable?: boolean;
}

const WorkflowStep: React.FC<WorkflowStepProps> = ({
  stepConfig,
  validationErrors,
  isDragging,
  isTemporary = false,
  removable = true,
}) => {
  const { updateStepParameter, setCurrentWorkflow, currentWorkflow, availableSteps } =
    useVoiceModesStore();
  const stepError = validationErrors.find(e => e.stepId === stepConfig.id);

  // Find the original step definition to get parameter schemas
  const originalStep = availableSteps.find(s => s.name === stepConfig.step.name);

  const renderParameterInput = (paramName: string, currentValue: any) => {
    // Get the parameter definition from the original step
    const paramDef = originalStep?.parameters?.[paramName] as any;

    if (!paramDef) {
      console.warn(
        `Parameter definition not found for ${paramName} in step ${stepConfig.step.name}`
      );
      return null;
    }
    const handleChange = (value: any) => {
      updateStepParameter(stepConfig.id, paramName, value);
    };

    const renderNumberInput = (isFloat: boolean) => {
      const parseFunction = isFloat ? parseFloat : parseInt;

      return (
        <input
          type="number"
          {...(isFloat && { step: '0.01' })}
          value={currentValue ?? paramDef.default ?? 0}
          {...(paramDef.min !== undefined && { min: paramDef.min })}
          {...(paramDef.max !== undefined && { max: paramDef.max })}
          onChange={e => {
            const value = e.target.value;
            if (value === '') {
              handleChange(0);
            } else {
              const parsed = parseFunction(value);
              if (!isNaN(parsed)) {
                handleChange(parsed);
              }
            }
          }}
          onBlur={e => {
            const value = e.target.value;
            if (value === '' || isNaN(parseFunction(value))) {
              const fallbackValue = paramDef.min ?? paramDef.default ?? 0;
              handleChange(fallbackValue);
            } else if (value < paramDef.min) {
              handleChange(paramDef.min);
            } else if (value > paramDef.max) {
              handleChange(paramDef.max);
            }
            console.log('onBlur', value, paramDef.min, paramDef.max);
          }}
          className="param-input"
        />
      );
    };

    switch (paramDef.type) {
      case 'bool':
        return (
          <input
            type="checkbox"
            checked={currentValue || false}
            onChange={e => handleChange(e.target.checked)}
            className="param-input"
          />
        );
      case 'int':
        return renderNumberInput(false);
      case 'float':
        return renderNumberInput(true);
      case 'str':
        if (paramDef.options) {
          return (
            <select
              value={currentValue || paramDef.default || ''}
              onChange={e => handleChange(e.target.value)}
              className="param-input"
            >
              {paramDef.options.map((option: string) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          );
        }
        return (
          <input
            type="text"
            value={currentValue || paramDef.default || ''}
            onChange={e => handleChange(e.target.value)}
            className="param-input"
          />
        );
      case 'string':
        return (
          <input
            type="text"
            value={Array.isArray(currentValue) ? currentValue.join(', ') : currentValue || ''}
            placeholder="Comma-separated"
            onChange={e => {
              const values = e.target.value
                .split(',')
                .map(v => v.trim())
                .filter(v => v);
              handleChange(values);
            }}
            className="param-input"
          />
        );
      default:
        return (
          <input
            type="text"
            value={currentValue || paramDef.default || ''}
            onChange={e => handleChange(e.target.value)}
            className="param-input"
          />
        );
    }
  };

  return (
    <div
      className={`workflow-step ${stepError ? 'error' : ''}`}
      style={{ opacity: isTemporary ? 0.5 : 1 }}
    >
      {/* Header */}
      <div style={{ display: 'flex', flexDirection: 'row', justifyContent: 'space-between' }}>
        <div
          className="step-header-draggable"
          style={{ backgroundColor: getCategoryColor(stepConfig.step.category) }}
        >
          <span className="step-icon">{getCategoryIcon(stepConfig.step.category)}</span>
          <span className="step-title">{stepConfig.step.display_name}</span>
          {removable && (
            <button
              className="remove-step"
              onClick={e => {
                e.stopPropagation();
                const newWorkflow = currentWorkflow.filter(s => s.id !== stepConfig.id);
                setCurrentWorkflow(newWorkflow);
              }}
            >
              ×
            </button>
          )}
        </div>

        {/* Parameters area */}
        {stepConfig.step.parameters && Object.keys(stepConfig.step.parameters).length > 0 && (
          <div className="step-parameters-compact" onClick={e => e.stopPropagation()}>
            {Object.entries(stepConfig.step.parameters).map(([paramName, paramDef]) => (
              <div key={paramName} className="param-row">
                <label className="param-label" title={paramName}>
                  {paramName}:
                </label>
                {renderParameterInput(paramName, paramDef)}
              </div>
            ))}
          </div>
        )}
      </div>

      {stepError && <div className="validation-error">{stepError.message}</div>}
    </div>
  );
};

export default WorkflowStep;
