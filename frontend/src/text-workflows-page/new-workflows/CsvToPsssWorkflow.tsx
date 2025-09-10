import React, { useEffect } from 'react';
import DropZone from '../../components/DropZone';
import { FileInfo, Script } from '../../types/readableBackendTypes';
import { textWorkflowsApi } from '../../api/api';

interface CsvToPsssWorkflowProps {
  onScriptGenerated: (script: Script) => void;
  onError: (error: string) => void;
  csvDroppedFile?: FileInfo | null;
  onCsvFileRemove?: () => void;
  onCsvFileDrop?: (file: FileInfo) => void;
  isWorkflowRunning?: boolean;
  startWorkflow?: (workflowCall: () => Promise<{ execution_id: string }>) => Promise<void>;
}

const CsvToPsssWorkflow: React.FC<CsvToPsssWorkflowProps> = ({
  onScriptGenerated,
  onError,
  csvDroppedFile,
  onCsvFileRemove,
  onCsvFileDrop,
  isWorkflowRunning = false,
  startWorkflow,
}) => {
  const handleRemoveCsvFile = () => {
    if (onCsvFileRemove) {
      onCsvFileRemove();
    }
  };

  // Auto-process CSV when file is dropped
  useEffect(() => {
    const handleProcessCsv = async () => {
      if (!csvDroppedFile) {
        onError('Please drop a CSV file first');
        return;
      }

      if (!startWorkflow) {
        onError('Workflow handler not available');
        return;
      }

      try {
        onError(''); // Clear previous errors

        await startWorkflow(() =>
          textWorkflowsApi.csvToPsss({
            filepath: csvDroppedFile.path,
          })
        );
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to process CSV';
        onError(errorMessage);
      }
    };
    if (csvDroppedFile && !isWorkflowRunning) {
      handleProcessCsv();
    }
  }, [csvDroppedFile, isWorkflowRunning, onError, startWorkflow]);

  return (
    <div className="workflow-content">
      <div className="workflow-input">
        <DropZone
          id="csv-drop"
          label="Drop CSV file here"
          acceptedTypes={['text']}
          droppedFile={csvDroppedFile}
          onFileRemove={handleRemoveCsvFile}
          onFileDrop={onCsvFileDrop}
          className="csv-drop-zone"
        />
        {isWorkflowRunning && <div className="processing-indicator">Processing CSV file...</div>}
      </div>
      <div className="tips-section" style={{ width: '40%' }}>
        <h3>Tips</h3>
        <p style={{ marginTop: 0 }}>
          This workflow will make a script from a CSV file. Drag a CSV file from the "Input Files"
          section in the lower left.
        </p>
        <p>The CSV file should have the following columns:</p>
        <ul>
          <li>Speaker</li>
          <li>Text</li>
        </ul>
        <p>The script will be saved as a JSON file.</p>
      </div>
    </div>
  );
};

export default CsvToPsssWorkflow;
