import React, { useState, useEffect, useImperativeHandle, forwardRef } from 'react';
import { Script } from '../types/readableBackendTypes';

interface TextWorkflowScriptEditorProps {
  script: Script;
  title: string;
  onScriptChange: (script: Script) => void;
  onTitleChange: (title: string) => void;
  onSave: (scriptToSave: Script) => void;
  onDirtyStateChange?: (isDirty: boolean) => void;
  isSaving: boolean;
}

export interface TextWorkflowScriptEditorRef {
  saveChanges: () => void;
}

interface RowEditData {
  rowIndex: number;
  speaker: string;
  text: string;
  hasAudioGenerated: boolean;
}

const TextWorkflowScriptEditor = forwardRef<
  TextWorkflowScriptEditorRef,
  TextWorkflowScriptEditorProps
>(({ script, title, onScriptChange, onTitleChange, onSave, onDirtyStateChange, isSaving }, ref) => {
  const [editData, setEditData] = useState<RowEditData[]>([]);
  const [originalData, setOriginalData] = useState<RowEditData[]>([]);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Expose save function to parent via ref
  useImperativeHandle(ref, () => ({
    saveChanges: handleSaveChanges,
  }));

  // Initialize edit data from script
  useEffect(() => {
    const initializeEditData = () => {
      const newEditData: RowEditData[] = script.history_grid.grid.map((row, rowIndex) => {
        const currentCell = row.cells[row.current_index] || {
          speakers: [''],
          texts: [''],
          generated_filepath: '',
        };

        return {
          rowIndex,
          speaker: currentCell.speakers[0] || '',
          text: currentCell.texts[0] || '',
          hasAudioGenerated: !!currentCell.generated_filepath,
        };
      });

      setEditData(newEditData);
      setOriginalData(newEditData); // Store original data for comparison
      setHasUnsavedChanges(false);
    };

    initializeEditData();
  }, [script]);

  // Helper function to check if a row is dirty (has unsaved changes)
  const isRowDirty = (rowIndex: number): boolean => {
    const current = editData.find(ed => ed.rowIndex === rowIndex);
    const original = originalData.find(od => od.rowIndex === rowIndex);

    if (!current || !original) return false;

    return current.speaker !== original.speaker || current.text !== original.text;
  };

  // Notify parent of dirty state changes
  useEffect(() => {
    if (onDirtyStateChange) {
      onDirtyStateChange(hasUnsavedChanges);
    }
  }, [hasUnsavedChanges, onDirtyStateChange]);

  const handleSpeakerChange = (rowIndex: number, newSpeaker: string) => {
    setEditData(prev =>
      prev.map(row => (row.rowIndex === rowIndex ? { ...row, speaker: newSpeaker } : row))
    );
    setHasUnsavedChanges(true);
  };

  const handleTextChange = (rowIndex: number, newText: string) => {
    setEditData(prev =>
      prev.map(row => (row.rowIndex === rowIndex ? { ...row, text: newText } : row))
    );
    setHasUnsavedChanges(true);
  };

  const handleSaveChanges = () => {
    // Create a deep copy of the script
    const updatedScript: Script = {
      ...script,
      title: title,
      history_grid: {
        ...script.history_grid,
        grid: script.history_grid.grid.map((row, rowIndex) => {
          const editRow = editData.find(ed => ed.rowIndex === rowIndex);
          if (!editRow) return row;

          const currentCell = row.cells[row.current_index];
          const hasExistingAudio = currentCell?.generated_filepath;

          if (hasExistingAudio) {
            // Create new cell and update current_index
            const newCell = {
              hide: false,
              height: 100,
              texts: [editRow.text],
              speakers: [editRow.speaker],
              actors: currentCell?.actors || [''],
              voice_mode: currentCell?.voice_mode || '',
              generated_filepath: '', // New cell has no audio generated yet
              waveform_data: [],
            };

            return {
              ...row,
              cells: [...row.cells, newCell],
              current_index: row.cells.length, // Point to the new cell
            };
          } else {
            // Update existing cell
            const updatedCells = row.cells.map((cell, cellIndex) => {
              if (cellIndex === row.current_index) {
                return {
                  ...cell,
                  texts: [editRow.text],
                  speakers: [editRow.speaker],
                };
              }
              return cell;
            });

            return {
              ...row,
              cells: updatedCells,
            };
          }
        }),
      },
    };

    onScriptChange(updatedScript);
    setHasUnsavedChanges(false);
    onSave(updatedScript);
  };

  return (
    <div className="script-editor">
      {/* Title Section */}
      <div className="script-title-section">
        <label className="script-title-label">
          Script Title (different from the file name):
          <input
            type="text"
            value={title}
            onChange={e => onTitleChange(e.target.value)}
            placeholder="Enter script title..."
            className="script-title-input"
          />
        </label>
      </div>

      {/* Script Info */}
      <div className="script-info">
        <p>Total rows: {script.history_grid.grid.length}</p>
        <p>Speakers: {Object.keys(script.speaker_to_actor_map).join(', ') || 'None defined'}</p>
      </div>

      {/* Grid Editor */}
      <div className="grid-editor">
        <div className="grid-header">
          <div>Row</div>
          <div>Speaker</div>
          <div>Text</div>
          <div>Audio Status</div>
        </div>

        {editData.map(rowData => (
          <div key={rowData.rowIndex} className="grid-row">
            {/* Row Index */}
            <div className="row-index">{rowData.rowIndex + 1}</div>

            {/* Speaker Input */}
            <input
              type="text"
              value={rowData.speaker}
              onChange={e => handleSpeakerChange(rowData.rowIndex, e.target.value)}
              placeholder="Speaker"
              className="speaker-input"
            />

            {/* Text Input */}
            <textarea
              value={rowData.text}
              onChange={e => handleTextChange(rowData.rowIndex, e.target.value)}
              placeholder="Enter text..."
              rows={8}
              className="text-input-editor"
            />

            {/* Audio Status */}
            <div className="audio-status">
              {(() => {
                const isDirty = isRowDirty(rowData.rowIndex);

                if (rowData.hasAudioGenerated && isDirty) {
                  return <span className="status-warning">⚠ New cell will be created</span>;
                } else if (rowData.hasAudioGenerated) {
                  return <span className="status-success">✓ Generated</span>;
                } else {
                  return <span className="status-error">✗ Not Generated</span>;
                }
              })()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

export default TextWorkflowScriptEditor;
