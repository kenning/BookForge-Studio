import React, { useState } from 'react';
import { FileInfo, Script } from '../../types/readableBackendTypes';
import { textWorkflowsApi } from '../../api/api';

interface TextToPsssWorkflowProps {
  onScriptGenerated: (script: Script) => void;
  onError: (error: string) => void;
  isWorkflowRunning?: boolean;
  startWorkflow?: (workflowCall: () => Promise<{ execution_id: string }>) => Promise<void>;
  onTextFileDrop?: (file: FileInfo) => void;
}

const TextToPsssWorkflow: React.FC<TextToPsssWorkflowProps> = ({
  onScriptGenerated,
  onError,
  isWorkflowRunning = false,
  startWorkflow,
  // onTextFileDrop,
}) => {
  const [textInput, setTextInput] = useState<string>('');

  const handleProcessText = async () => {
    if (!textInput.trim()) {
      onError('Please enter some text first');
      return;
    }

    if (!startWorkflow) {
      onError('Workflow handler not available');
      return;
    }

    try {
      onError(''); // Clear previous errors

      await startWorkflow(() =>
        textWorkflowsApi.textToPsss({
          text: textInput,
        })
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to process text';
      onError(errorMessage);
    }
  };

  return (
    <div className="workflow-content">
      <div className="workflow-input">
        <div className="text-input-section">
          <textarea
            value={textInput}
            onChange={e => setTextInput(e.target.value)}
            placeholder="Narrator: It is a truth universally acknowledged...&#10;Mrs. Bennet: My dear Mr. Bennet,&#10;Narrator: said his lady to him one day,&#10;Mrs. Bennet: have you heard that Netherfield Park is let at last?"
            className="text-input"
            rows={8}
          />
        </div>

        <button
          onClick={handleProcessText}
          disabled={!textInput.trim() || isWorkflowRunning}
          className="process-btn"
        >
          {isWorkflowRunning ? 'Processing...' : 'Process Text'}
        </button>
      </div>
    </div>
  );
};

export default TextToPsssWorkflow;
