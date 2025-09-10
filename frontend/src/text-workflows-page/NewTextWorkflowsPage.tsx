import React, { useState, useEffect, useRef } from 'react';
import { FileInfo, Script } from '../types/readableBackendTypes';
import { webSocketService } from '../services/websocketService';
import TextToLlmApiWorkflow from './new-workflows/TextToLlmApiWorkflow';
import TextToOllamaWorkflow from './new-workflows/TextToOllamaWorkflow';
import CsvToPsssWorkflow from './new-workflows/CsvToPsssWorkflow';
import TextToPsssWorkflow from './new-workflows/TextToPsssWorkflow';

interface NewTextWorkflowsPageProps {
  onScriptGenerated: (script: Script) => void;
  onError: (error: string) => void;
  csvDroppedFile?: FileInfo | null;
  onCsvFileRemove?: () => void;
  textDroppedFile?: FileInfo | null;
  onTextFileRemove?: () => void;
  onCsvFileDrop?: (file: FileInfo) => void;
  onTextFileDrop?: (file: FileInfo) => void;
}

interface WorkflowProgress {
  stepNum: number;
  totalSteps: number;
  message: string;
  workflowName: string;
  executionId?: string;
}

type WorkflowType = 'text_to_llm_api' | 'text_to_ollama_api' | 'csv_to_psss' | 'text_to_psss';

const WORKFLOW_OPTIONS = [
  { value: 'text_to_llm_api', label: 'Make Script with LLM API (Gemini)' },
  { value: 'text_to_ollama_api', label: 'Make Script with Ollama (Local LLM)' },
  { value: 'csv_to_psss', label: 'Make Script from CSV' },
  { value: 'text_to_psss', label: 'Make Script from plain text (simple)' },
] as const;

const NewTextWorkflowsPage: React.FC<NewTextWorkflowsPageProps> = ({
  onScriptGenerated,
  onError,
  csvDroppedFile,
  onCsvFileRemove,
  textDroppedFile,
  onTextFileRemove,
  onCsvFileDrop,
  onTextFileDrop,
}) => {
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowType>('text_to_ollama_api');
  const [currentProgress, setCurrentProgress] = useState<WorkflowProgress | null>(null);
  const [isWorkflowRunning, setIsWorkflowRunning] = useState(false);

  // Not actually using execution id yet, it causes some bugs...
  const [, setCurrentExecutionId] = useState<string | null>(null);
  const currentExecutionIdRef = useRef<string | null>(null);

  // Set up WebSocket handlers for text workflow messages
  useEffect(() => {
    webSocketService.setHandlers({
      onTextWorkflowProgress: message => {
        console.log('onTextWorkflowProgress', message);
        // Only show progress for our current execution
        // if (message.execution_id === currentExecutionIdRef.current) {
        if (true) {
          setCurrentProgress({
            stepNum: message.step_num,
            totalSteps: message.total_steps,
            message: message.message,
            workflowName: message.workflow_name,
            executionId: message.execution_id,
          });
        }
      },
      onTextWorkflowComplete: message => {
        console.log('onTextWorkflowComplete', message);
        // Only handle completion for our current execution
        // if (message.execution_id === currentExecutionIdRef.current) {
        if (true) {
          setCurrentProgress(null);
          setIsWorkflowRunning(false);
          setCurrentExecutionId(null);
          currentExecutionIdRef.current = null;
          if (message.result && message.result.script) {
            onScriptGenerated(message.result.script);
          }
        }
      },
      onTextWorkflowError: message => {
        console.log('onTextWorkflowError', message);
        // Only handle errors for our current execution
        // if (message.execution_id === currentExecutionIdRef.current) {
        if (true) {
          setCurrentProgress(null);
          setIsWorkflowRunning(false);
          setCurrentExecutionId(null);
          currentExecutionIdRef.current = null;
          onError(`Workflow error: ${message.error}`);
        }
      },
    });

    return () => {
      // Clean up text workflow handlers when component unmounts
      webSocketService.clearHandlers([
        'onTextWorkflowProgress',
        'onTextWorkflowComplete',
        'onTextWorkflowError',
      ]);
    };
  }, [onScriptGenerated, onError]);

  // Function to start a workflow and track its execution
  const startWorkflow = async (workflowCall: () => Promise<{ execution_id: string }>) => {
    try {
      setIsWorkflowRunning(true);
      setCurrentProgress(null);

      const response = await workflowCall();
      setCurrentExecutionId(response.execution_id);
      currentExecutionIdRef.current = response.execution_id;
      console.log('Started workflow with execution ID:', response.execution_id);
    } catch (error) {
      setIsWorkflowRunning(false);
      setCurrentExecutionId(null);
      currentExecutionIdRef.current = null;
      const errorMessage = error instanceof Error ? error.message : 'Failed to start workflow';
      onError(errorMessage);
    }
  };

  const renderProgressBar = () => {
    if (!currentProgress) return null;

    const progressPercentage = (currentProgress.stepNum / currentProgress.totalSteps) * 100;

    return (
      <div className="workflow-progress-container">
        <div className="progress-info">
          <span className="progress-message">
            {currentProgress.message.length > 500
              ? `${currentProgress.message.substring(0, 500)}...`
              : currentProgress.message}
          </span>
          <span className="progress-steps">
            Step {currentProgress.stepNum} of {currentProgress.totalSteps}
          </span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progressPercentage}%` }} />
        </div>
      </div>
    );
  };

  const renderSelectedWorkflow = () => {
    const workflowProps = {
      onScriptGenerated,
      onError,
      isWorkflowRunning,
      startWorkflow,
    };

    switch (selectedWorkflow) {
      case 'text_to_llm_api':
        return (
          <TextToLlmApiWorkflow
            {...workflowProps}
            textDroppedFile={textDroppedFile}
            onTextFileRemove={onTextFileRemove}
            onTextFileDrop={onTextFileDrop}
          />
        );
      case 'text_to_ollama_api':
        return (
          <TextToOllamaWorkflow
            {...workflowProps}
            textDroppedFile={textDroppedFile}
            onTextFileRemove={onTextFileRemove}
            onTextFileDrop={onTextFileDrop}
          />
        );
      case 'csv_to_psss':
        return (
          <CsvToPsssWorkflow
            {...workflowProps}
            csvDroppedFile={csvDroppedFile}
            onCsvFileRemove={onCsvFileRemove}
            onCsvFileDrop={onCsvFileDrop}
          />
        );
      case 'text_to_psss':
        return <TextToPsssWorkflow {...workflowProps} onTextFileDrop={onTextFileDrop} />;
      default:
        return null;
    }
  };

  return (
    <div className="workflows-main">
      <div className="workflow-selector-section">
        <h2>{WORKFLOW_OPTIONS.find(option => option.value === selectedWorkflow)?.label}</h2>
        <label>
          Workflow:
          <select
            value={selectedWorkflow}
            onChange={e => setSelectedWorkflow(e.target.value as WorkflowType)}
            className="workflow-selector"
            disabled={isWorkflowRunning}
          >
            {WORKFLOW_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {renderProgressBar()}

      {renderSelectedWorkflow()}
    </div>
  );
};

export default NewTextWorkflowsPage;
