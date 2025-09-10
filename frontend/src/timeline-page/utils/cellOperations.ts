import { Script, ScriptHistoryGridCell } from '../../types/readableBackendTypes';
import { makeHiddenCell, newPointerCell } from './timelineUtils';

// Create a dialogue cell from multiple selected cells
export const createDialogueCellFromSelection = (
  script: Script,
  selectedCells: Set<string>
): Script => {
  // Find the first selected row to use as the starting row for the dialogue
  const selectedCellKeys = Array.from(selectedCells);
  const firstCellKey = selectedCellKeys[0];
  const [startRowIndex] = firstCellKey.split('-').map(Number);

  // Get all selected cells data
  const selectedCellsData: ScriptHistoryGridCell[] = [];
  selectedCellKeys.forEach(cellKey => {
    const [rowIndex, cellIndex] = cellKey.split('-').map(Number);
    const cell = script.history_grid.grid[rowIndex]?.cells[cellIndex];
    if (cell) {
      selectedCellsData.push(cell);
    }
  });

  if (selectedCellsData.length === 0) {
    return script; // No valid cells selected
  }

  // Combine data from selected cells
  const combinedTexts = ['Multiple speaker Cell: Text'];
  const combinedSpeakers: string[] = [];
  const combinedActors: string[] = [];

  selectedCellsData.forEach(cell => {
    combinedTexts.push(...cell.texts);
    combinedSpeakers.push(...cell.speakers);
    combinedActors.push(...cell.actors);
  });

  // Calculate height based on number of speakers or texts
  const calculatedHeight = Math.max(selectedCellsData.length, 2);

  const dialogueCell: ScriptHistoryGridCell = {
    hide: false,
    height: calculatedHeight,
    texts: combinedTexts,
    speakers: combinedSpeakers,
    actors: combinedActors,
    voice_mode: selectedCellsData[0].voice_mode,
    generated_filepath: '',
    waveform_data: [],
  };

  // Update all affected rows
  const affectedRows = Array.from({ length: calculatedHeight }, (_, i) => startRowIndex + i);

  return {
    ...script,
    history_grid: {
      ...script.history_grid,
      grid: script.history_grid.grid.map((row, i) => {
        if (affectedRows.includes(i)) {
          const newCells = [...row.cells];

          if (i === startRowIndex) {
            // First row gets the actual dialogue cell
            newCells.push(dialogueCell);
          } else {
            // Subsequent rows get placeholder cells
            newCells.push(makeHiddenCell(row));
          }

          return {
            ...row,
            cells: newCells,
            current_index: newCells.length - 1,
          };
        }
        return row;
      }),
    },
  };
};

export const handleCellSelection = (
  script: Script,
  rowIndex: number,
  cellIndex: number
): Script | null => {
  // Check if the selected cell is a multi-speaker cell or part of one,
  // or if the current cell being selected is part of a multi-speaker cell
  const row = script.history_grid.grid[rowIndex];
  if (row.current_index === cellIndex) {
    return null;
  }
  const currentRowCell = row.cells[row.current_index];
  const clickedCell = row.cells[cellIndex];
  let affectedRows = [rowIndex];

  if (clickedCell && clickedCell.height > 1) {
    // If the selected cell is a multi-speaker cell, affect all rows it covers
    affectedRows = Array.from({ length: clickedCell.height }, (_, i) => rowIndex + i);
  } else if (currentRowCell && currentRowCell.height > 1) {
    // If the current cell is part of a multi-speaker cell, affect all rows it covers
    affectedRows = Array.from({ length: currentRowCell.height }, (_, i) => rowIndex + i);
  } else if (currentRowCell && currentRowCell.hide) {
    return script;
  } else {
    // Check if this cell position is covered by a multi-speaker cell from a previous row
    for (let checkRow = 0; checkRow < rowIndex; checkRow++) {
      const checkRowData = script.history_grid.grid[checkRow];
      const checkCell = checkRowData.cells[cellIndex];

      if (checkCell && checkCell.height > 1 && !checkCell.hide) {
        const coverageEnd = checkRow + checkCell.height;
        if (rowIndex < coverageEnd) {
          // This cell is part of a multi-speaker cell, update all covered rows
          affectedRows = Array.from({ length: checkCell.height }, (_, i) => checkRow + i);
          break;
        }
      }
    }
  }

  const difference = cellIndex - script.history_grid.grid[rowIndex].current_index;

  const result = {
    ...script,
    history_grid: {
      ...script.history_grid,
      grid: script.history_grid.grid.map((row, i) =>
        affectedRows.includes(i) ? { ...row, current_index: row.current_index + difference } : row
      ),
    },
  };

  return result;
};
export const handleAddDialogueCell = (script: Script, rowIndex: number): Script => {
  const currentRow = script.history_grid.grid[rowIndex];
  const currentCell = currentRow.cells[currentRow.current_index];
  const affectedRows = Array.from({ length: currentCell.height }, (_, i) => rowIndex + i);
  const newCell: ScriptHistoryGridCell = {
    ...currentCell,
    generated_filepath: '',
    waveform_data: [],
    hide: false,
  };

  return {
    ...script,
    history_grid: {
      ...script.history_grid,
      grid: script.history_grid.grid.map((row, i) => {
        if (affectedRows.includes(i)) {
          let newCells = [...row.cells, newCell];
          if (i !== rowIndex) {
            // For cells that aren't the multi-speaker cell, make empty, hidden cells
            newCells = [...row.cells, makeHiddenCell(row)];
          }
          return {
            ...row,
            cells: newCells,
            current_index: newCells.length - 1,
          };
        }
        return row;
      }),
    },
  };
};

export const handleAddCell = (
  script: Script,
  rowIndex: number,
  selectedCells: Set<string>,
  creatingSingleDialogueCell: boolean = false
): Script => {
  // Check if we're dealing with a multi-speaker cell
  const currentRow = script.history_grid.grid[rowIndex];
  const currentCell = currentRow.cells[currentRow.current_index];

  const text = currentCell.height > 1 ? currentCell.texts[1] : currentCell.texts[0];
  // Handle regular cell creation (single new cell)
  const newCell = {
    ...currentCell,
    texts: [text],
    speakers: [currentCell.speakers[0]],
    actors: [currentCell.actors[0]],
    voice_mode: currentCell.voice_mode,
    generated_filepath: '',
    waveform_data: [],
    height: 1,
    hide: false,
  };

  return {
    ...script,
    history_grid: {
      ...script.history_grid,
      grid: script.history_grid.grid.map((row, i) => {
        if (i === rowIndex) {
          const newCells = [...row.cells, newCell];
          return {
            ...row,
            cells: newCells,
            current_index: newCells.length - 1,
          };
        }
        return row;
      }),
    },
  };
};
