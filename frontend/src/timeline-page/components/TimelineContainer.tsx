import React from 'react';
import { FileInfo } from '../../types/readableBackendTypes';
import TimelineCell from './TimelineCell';
import AddCellButton from './AddCellButton';
import NewDialogueButton from './NewDialogueButton';
import {
  getGradientStyle,
  getMultiSpeakerInfo,
  isRowCoveredByMultiSpeaker,
  calculateSelectedCellsCenter,
  areSelectedCellsConsecutive,
  CELL_WIDTH,
  ROW_HEIGHT,
} from '../utils/timelineUtils';
import { useTimelineGenerationStore } from '../store/timelineGenerationStore';

interface TimelineContainerProps {
  selectedCells: Set<string>;
  actors: FileInfo[];
  voiceModes: FileInfo[];
  onCellToggleCheckbox: (rowIndex: number, cellIndex: number) => void;
  onAddCell: (rowIndex: number) => void;
  onAddDialogueCell: (rowIndex: number) => void;
  onCreateDialogue: () => void;
}

const TimelineContainer: React.FC<TimelineContainerProps> = ({
  selectedCells,
  actors,
  voiceModes,
  onCellToggleCheckbox,
  onAddCell,
  onAddDialogueCell,
  onCreateDialogue,
}) => {
  const { script } = useTimelineGenerationStore();
  if (!script) return null;
  const multiSpeakerCells = getMultiSpeakerInfo(script.history_grid.grid);
  const gradientStyle = getGradientStyle();

  return (
    <div className="timeline-grid" style={{ position: 'relative' }}>
      {script.history_grid.grid.map((row, rowIndex) => {
        return (
          <div key={rowIndex} className="timeline-row">
            <div className="timeline-track" style={gradientStyle}>
              <div className="cells-container" style={{ position: 'relative' }}>
                {row.cells.map((cell, cellIndex) => {
                  const cellKey = `${rowIndex}-${cellIndex}`;
                  const isActive = cellIndex === row.current_index;
                  const isSelected = selectedCells.has(cellKey);

                  // Skip rendering if this position is covered by a multi-speaker cell from a previous row
                  if (isRowCoveredByMultiSpeaker(multiSpeakerCells, rowIndex, cellIndex)) {
                    return (
                      <div
                        key={cellIndex}
                        className="timeline-cell-placeholder"
                        style={{ width: CELL_WIDTH, height: ROW_HEIGHT - 20 }}
                      />
                    );
                  }

                  return (
                    <TimelineCell
                      key={cellIndex}
                      cell={cell}
                      isActive={isActive}
                      isSelected={isSelected}
                      onToggleCheckbox={() => onCellToggleCheckbox(rowIndex, cellIndex)}
                      rowIndex={rowIndex}
                      cellIndex={cellIndex}
                      currentIndex={row.current_index}
                      height={cell.height}
                      actors={actors}
                      voiceModes={voiceModes}
                    />
                  );
                })}
              </div>
            </div>
          </div>
        );
      })}

      {/* Render "+ New" buttons for multi-speaker cells */}
      {Array.from(multiSpeakerCells.entries()).map(([cellKey, msInfo]) => {
        const [startRowStr] = cellKey.split('-');
        const startRow = parseInt(startRowStr);
        const currentRow = script.history_grid.grid[startRow];

        // Only show button if this multi-speaker cell is currently active
        if (currentRow.current_index !== msInfo.cellIndex) {
          return null;
        }

        const centerY = startRow * ROW_HEIGHT + (msInfo.height * ROW_HEIGHT) / 2;

        return (
          <AddCellButton
            key={`ms-button-${cellKey}`}
            rowIndex={startRow}
            onAddCell={onAddDialogueCell}
            isMultiSpeaker={true}
            style={{
              position: 'absolute',
              right: '20px',
              top: `${centerY}px`,
              transform: 'translateY(-50%)',
              zIndex: 20,
            }}
          />
        );
      })}

      {/* Regular "+ New" buttons for single-row cells */}
      {script.history_grid.grid.map((row, rowIndex) => {
        return (
          <AddCellButton
            key={`single-button-${rowIndex}`}
            rowIndex={rowIndex}
            onAddCell={onAddCell}
            style={{
              position: 'absolute',
              right: '20px',
              top: `${rowIndex * (ROW_HEIGHT - 2) + ROW_HEIGHT / 2}px`,
              transform: 'translateY(-50%)',
              zIndex: 10,
            }}
          />
        );
      })}

      {/* New Dialogue Button for selected cells */}
      {selectedCells.size > 1 &&
        areSelectedCellsConsecutive(selectedCells) &&
        (() => {
          const { centerY } = calculateSelectedCellsCenter(selectedCells);
          return (
            <NewDialogueButton
              selectedCells={selectedCells}
              onCreateDialogue={onCreateDialogue}
              style={{
                right: `30px`,
                top: `${centerY}px`,
                transform: 'translate(-50%, -50%)',
              }}
            />
          );
        })()}
    </div>
  );
};

export default TimelineContainer;
