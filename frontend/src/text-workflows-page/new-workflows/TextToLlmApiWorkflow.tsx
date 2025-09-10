import React, { useState, useEffect } from 'react';
import DropZone from '../../components/DropZone';
import { FileInfo, Script } from '../../types/readableBackendTypes';
import { textWorkflowsApi } from '../../api/api';

interface TextToLlmApiWorkflowProps {
  onScriptGenerated: (script: Script) => void;
  onError: (error: string) => void;
  textDroppedFile?: FileInfo | null;
  onTextFileRemove?: () => void;
  onTextFileDrop?: (file: FileInfo) => void;
  isWorkflowRunning?: boolean;
  startWorkflow: (workflowCall: () => Promise<{ execution_id: string }>) => Promise<void>;
}

const TextToLlmApiWorkflow: React.FC<TextToLlmApiWorkflowProps> = ({
  onScriptGenerated,
  onError,
  textDroppedFile,
  onTextFileRemove,
  onTextFileDrop,
  isWorkflowRunning = false,
  startWorkflow,
}) => {
  const [apiKey, setApiKey] = useState<string>('');
  const [llmTextInput, setLlmTextInput] = useState<string>('');

  // Load API key from localStorage on component mount
  useEffect(() => {
    try {
      const storedApiKey = localStorage.getItem('gemini_api_key');
      if (storedApiKey) {
        // Decode from base64
        const decodedApiKey = atob(storedApiKey);
        setApiKey(decodedApiKey);
      }
    } catch (err) {
      console.warn('Failed to load stored API key:', err);
    }
  }, []);

  // Save API key to localStorage whenever it changes
  const handleApiKeyChange = (newApiKey: string) => {
    setApiKey(newApiKey);
    if (newApiKey.trim()) {
      try {
        // Encode to base64
        const encodedApiKey = btoa(newApiKey);
        localStorage.setItem('gemini_api_key', encodedApiKey);
      } catch (err) {
        console.warn('Failed to save API key:', err);
      }
    } else {
      localStorage.removeItem('gemini_api_key');
    }
  };

  const handleRemoveTextFile = () => {
    if (onTextFileRemove) {
      onTextFileRemove();
    }
  };

  // Clear text input when file is dropped
  useEffect(() => {
    if (textDroppedFile && llmTextInput.trim()) {
      setLlmTextInput('');
    }
  }, [textDroppedFile, llmTextInput]);

  const handleProcessLlmApi = async () => {
    // Check if we have either a file or text input
    if (!textDroppedFile && !llmTextInput.trim()) {
      onError('Please either drop a text file or enter text in the textarea');
      return;
    }

    if (!apiKey.trim()) {
      onError('Please enter your API key');
      return;
    }

    try {
      onError(''); // Clear previous errors

      await startWorkflow(() =>
        textWorkflowsApi.executeWorkflowBackground({
          workflow_name: 'text_to_llm_api',
          parameters: {
            filepath: textDroppedFile?.path,
            text: llmTextInput || undefined,
            api_key: apiKey,
          },
        })
      );
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to process text with LLM API';
      onError(errorMessage);
    }
  };

  return (
    <div className="workflow-content">
      <div style={{ display: 'flex', flexDirection: 'row', gap: '10px' }}>
        <div className="workflow-input">
          <div className="text-input-section">
            <label>
              API Key:
              <input
                type="password"
                value={apiKey}
                onChange={e => handleApiKeyChange(e.target.value)}
                placeholder="Enter your Gemini API key..."
                className="api-key-input"
              />
            </label>
            <div className="security-warning">
              <small>
                Caution: This web app saves your api key in your browser. This is insecure.
                <br />
                If you want to be more secure (and you know how to do it), pass in your api key as
                an environmental variable, "GEMINI_API_KEY".
              </small>
            </div>
          </div>

          <div className="input-styling-wrapper-section">
            <div className="text-input-section">
              <label>Text Input:</label>
              <textarea
                value={llmTextInput}
                onChange={e => {
                  setLlmTextInput(e.target.value);
                  // Clear dropped file when user starts typing
                  if (e.target.value.trim() && textDroppedFile) {
                    handleRemoveTextFile();
                  }
                }}
                placeholder="Paste your text here "
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
            onClick={handleProcessLlmApi}
            disabled={
              (!textDroppedFile && !llmTextInput.trim()) || !apiKey.trim() || isWorkflowRunning
            }
            className="process-btn"
          >
            {isWorkflowRunning ? 'Processing with AI...' : 'Process Text with AI'}
          </button>
        </div>
        <div className="tips-section" style={{ width: '40%' }}>
          <h3>Tips</h3>
          <ul>
            <li>This can take a while.</li>
            <li>
              <strong>This creates a complete script ready for audio generation.</strong> The AI
              will convert your text into a structured script with speakers and dialogue.
            </li>
            <li>
              This uses the Gemini API, which used to be free but isn't anymore. You can get an API
              key <a href="https://ai.google.dev/gemini-api/docs/quickstart">here</a>. Later this
              should support more platforms but basically we have found Gemini 2.5 Pro is very good
              and pretty cheap.
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

export default TextToLlmApiWorkflow;
