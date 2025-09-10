import React, { useState, useEffect } from 'react';
import DropZone from '../../components/DropZone';
import { FileInfo, Script } from '../../types/readableBackendTypes';
import { textWorkflowsApi } from '../../api/api';

interface TextToOllamaWorkflowProps {
  onScriptGenerated: (script: Script) => void;
  onError: (error: string) => void;
  textDroppedFile?: FileInfo | null;
  onTextFileRemove?: () => void;
  onTextFileDrop?: (file: FileInfo) => void;
  isWorkflowRunning?: boolean;
  startWorkflow: (workflowCall: () => Promise<{ execution_id: string }>) => Promise<void>;
}

const TextToOllamaWorkflow: React.FC<TextToOllamaWorkflowProps> = ({
  onScriptGenerated,
  onError,
  textDroppedFile,
  onTextFileRemove,
  onTextFileDrop,
  isWorkflowRunning = false,
  startWorkflow,
}) => {
  const [ollamaUrl, setOllamaUrl] = useState<string>('');
  const [ollamaModel, setOllamaModel] = useState<string>('');
  const [ollamaTextInput, setOllamaTextInput] = useState<string>('');

  const handleRemoveTextFile = () => {
    if (onTextFileRemove) {
      onTextFileRemove();
    }
  };

  // Clear text input when file is dropped
  useEffect(() => {
    if (textDroppedFile && ollamaTextInput.trim()) {
      setOllamaTextInput('');
    }
  }, [textDroppedFile, ollamaTextInput]);

  const handleProcessOllamaApi = async () => {
    // Check if we have either a file or text input
    if (!textDroppedFile && !ollamaTextInput.trim()) {
      onError('Please either drop a text file or enter text in the textarea');
      return;
    }

    try {
      onError(''); // Clear previous errors

      // Build request parameters based on input method
      const parameters: any = {};

      // Add optional parameters if they have values
      if (ollamaUrl.trim()) {
        parameters.ollama_url = ollamaUrl.trim();
      }
      if (ollamaModel.trim()) {
        parameters.model_name = ollamaModel.trim();
      }

      // Use file path if available, otherwise use direct text
      if (textDroppedFile) {
        parameters.filepath = textDroppedFile.path;
      } else {
        parameters.text = ollamaTextInput;
      }

      await startWorkflow(() =>
        textWorkflowsApi.executeWorkflowBackground({
          workflow_name: 'text-to-script-via-ollama',
          parameters,
        })
      );
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to process text with Ollama API';
      onError(errorMessage);
    }
  };

  return (
    <div className="workflow-content">
      <div style={{ display: 'flex', flexDirection: 'row', gap: '10px' }}>
        <div className="workflow-input">
          <div style={{ display: 'flex', flexDirection: 'row', gap: '10px' }}>
            <div className="text-input-section">
              <label>
                Ollama URL:
                <input
                  type="text"
                  value={ollamaUrl}
                  onChange={e => setOllamaUrl(e.target.value)}
                  placeholder="(leave empty for default)"
                  className="api-url-input"
                />
              </label>
              <div className="info-text">
                <small>
                  URL of your local Ollama API endpoint (optional - uses default if empty)
                </small>
              </div>
            </div>

            <div className="text-input-section">
              <label>
                Model Name:
                <input
                  type="text"
                  value={ollamaModel}
                  onChange={e => setOllamaModel(e.target.value)}
                  placeholder="(leave empty for default)"
                  className="model-name-input"
                />
              </label>
              <div className="info-text">
                <small>Name of the model to use (must be installed in Ollama)</small>
              </div>
            </div>
          </div>

          <div className="input-styling-wrapper-section">
            <div className="text-input-section">
              <label>Text Input: </label>
              <textarea
                value={ollamaTextInput}
                onChange={e => {
                  setOllamaTextInput(e.target.value);
                  // Clear dropped file when user starts typing
                  if (e.target.value.trim() && textDroppedFile) {
                    handleRemoveTextFile();
                  }
                }}
                placeholder="Paste your text here"
                className="text-input"
                rows={6}
              />
            </div>

            <div className="text-input-section">
              <label>OR Drop a text file:</label>
              <DropZone
                id="text-drop"
                label="Drop text file here"
                acceptedTypes={['text']}
                droppedFile={textDroppedFile}
                onFileDrop={onTextFileDrop}
                onFileRemove={handleRemoveTextFile}
                className="text-drop-zone"
              />
              <div className="info-text">
                <small>You can either paste text OR drop a file above (not both)</small>
              </div>
            </div>
          </div>

          <button
            onClick={handleProcessOllamaApi}
            disabled={(!textDroppedFile && !ollamaTextInput.trim()) || isWorkflowRunning}
            className="process-btn"
          >
            {isWorkflowRunning ? 'Processing with Local LLM...' : 'Process Text with Ollama'}
          </button>
        </div>
        <div className="tips-section" style={{ width: '40%' }}>
          <h3>Tips</h3>
          <ul>
            <li>Make sure Ollama is running locally first!</li>
            <li>
              <strong>This creates a complete script ready for audio generation.</strong> The local
              LLM will convert your text into a structured script with speakers and dialogue.
            </li>
            <li>
              This uses your local Ollama installation, so it's completely private and free. You
              need to install Ollama and pull a model first (e.g.,{' '}
              <code>ollama pull deepseek-r1:32b</code>).
            </li>
            <li>
              Processing time depends on your hardware and model size. Larger models may be slower
              but produce better results.
            </li>
            <li>
              Don't drop a whole book in here. Try individual chapters or shorter segments. This
              will also make it easier for you to generate and edit audio for one chapter at a time.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default TextToOllamaWorkflow;
